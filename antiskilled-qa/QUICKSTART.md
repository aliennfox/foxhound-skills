# 🚀 Quick Start - 5 分钟上手 Antiskilled QA

## ⚡ 最快验证（2 分钟）

```bash
# 1. 进入 skill 目录
cd /home/ubuntu/clawd/skills/antiskilled-qa

# 2. 设置 API Key
export OPENROUTER_API_KEY="sk-or-v1-..."  # 替换为你的 key

# 3. 运行测试（使用已有视频）
python test_example.py
```

如果看到类似输出，说明系统正常：
```
✅ Transcript 长度: 15234 字符
✅ Signals 数量: 1
✅ Summary Sections: 7
🤖 使用模型: anthropic/claude-sonnet-4
⏳ 开始评估...

🎯 Total Score: 8.64/10
📊 Grade: B
```

---

## 📊 评估单个视频（5 分钟）

```bash
# 假设你有一个新处理的视频
VIDEO_ID="abc123"
VIDEO_DIR="/home/ubuntu/clawd/Antiskilled/temp/$VIDEO_ID"

python evaluate.py single \
  --transcript "$VIDEO_DIR/${VIDEO_ID}_transcript.txt" \
  --audit-result "$VIDEO_DIR/${VIDEO_ID}_audit_result.json" \
  --output "/tmp/${VIDEO_ID}_qa.json"

# 查看结果
cat "/tmp/${VIDEO_ID}_qa.json" | jq '.total_score, .grade, .recommendations'
```

---

## 🔥 批量评估所有视频

```bash
# 评估所有，仅保存低于 7.0 分的报告
python evaluate.py batch \
  --video-dir /home/ubuntu/clawd/Antiskilled/temp \
  --output-dir /home/ubuntu/clawd/Antiskilled/qa_reports \
  --min-score 7.0

# 生成 CSV 报告
python generate_report.py \
  --qa-dir /home/ubuntu/clawd/Antiskilled/qa_reports \
  --output summary.csv \
  --stats
```

---

## 💾 保存到数据库

```bash
# 首次运行：执行数据库迁移
cd /home/ubuntu/clawd/Antiskilled
source .venv/bin/activate
source .env  # 加载 DATABASE_URL

psql $SUPABASE_URL -f /home/ubuntu/clawd/skills/antiskilled-qa/database_migration.sql

# 保存 QA 结果
cd /home/ubuntu/clawd/skills/antiskilled-qa
python save_to_db.py batch --qa-dir /home/ubuntu/clawd/Antiskilled/qa_reports

# 查询统计
python save_to_db.py query --type summary
python save_to_db.py query --type worst --limit 10
```

---

## ⏰ 设置每日自动化

```bash
# 编辑 cron
crontab -e

# 添加每天凌晨 2 点运行
0 2 * * * /home/ubuntu/clawd/skills/antiskilled-qa/daily_qa.sh >> /tmp/qa_daily.log 2>&1

# 测试脚本（不等到凌晨）
./daily_qa.sh
```

---

## 🎯 核心评分维度

| 维度 | 满分标准 | 常见问题 |
|------|---------|---------|
| **准确性** | 数据与原文 100% 一致 | ticker 错误、价格编造 |
| **完整性** | 无遗漏重要信号 | 漏提 ticker、漏提价格目标 |
| **可读性** | 自然流畅，普通人能懂 | 术语堆砌、机器味 |
| **信号质量** | conviction/action 合理 | conviction 过高/过低 |
| **Hype 评估** | 6 维度准确匹配风格 | lexical/urgency 误判 |
| **结构质量** | 3-7 个板块，highlight 准确 | 板块过少/过多 |
| **Claims 质量** | 可验证断言完整准确 | 遗漏目标价、时间窗口模糊 |

---

## 📈 解读评分

- **A (9.0-10)** → 直接上线，无需修改 ✨
- **B (7.0-8.9)** → 良好，小问题可忽略 👍
- **C (5.0-6.9)** → 需改进，检查 recommendations ⚠️
- **D (3.0-4.9)** → 不合格，需重新处理 ❌
- **F (0-2.9)** → 失败，检查 prompt/模型 💥

---

## 🛠️ Troubleshooting

### 问题：`ModuleNotFoundError: No module named 'openai'`
```bash
cd /home/ubuntu/clawd/Antiskilled
source .venv/bin/activate
pip install openai
```

### 问题：API 超时
```bash
# 切换到更快的模型
python evaluate.py batch --model anthropic/claude-haiku-4 ...
```

### 问题：找不到测试视频
```bash
# 先处理一个视频
cd /home/ubuntu/clawd/Antiskilled
python -c "from api.main import process_video; import asyncio; asyncio.run(process_video('https://youtube.com/watch?v=...'))"
```

---

## 📚 完整文档

- **SKILL.md** - 完整评估框架和评分标准（详细版）
- **README.md** - 使用说明和示例
- **INDEX.md** - 文件导航
- **EXAMPLE_OUTPUT.json** - 示例输出

---

## 💰 成本参考

| 场景 | 成本 |
|------|------|
| 单视频评估 | ~$0.02 |
| 100 视频批量 | ~$2.00 |
| 使用 Haiku 模型 | ~$0.003/视频 |

**省钱技巧**：用 `--min-score 7.0` 仅保存低分视频，大部分视频不保存。

---

🎉 **就这么简单！** 如有问题，查看 `README.md` 或 `SKILL.md`。
