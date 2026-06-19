"""
聊天记录数据清洗器

清洗和格式化微信聊天记录，提取说话风格特征。

使用方法：
    python run.py clean
"""

import json
import os
import re
from collections import Counter

# 文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
RAW_FILE = os.path.join(DATA_DIR, "chat_raw.json")
CLEAN_FILE = os.path.join(DATA_DIR, "chat_clean.json")
STYLE_FILE = os.path.join(DATA_DIR, "style_profile.json")


# 需要过滤的消息模式
FILTER_PATTERNS = [
    r"^\[.*\]$",                    # [图片]、[语音]、[视频] 等
    r"^<.*>$",                      # XML 消息
    r"^<msg>.*</msg>$",            # XML 格式消息
    r"你已添加了.*",                 # 添加好友提示
    r"以上是打招呼的内容.*",         # 系统提示
    r"撤回了一条消息",              # 撤回消息
    r"你领取了.*的红包",            # 红包消息
    r".*发出了一个红包.*",          # 红包消息
    r".*邀请你加入了群聊.*",        # 群聊邀请
    r"系统消息",                    # 系统消息
]


def load_raw_data(filepath=None):
    """加载原始聊天数据"""
    if filepath is None:
        filepath = RAW_FILE

    if not os.path.exists(filepath):
        print(f"❌ 未找到文件: {filepath}")
        print("请先运行: python run.py extract")
        print("或将聊天记录文件放入 data/chat_raw.json")
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"📂 已加载数据: {data.get('contact', '未知')}")
    print(f"   消息总数: {len(data.get('messages', []))}")
    return data


def should_filter(message):
    """判断消息是否应该被过滤"""
    content = message.get("content", "").strip()

    # 过滤空消息
    if not content:
        return True

    # 过滤匹配模式的消息
    for pattern in FILTER_PATTERNS:
        if re.match(pattern, content):
            return True

    # 过滤纯表情消息（单个 emoji）
    if len(content) <= 2 and not content.isalnum():
        return True

    return False


def clean_messages(raw_data):
    """清洗消息列表"""
    messages = raw_data.get("messages", [])
    contact = raw_data.get("contact", "她")
    my_name = raw_data.get("my_name", "我")

    cleaned = []
    filtered_count = 0

    for msg in messages:
        if should_filter(msg):
            filtered_count += 1
            continue

        cleaned.append({
            "sender": msg["sender"],
            "time": msg.get("time", ""),
            "content": msg["content"].strip()
        })

    print(f"🧹 清洗完成:")
    print(f"   原始消息: {len(messages)} 条")
    print(f"   过滤消息: {filtered_count} 条")
    print(f"   保留消息: {len(cleaned)} 条")

    return cleaned


def build_conversations(messages, contact, my_name, time_gap=300):
    """
    将消息整理成对话轮次

    参数:
        time_gap: 同一对话中两条消息的最大时间间隔（秒）
    """
    if not messages:
        return []

    conversations = []
    current_conv = []

    for i, msg in enumerate(messages):
        if not current_conv:
            current_conv.append(msg)
            continue

        # 检查时间间隔（如果有的话）
        current_conv.append(msg)

        # 如果发送者切换，且下一条是对方发的，可能是一个对话轮次结束
        if msg["sender"] == my_name and i + 1 < len(messages):
            next_msg = messages[i + 1]
            if next_msg["sender"] != my_name:
                # 对话轮次结束
                if len(current_conv) >= 2:
                    conversations.append(current_conv)
                current_conv = []

    # 添加最后一个对话
    if current_conv and len(current_conv) >= 2:
        conversations.append(current_conv)

    print(f"📝 整理对话轮次: {len(conversations)} 个")
    return conversations


