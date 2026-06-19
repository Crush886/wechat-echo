"""
wechat-echo 网页聊天界面

基于 Gradio 构建的聊天界面，可以和模仿对方说话风格的机器人对话。

使用方法：
    python run.py
    python -m src.webui
"""

import gradio as gr
import os
import json
import sys

# 确保能找到项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.chatbot import get_bot

# 项目路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(BASE_DIR, "config.yaml")
README_FILE = os.path.join(BASE_DIR, "README.md")


def load_bot():
    """加载机器人"""
    try:
        bot = get_bot()
        if bot.initialize():
            return bot, None
        else:
            return None, "机器人初始化失败，请检查配置和数据文件"
    except Exception as e:
        return None, str(e)


def chat_response(message, history, bot_state):
    """处理聊天消息"""
    if not message.strip():
        return "", history

    bot = bot_state.get("bot")
    if not bot:
        bot, error = load_bot()
        if error:
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": f"❌ {error}"})
            return "", history
        bot_state["bot"] = bot

    # 添加用户消息
    history.append({"role": "user", "content": message})

    # 转换历史格式给 chatbot
    chat_history = []
    for h in history[:-1]:  # 不包含当前消息
        if h["role"] == "user":
            chat_history.append({"role": "user", "content": h["content"]})
        else:
            chat_history.append({"role": "assistant", "content": h["content"]})

    # 获取回复
    reply = bot.chat(message, chat_history)

    # 添加回复
    history.append({"role": "assistant", "content": reply})

    return "", history


def clear_chat():
    """清空聊天记录"""
    return []


def get_bot_info(bot_state):
    """获取机器人信息"""
    bot = bot_state.get("bot")
    if not bot:
        return "机器人未加载"

    info = bot.get_info()
    if not info:
        return "暂无信息"

    return f"""**联系人**: {info.get('contact', '未知')}
**消息数量**: {info.get('message_count', 0)} 条
**对话轮次**: {info.get('conversation_count', 0)} 个
**API 提供商**: {info.get('provider', '未知')}
**模型**: {info.get('model', '未知')}"""


def check_data_files():
    """检查数据文件是否存在"""
    clean_file = os.path.join(DATA_DIR, "chat_clean.json")
    config_file = CONFIG_FILE

    issues = []
    if not os.path.exists(config_file):
        issues.append("❌ 配置文件 config.yaml 不存在")
    if not os.path.exists(clean_file):
        issues.append("❌ 聊天数据 chat_clean.json 不存在，请先运行数据清洗")

    return issues


def create_ui():
    """创建界面"""
    # 检查数据
    issues = check_data_files()

    with gr.Blocks(
        title="wechat-echo",
        theme=gr.themes.Soft(),
        css="""
        .container { max-width: 900px; margin: auto; }
        .header { text-align: center; margin-bottom: 20px; }
        .info-panel { padding: 15px; background: #f5f5f5; border-radius: 8px; }
        """
    ) as app:

        # 状态
        bot_state = gr.State({"bot": None})

        # 标题
        gr.Markdown("""
        # 💬 wechat-echo

        > 用你的微信聊天记录，训练一个聊天机器人

        在下方输入消息，和模仿对方说话风格的机器人聊天。
        """)

        # 警告信息
        if issues:
            gr.Markdown("\n".join([f"⚠️ {issue}" for issue in issues]))

        with gr.Row():
            # 左侧：聊天区
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="聊天",
                    height=500,
                    type="messages",
                    show_label=False,
                    bubble_full_width=False,
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        label="输入消息",
                        placeholder="输入你想说的话...",
                        scale=4,
                        show_label=False,
                    )
                    send_btn = gr.Button("发送", variant="primary", scale=1)

                with gr.Row():
                    clear_btn = gr.Button("🗑️ 清空聊天", size="sm")

            # 右侧：信息面板
            with gr.Column(scale=1):
                gr.Markdown("### 📊 机器人信息")

                info_display = gr.Markdown(
                    value="点击「加载机器人」查看信息",
                    elem_classes=["info-panel"]
                )

                load_btn = gr.Button("🔄 加载机器人", variant="secondary")

                gr.Markdown("---")

                gr.Markdown("""
                ### 💡 使用提示

                - 用自然的语言和对方聊天
                - 机器人会模仿对方的说话风格
                - 回复内容基于你们的聊天记录生成

                ### ⚙️ 配置

                编辑 `config.yaml` 可以：
                - 切换 API 提供商
                - 调整回复温度
                - 修改检索数量
                """)

        # 事件绑定
        def on_load_bot(bot_state):
            bot, error = load_bot()
            if error:
                return bot_state, f"❌ {error}"
            bot_state["bot"] = bot
            info = get_bot_info(bot_state)
            return bot_state, info

        def on_send(message, history, bot_state):
            return chat_response(message, history, bot_state)

        def on_clear():
            return clear_chat()

        # 绑定事件
        load_btn.click(
            fn=on_load_bot,
            inputs=[bot_state],
            outputs=[bot_state, info_display]
        )

        send_btn.click(
            fn=on_send,
            inputs=[msg_input, chatbot, bot_state],
            outputs=[msg_input, chatbot]
        )

        msg_input.submit(
            fn=on_send,
            inputs=[msg_input, chatbot, bot_state],
            outputs=[msg_input, chatbot]
        )

        clear_btn.click(
            fn=on_clear,
            outputs=[chatbot]
        )

    return app


def main():
    """启动界面"""
    print("=" * 50)
    print("       wechat-echo 网页聊天界面")
    print("=" * 50)

    # 检查配置
    issues = check_data_files()
    if issues:
        print("\n⚠️ 发现以下问题:")
        for issue in issues:
            print(f"   {issue}")
        print("\n请先完成数据准备，再启动界面。")
        print("参考 README.md 了解完整流程。")
        print()

    # 创建并启动界面
    app = create_ui()

    print("\n🌐 正在启动网页界面...")
    print("   浏览器将自动打开，如果没有请手动访问显示的地址")
    print("   按 Ctrl+C 停止服务")
    print()

    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        inbrowser=True,
    )


if __name__ == "__main__":
    main()
