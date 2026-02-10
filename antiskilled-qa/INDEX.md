# Antiskilled QA Skill - 文件索引

## 核心文档
- **SKILL.md** - 完整的评估框架和标准（必读）
- **README.md** - 快速开始和使用说明
- **INDEX.md** - 本文件（文件导航）

## 脚本文件

### 评估脚本
| 文件 | 用途 | 示例命令 |
|------|------|----------|
| `evaluate.py` | 单个/批量评估视频 | `python evaluate.py batch --video-dir /path/to/videos --output-dir /path/to/output` |
| `test_example.py` | 测试示例（快速验证） | `python test_example.py` |

### 报告生成
| 文件 | 用途 | 示例命令 |
|------|------|----------|
| `generate_report.py` | 生成 CSV/HTML 报告 | `python generate_report.py --qa-dir /path/to/qa --output summary.csv --stats` |

### 数据库集成
| 文件 | 用途 | 示例命令 |
|------|------|----------|
| `save_to_db.py` | 保存 QA 结果到 Supabase | `python save_to_db.py batch --qa-dir /path/to/qa` |
| `database_migration.sql` | 数据库表结构迁移 | `psql -f database_migration.sql` |

### 自动化
| 文件 | 用途 | 示例命令 |
|------|------|----------|
| `daily_qa.sh` | 每日自动化 QA 脚本 | `./daily_qa.sh` 或 `crontab -e` |

## 模板文件
- **evaluation_template.json** - 手动评估模板

## 典型工作流

### 1. 快速测试（首次使用）
```bash
cd /home/ubuntu/clawd/skills/antiskilled-qa
export OPENROUTER_API_KEY="sk-or-v1-..."
python test_example.py
```

### 2. 单个视频评估
```bash
python evaluate.py single \
  --transcript /path/to/transcript.txt \
  --audit-result /path/to/audit_result.json \
  --output /tmp/qa.json
```

### 3. 批量评估（仅保存低分）
```bash
python evaluate.py batch \
  --video-dir /home/ubuntu/clawd/Antiskilled/temp \
  --output-dir /home/ubuntu/clawd/Antiskilled/qa_reports \
  --min-score 7.0
```

### 4. 生成可视化报告
```bash
python generate_report.py \
  --qa-dir /home/ubuntu/clawd/Antiskilled/qa_reports \
  --output report.html
```

### 5. 保存到数据库
```bash
# 先运行数据库迁移（仅首次）
cd /home/ubuntu/clawd/Antiskilled
psql $DATABASE_URL -f /home/ubuntu/clawd/skills/antiskilled-qa/database_migration.sql

# 保存 QA 结果
cd /home/ubuntu/clawd/skills/antiskilled-qa
python save_to_db.py batch --qa-dir /home/ubuntu/clawd/Antiskilled/qa_reports
```

### 6. 设置定时任务
```bash
crontab -e
# 添加行：
# 0 2 * * * /home/ubuntu/clawd/skills/antiskilled-qa/daily_qa.sh >> /tmp/qa_cron.log 2>&1
```

## 输出文件说明

### QA 结果文件 (`*_qa.json`)
```json
{
  "video_id": "abc123",
  "total_score": 8.64,
  "grade": "B",
  "scores": { ... },
  "issues": { ... },
  "recommendations": [ ... ]
}
```

### 汇总报告 (`summary.json`)
```json
{
  "total_videos": 50,
  "successful": 48,
  "low_score_videos": [ ... ]
}
```

### CSV 报告 (`summary_YYYYMMDD.csv`)
| video_id | total_score | grade | accuracy | ... |
|----------|-------------|-------|----------|-----|
| abc123   | 8.64        | B     | 9.0      | ... |

## 评分标准速查

| 维度 | 关键检查项 | 扣分项 |
|------|-----------|--------|
| **准确性** | ticker, 价格, 时间戳 | 编造数据 -5 |
| **完整性** | 遗漏 ticker, 遗漏价格目标 | 遗漏主要 ticker -3 |
| **可读性** | 流畅自然, 术语解释 | 机器味 -2 |
| **信号质量** | conviction 合理, action 正确 | action 错误 -5 |
| **Hype 评估** | 6 维度打分准确 | 维度偏差 ±3 -1 |
| **结构质量** | 3-7 个板块, highlight_tokens | 板块 <3 或 >7 -2 |
| **Claims 质量** | 可验证, direction 正确 | 遗漏 Claim -3 |

## 等级划分
- **A (9.0-10.0)**: 卓越 ✨
- **B (7.0-8.9)**: 良好 👍
- **C (5.0-6.9)**: 合格 ⚠️
- **D (3.0-4.9)**: 不合格 ❌
- **F (0.0-2.9)**: 失败 💥

## 问题排查

| 问题 | 解决方案 |
|------|----------|
| `ModuleNotFoundError` | `pip install openai` |
| API 超时 | 增加 timeout 或切换模型 |
| JSON 解析失败 | 检查 Claude 输出格式，添加容错 |
| 数据库连接失败 | 检查 `.env` 中的 `SUPABASE_URL` |

## 成本估算
- **单视频**: $0.015 - $0.025 (Claude Sonnet)
- **100 视频**: ~$2.00
- **省钱**: 用 Claude Haiku 初筛 (~$0.003/视频)

## 相关资源
- Antiskilled 项目: `/home/ubuntu/clawd/Antiskilled`
- 数据模型: `/home/ubuntu/clawd/Antiskilled/models/`
- Prompt 模板: `/home/ubuntu/clawd/Antiskilled/core/business/prompts/`

---

**Maintained by**: Claude (OpenClaw Agent)  
**Version**: 1.0.0  
**Last Updated**: 2026-01-03