def extract_style_features(messages, contact):
    """提取对方的说话风格特征"""
    her_messages = [m for m in messages if m["sender"] == contact]

    if not her_messages:
        return {}

    # 统计常用词
    all_words = []
    for msg in her_messages:
        content = msg["content"]
        # 简单分词（按字符和常见分隔符）
        words = re.findall(r'[一-鿿]+|[a-zA-Z]+|[0-9]+', content)
        all_words.extend(words)

    word_freq = Counter(all_words).most_common(50)

    # 统计常用语气词
    particles = ["哈哈", "嗯嗯", "嘻嘻", "嘿嘿", "啦", "呀", "呢", "吧", "嘛", "诶", "哦", "噢", "emmm", "hhh"]
    particle_usage = {}
    for p in particles:
        count = sum(1 for m in her_messages if p in m["content"])
        if count > 0:
            particle_usage[p] = count

    # 统计表情使用
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # 表情
        "\U0001F300-\U0001F5FF"  # 符号
        "\U0001F680-\U0001F6FF"  # 交通
        "\U0001F1E0-\U0001F1FF"  # 旗帜
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    emoji_count = sum(1 for m in her_messages if emoji_pattern.search(m["content"]))

    # 消息长度统计
    lengths = [len(m["content"]) for m in her_messages]
    avg_length = sum(lengths) / len(lengths) if lengths else 0

    # 常用标点
    punctuation = ["！", "？", "~", "。。。", "…", "！？", "？？"]
    punct_usage = {}
    for p in punctuation:
        count = sum(1 for m in her_messages if p in m["content"])
        if count > 0:
            punct_usage[p] = count

    style = {
        "total_messages": len(her_messages),
        "avg_message_length": round(avg_length, 1),
        "top_words": word_freq[:20],
        "particle_usage": particle_usage,
        "emoji_frequency": emoji_count,
        "punctuation_usage": punct_usage,
        "sample_messages": [m["content"] for m in her_messages[:20]]
    }

    return style


def save_clean_data(contact, my_name, messages, conversations, style):
    """保存清洗后的数据"""
    os.makedirs(DATA_DIR, exist_ok=True)

    # 保存清洗后的聊天记录
    clean_data = {
        "contact": contact,
        "my_name": my_name,
        "total_messages": len(messages),
        "total_conversations": len(conversations),
        "messages": messages,
        "conversations": conversations
    }

    with open(CLEAN_FILE, "w", encoding="utf-8") as f:
        json.dump(clean_data, f, ensure_ascii=False, indent=2)

    # 保存风格分析
    with open(STYLE_FILE, "w", encoding="utf-8") as f:
        json.dump(style, f, ensure_ascii=False, indent=2)

    print(f"\n💾 文件已保存:")
    print(f"   聊天记录: {CLEAN_FILE}")
    print(f"   风格分析: {STYLE_FILE}")


def print_style_summary(style):
    """打印风格分析摘要"""
    print("\n" + "=" * 50)
    print("       📊 说话风格分析")
    print("=" * 50)

    print(f"  消息总数: {style.get('total_messages', 0)}")
    print(f"  平均消息长度: {style.get('avg_message_length', 0)} 字")

    if style.get("particle_usage"):
        print("\n  常用语气词:")
        for word, count in sorted(style["particle_usage"].items(), key=lambda x: -x[1])[:5]:
            print(f"    {word}: {count} 次")

    if style.get("top_words"):
        print("\n  常用词:")
        for word, count in style["top_words"][:10]:
            print(f"    {word}: {count} 次")

    if style.get("sample_messages"):
        print("\n  典型消息示例:")
        for msg in style["sample_messages"][:5]:
            print(f"    「{msg}」")


def main():
    """主函数"""
    print("=" * 50)
    print("       聊天记录数据清洗工具")
    print("=" * 50)

    # 加载数据
    raw_data = load_raw_data()
    if not raw_data:
        return

    contact = raw_data.get("contact", "她")
    my_name = raw_data.get("my_name", "我")

    # 清洗消息
    messages = clean_messages(raw_data)
    if not messages:
        print("❌ 清洗后没有有效消息")
        return

    # 整理对话轮次
    conversations = build_conversations(messages, contact, my_name)

    # 提取风格特征
    print("\n🔍 正在分析说话风格...")
    style = extract_style_features(messages, contact)

    # 打印风格摘要
    print_style_summary(style)

    # 保存
    save_clean_data(contact, my_name, messages, conversations, style)

    print("\n" + "=" * 50)
    print("✅ 清洗完成！")
    print("接下来运行: python run.py 启动聊天界面")
    print("=" * 50)


if __name__ == "__main__":
    main()
