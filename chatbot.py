"""
wechat-echo 聊天机器人核心

使用 RAG（检索增强生成）技术：
1. 将历史聊天记录存入向量数据库
2. 用户发消息时，检索最相关的历史对话
3. 将历史对话作为参考，让 AI 模仿对方的说话风格回复

支持 DeepSeek 和通义千问 API
"""

import json
import os
from typing import List, Dict, Optional

# 文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(BASE_DIR, "config.yaml")
CLEAN_FILE = os.path.join(DATA_DIR, "chat_clean.json")
STYLE_FILE = os.path.join(DATA_DIR, "style_profile.json")


class WechatEchoBot:
    """wechat-echo 聊天机器人"""

    def __init__(self, config_path=None):
        self.config = self._load_config(config_path or CONFIG_FILE)
        self.chat_data = None
        self.style_profile = None
        self.collection = None
        self.client = None
        self._initialized = False

    def _load_config(self, path):
        """加载配置文件"""
        import yaml
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"配置文件不存在: {path}\n"
                f"请复制 config.yaml.example 为 config.yaml 并填写 API Key"
            )
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def initialize(self):
        """初始化机器人（加载数据、创建向量库）"""
        if self._initialized:
            return True

        print("🤖 正在初始化 wechat-echo 机器人...")

        # 加载聊天数据
        if not self._load_chat_data():
            return False

        # 加载风格分析
        self._load_style_profile()

        # 初始化 API 客户端
        if not self._init_api_client():
            return False

        # 创建向量数据库
        if not self._init_vector_db():
            return False

        self._initialized = True
        print("✅ 机器人初始化完成！")
        return True

    def _load_chat_data(self):
        """加载清洗后的聊天数据"""
        if not os.path.exists(CLEAN_FILE):
            print(f"❌ 未找到聊天数据: {CLEAN_FILE}")
            print("请先运行数据清洗: python run.py clean")
            return False

        with open(CLEAN_FILE, "r", encoding="utf-8") as f:
            self.chat_data = json.load(f)

        contact = self.chat_data.get("contact", "未知")
        msg_count = len(self.chat_data.get("messages", []))
        print(f"📂 已加载聊天数据: {contact} ({msg_count} 条消息)")
        return True

    def _load_style_profile(self):
        """加载风格分析数据"""
        if os.path.exists(STYLE_FILE):
            with open(STYLE_FILE, "r", encoding="utf-8") as f:
                self.style_profile = json.load(f)
            print("📊 已加载说话风格分析")
        else:
            self.style_profile = {}
            print("⚠️ 未找到风格分析文件，将使用默认风格")

    def _init_api_client(self):
        """初始化 API 客户端"""
        try:
            from openai import OpenAI

            provider = self.config["api"]["provider"]

            if provider == "deepseek":
                api_key = self.config["api"]["deepseek_key"]
                base_url = "https://api.deepseek.com"
                model = self.config["api"].get("deepseek_model", "deepseek-chat")
            elif provider == "qwen":
                api_key = self.config["api"]["qwen_key"]
                base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
                model = self.config["api"].get("qwen_model", "qwen-turbo")
            else:
                print(f"❌ 不支持的 API 提供商: {provider}")
                return False

            if "your-key" in api_key or not api_key:
                print("❌ 请在 config.yaml 中填写正确的 API Key")
                return False

            self.client = OpenAI(api_key=api_key, base_url=base_url)
            self.model = model

            print(f"🔗 API 已连接: {provider} ({model})")
            return True

        except ImportError:
            print("❌ 缺少依赖: openai")
            print("请运行: pip install openai")
            return False
        except Exception as e:
            print(f"❌ API 初始化失败: {e}")
            return False

    def _init_vector_db(self):
        """初始化向量数据库"""
        try:
            import chromadb

            # 创建持久化客户端
            db_path = os.path.join(DATA_DIR, "chroma_db")
            os.makedirs(db_path, exist_ok=True)

            client = chromadb.PersistentClient(path=db_path)

            # 获取或创建集合
            self.collection = client.get_or_create_collection(
                name="wechat_messages",
                metadata={"hnsw:space": "cosine"}
            )

            # 如果集合为空，添加数据
            if self.collection.count() == 0:
                self._populate_vector_db()
            else:
                print(f"📦 向量库已有 {self.collection.count()} 条记录")

            return True

        except ImportError:
            print("❌ 缺少依赖: chromadb")
            print("请运行: pip install chromadb")
            return False
        except Exception as e:
            print(f"❌ 向量数据库初始化失败: {e}")
            return False

    def _populate_vector_db(self):
        """将聊天记录添加到向量数据库"""
        import jieba

        messages = self.chat_data.get("messages", [])
        contact = self.chat_data.get("contact", "她")

        print(f"📦 正在构建向量库 ({len(messages)} 条消息)...")

        # 准备数据
        ids = []
        documents = []
        metadatas = []

        for i, msg in enumerate(messages):
            # 只索引对方的消息（用于学习风格）
            # 但也索引我方消息（用于检索上下文）
            content = msg["content"]

            # 使用 jieba 分词提高检索效果
            words = " ".join(jieba.cut(content))

            ids.append(f"msg_{i}")
            documents.append(words)
            metadatas.append({
                "sender": msg["sender"],
                "original": content,
                "time": msg.get("time", ""),
                "index": i
            })

        # 批量添加（ChromaDB 限制每批 5461 条）
        batch_size = 5000
        for start in range(0, len(ids), batch_size):
            end = min(start + batch_size, len(ids))
            self.collection.add(
                ids=ids[start:end],
                documents=documents[start:end],
                metadatas=metadatas[start:end]
            )

        print(f"✅ 向量库构建完成")

    def _build_system_prompt(self):
        """构建系统提示词"""
        contact = self.chat_data.get("contact", "她")
        style = self.style_profile or {}

        # 基础提示
        prompt = f"""你是一个聊天机器人，你的任务是模仿「{contact}」的说话风格和用户聊天。

## 你的身份
- 你是「{contact}」，不是 AI 助手
- 用「{contact}」的口吻、语气、用词习惯来回复
- 保持自然、真实的聊天感觉

## 说话风格要求"""

        # 添加风格特征
        if style.get("particle_usage"):
            particles = ", ".join(list(style["particle_usage"].keys())[:5])
            prompt += f"\n- 常用语气词: {particles}"

        if style.get("avg_message_length"):
            avg_len = style["avg_message_length"]
            if avg_len < 10:
                prompt += "\n- 回复要简短，几句话就好"
            elif avg_len < 20:
                prompt += "\n- 回复长度适中，不要太长"
            else:
                prompt += "\n- 可以回复稍长一些"

        if style.get("punctuation_usage"):
            puncts = ", ".join(list(style["punctuation_usage"].keys())[:3])
            prompt += f"\n- 常用标点: {puncts}"

        # 添加示例消息
        if style.get("sample_messages"):
            prompt += "\n\n## 典型消息示例（参考语气）"
            for msg in style["sample_messages"][:5]:
                prompt += f'\n- "{msg}"'

        prompt += f"""

## 对话上下文
以下是你们之前的聊天记录片段，参考这些来理解你们的关系和聊天风格：

"""

        return prompt

    def _retrieve_relevant_messages(self, query, top_k=None):
        """检索与用户消息相关的历史记录"""
        import jieba

        if top_k is None:
            top_k = self.config["chatbot"]["top_k"]

        # 分词
        query_words = " ".join(jieba.cut(query))

        # 检索
        results = self.collection.query(
            query_texts=[query_words],
            n_results=top_k
        )

        # 整理结果
        relevant = []
        if results and results["metadatas"]:
            for meta in results["metadatas"][0]:
                relevant.append({
                    "sender": meta["sender"],
                    "content": meta["original"],
                    "time": meta.get("time", "")
                })

        return relevant

    def _build_context_messages(self, relevant_msgs):
        """构建上下文消息"""
        contact = self.chat_data.get("contact", "她")
        my_name = self.chat_data.get("my_name", "我")

        context_parts = []
        for msg in relevant_msgs:
            sender = msg["sender"]
            content = msg["content"]
            context_parts.append(f"{sender}: {content}")

        return "\n".join(context_parts)

    def chat(self, user_message: str, history: List[Dict] = None) -> str:
        """
        与机器人对话

        参数:
            user_message: 用户发送的消息
            history: 对话历史（可选）

        返回:
            机器人回复
        """
        if not self._initialized:
            if not self.initialize():
                return "❌ 机器人初始化失败，请检查配置"

        contact = self.chat_data.get("contact", "她")

        # 检索相关历史记录
        relevant = self._retrieve_relevant_messages(user_message)

        # 构建系统提示
        system_prompt = self._build_system_prompt()

        # 添加上下文
        context = self._build_context_messages(relevant)
        system_prompt += context

        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]

        # 添加对话历史
        if history:
            for h in history[-10:]:  # 只保留最近 10 轮
                messages.append(h)

        # 添加用户消息
        messages.append({"role": "user", "content": user_message})

        try:
            # 调用 API
            temperature = self.config["chatbot"]["temperature"]
            max_tokens = self.config["chatbot"]["max_tokens"]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            reply = response.choices[0].message.content
            return reply

        except Exception as e:
            return f"❌ 生成回复失败: {e}"

    def get_info(self) -> Dict:
        """获取机器人信息"""
        if not self.chat_data:
            return {}

        return {
            "contact": self.chat_data.get("contact", "未知"),
            "message_count": len(self.chat_data.get("messages", [])),
            "conversation_count": self.chat_data.get("total_conversations", 0),
            "provider": self.config["api"]["provider"],
            "model": self.model if hasattr(self, "model") else "未知"
        }


# 全局实例
_bot_instance = None


def get_bot(config_path=None) -> WechatEchoBot:
    """获取机器人单例"""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = WechatEchoBot(config_path)
    return _bot_instance


def chat(user_message: str, history: List[Dict] = None) -> str:
    """快捷对话接口"""
    bot = get_bot()
    return bot.chat(user_message, history)
