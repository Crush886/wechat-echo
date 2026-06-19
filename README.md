# 示例数据说明

## sample_chat.json

这是一个示例聊天记录文件，格式与 `data/chat_raw.json` 相同。

你可以用它来测试项目是否正常工作：

```bash
# 复制示例数据到 data 目录
cp examples/sample_chat.json data/chat_raw.json

# 清洗数据
python run.py clean

# 启动聊天
python run.py
```

## 数据格式说明

```json
{
  "contact": "对方的昵称",      // 对方的名字
  "my_name": "我",              // 你的名字
  "messages": [
    {
      "sender": "我",           // 发送者
      "time": "2024-01-15 09:30:00",  // 时间（可选）
      "content": "消息内容"     // 消息文本
    },
    {
      "sender": "对方的昵称",
      "time": "2024-01-15 09:31:00",
      "content": "回复内容"
    }
  ]
}
```

## 如何准备自己的数据

### 方法一：从微信提取（Windows）
运行 `python run.py extract`，按提示操作。

### 方法二：手动整理
1. 在微信中找到和对方的聊天记录
2. 复制聊天内容
3. 按照上面的格式整理成 JSON 文件
4. 保存为 `data/chat_raw.json`

### 方法三：使用其他工具导出
有一些第三方工具可以导出微信聊天记录，导出后转换成上述 JSON 格式即可。
