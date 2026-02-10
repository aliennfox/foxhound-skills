# mem0 - 长期记忆层

云端向量记忆，自动提取对话关键信息。

## 快速使用

```bash
# 搜索记忆（回答问题前先搜）
python3 ~/clawd/scripts/mem0-client.py search "关键词"

# 添加记忆（重要信息手动存）
python3 ~/clawd/scripts/mem0-client.py add "Fox 说他喜欢用 Claude"

# 查看所有记忆
python3 ~/clawd/scripts/mem0-client.py history
```

## 使用场景

### 1. 对话开始时 - 检索上下文
```bash
python3 ~/clawd/scripts/mem0-client.py search "用户最近在做什么"
```

### 2. 用户提到偏好/重要信息时 - 存储
```bash
python3 ~/clawd/scripts/mem0-client.py add "Fox 的时区是 UTC+8"
```

### 3. 被问到历史问题时 - 搜索
```bash
python3 ~/clawd/scripts/mem0-client.py search "Antiskilled 项目"
```

## 注意事项

- mem0 会自动提取和结构化信息（不需要原样存储）
- 云端存储，有隐私考虑
- 免费额度 10K memories
- user_id 固定为 "fox"

## API Key

存储在脚本中：`m0-bKiPaQlg7WuYDmGH9bOJFf0jbnG8FqTXPdemKYPF`
