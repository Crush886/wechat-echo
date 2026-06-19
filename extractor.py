"""
微信聊天记录提取器

从微信 PC 版数据库中提取与指定联系人的聊天记录。
仅支持 Windows 系统。

使用方法：
    python run.py extract

依赖：
    pip install pywxdump
"""

import json
import os
import sys
from datetime import datetime

# 数据输出路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "chat_raw.json")


def check_dependencies():
    """检查依赖是否安装"""
    try:
        import pywxdump
        return True
    except ImportError:
        print("❌ 缺少依赖: pywxdump")
        print("请先运行: pip install pywxdump")
        return False


def get_wechat_key():
    """获取微信数据库密钥"""
    from pywxdump import bias_addr, read_info

    print("🔍 正在检测微信进程...")
    try:
        result = read_info(is_logging=False)
        if not result:
            print("❌ 未找到微信进程，请确保微信已登录并正在运行")
            return None

        # 返回第一个微信账号的信息
        for key, value in result.items():
            if isinstance(value, dict) and "key" in value:
                print(f"✅ 找到微信账号: {value.get('account', '未知')}")
                return value
        return None
    except Exception as e:
        print(f"❌ 获取微信密钥失败: {e}")
        return None


def decrypt_database(info):
    """解密微信数据库"""
    from pywxdump import wxXdump

    print("🔓 正在解密数据库...")
    try:
        wx = wxXdump(info)
        wx.start()
        print("✅ 数据库解密完成")
        return wx
    except Exception as e:
        print(f"❌ 解密失败: {e}")
        return None


def list_contacts(wx):
    """列出所有联系人"""
    print("\n📋 正在获取联系人列表...")
    try:
        contacts = wx.get_contact()
        if not contacts:
            print("❌ 未找到联系人")
            return []

        print(f"\n共找到 {len(contacts)} 个联系人：")
        print("-" * 50)
        for i, contact in enumerate(contacts[:50], 1):  # 只显示前50个
            nickname = contact.get("NickName", "未知")
            remark = contact.get("Remark", "")
            display = f"{remark}({nickname})" if remark else nickname
            print(f"  {i:3d}. {display}")

        if len(contacts) > 50:
            print(f"  ... 还有 {len(contacts) - 50} 个联系人")

        return contacts
    except Exception as e:
        print(f"❌ 获取联系人失败: {e}")
        return []


def extract_chat(wx, contact_name):
    """提取与指定联系人的聊天记录"""
    print(f"\n📥 正在提取与「{contact_name}」的聊天记录...")

    try:
        # 搜索联系人
        contacts = wx.get_contact()
        target = None
        for contact in contacts:
            nickname = contact.get("NickName", "")
            remark = contact.get("Remark", "")
            if contact_name in nickname or contact_name in remark:
                target = contact
                break

        if not target:
            print(f"❌ 未找到联系人「{contact_name}」")
            print("请检查输入的昵称或备注是否正确")
            return None

        wxid = target.get("wxid", "")
        nickname = target.get("NickName", "")
        remark = target.get("Remark", "")
        display_name = remark if remark else nickname

        print(f"✅ 找到联系人: {display_name} (wxid: {wxid})")

        # 提取聊天记录
        messages = wx.get_msgs(wxid)
        if not messages:
            print("❌ 未找到聊天记录")
            return None

        print(f"✅ 共提取到 {len(messages)} 条消息")

        # 整理消息格式
        chat_data = {
            "contact": display_name,
            "contact_wxid": wxid,
            "my_name": "我",
            "extract_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message_count": len(messages),
            "messages": []
        }

        for msg in messages:
            try:
                # 解析消息时间
                timestamp = msg.get("CreateTime", 0)
                if timestamp:
                    time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    time_str = "未知时间"

                # 判断发送者
                is_self = msg.get("IsSender", 0) == 1
                sender = "我" if is_self else display_name

                # 获取消息内容
                content = msg.get("StrContent", "")
                msg_type = msg.get("Type", 0)

                # 只保留文字消息
                if msg_type == 1 and content.strip():
                    chat_data["messages"].append({
                        "sender": sender,
                        "time": time_str,
                        "content": content.strip()
                    })
            except Exception:
                continue

        print(f"✅ 有效文字消息: {len(chat_data['messages'])} 条")
        return chat_data

    except Exception as e:
        print(f"❌ 提取失败: {e}")
        return None


def save_chat(chat_data):
    """保存聊天记录到文件"""
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(chat_data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 聊天记录已保存到: {OUTPUT_FILE}")
    print(f"   消息总数: {chat_data['message_count']}")
    print(f"   联系人: {chat_data['contact']}")


def main():
    """主函数"""
    print("=" * 50)
    print("       微信聊天记录提取工具")
    print("=" * 50)

    # 检查系统
    if sys.platform != "win32":
        print("❌ 此工具仅支持 Windows 系统")
        print("Mac 用户请参考 README 中的手动导出方法")
        return

    # 检查依赖
    if not check_dependencies():
        return

    # 获取微信密钥
    info = get_wechat_key()
    if not info:
        return

    # 列出联系人
    contacts = list_contacts(None)  # 传入 None，使用全局方法
    if not contacts:
        return

    # 获取要提取的联系人
    print("\n" + "=" * 50)
    contact_name = input("请输入要提取聊天记录的联系人昵称或备注: ").strip()
    if not contact_name:
        print("❌ 联系人名称不能为空")
        return

    # 解密数据库
    wx = decrypt_database(info)
    if not wx:
        return

    # 提取聊天记录
    chat_data = extract_chat(wx, contact_name)
    if not chat_data:
        return

    # 保存
    save_chat(chat_data)

    print("\n" + "=" * 50)
    print("✅ 提取完成！")
    print("接下来运行: python run.py clean")
    print("=" * 50)


if __name__ == "__main__":
    main()
