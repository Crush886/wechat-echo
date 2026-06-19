#!/usr/bin/env python3
"""
wechat-echo 一键启动脚本

使用方法：
    python run.py              # 启动网页聊天界面
    python run.py extract      # 提取微信聊天记录
    python run.py clean        # 清洗聊天数据
    python run.py --help       # 查看帮助
"""

import sys
import os

# 确保 src 目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "extract":
            from src.extractor import main as extract_main
            extract_main()

        elif command == "clean":
            from src.cleaner import main as clean_main
            clean_main()

        elif command == "--help" or command == "-h":
            print_help()

        else:
            print(f"❌ 未知命令: {command}")
            print_help()
    else:
        # 默认启动网页界面
        from src.webui import main as webui_main
        webui_main()


def print_help():
    print("""
╔══════════════════════════════════════════╗
║         wechat-echo 使用帮助             ║
╠══════════════════════════════════════════╣
║                                          ║
║  python run.py          启动聊天界面      ║
║  python run.py extract  提取微信聊天记录  ║
║  python run.py clean    清洗聊天数据      ║
║  python run.py --help   查看帮助          ║
║                                          ║
╚══════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()
