# Antiskilled QA - 使用说明

## 快速开始

### 1. 安装依赖

```bash
cd /home/ubuntu/clawd/Antiskilled
source .venv/bin/activate
pip install openai  # 如果尚未安装
```

### 2. 设置 API Key

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

或在 `/home/ubuntu/clawd/Antiskilled/.env` 中添加：
```
OPENROUTER_API_KEY=sk-or-v1-...
```

### 3. 评估单个视频

```bash
cd /home/ubuntu/clawd/skills/antiskilled-qa

python evaluate.py single \
  --transcript /home/ubuntu/clawd/Antiskilled/temp/-yfJIVV8i7E/-yfJIVV8i7E_transcript.txt \
  --audit-result /home/ubuntu/clawd/Antiskilled/temp/-yfJIVV8i7E/-yfJIVV8i7E_audit_result.json \
  --output /tmp/qa_result.json
```

### 4. 批量评估

```bash
# 评估所有视频，仅保存低于 7.0 分的报告
python evaluate.py batch \
  --video-dir /home/ubuntu/clawd/Antiskilled/temp \
  --output-dir /home/ubuntu/clawd/Antiskilled/qa_reports \
  --min-score 7.0

# 限制评估数量（测试用）
python evaluate.py batch \
  --video-dir /home/ubuntu/clawd/Antiskilled/temp \
  --output-dir /home/ubuntu/clawd/Antiskilled/qa_reports \
  --max-videos 5
```

### 5. 生成报告

```bash
# 生成 CSV 报告
python generate_report.py \
  --qa-dir /home/ubuntu/clawd/Antiskilled/qa_reports \
  --output summary.csv

# 生成 HTML 报告
python generate_report.py \
  --qa-dir /home/ubuntu/clawd/Antiskilled/qa_reports \
  --output report.html

# 打印统计摘要
python generate_report.py \
  --qa-dir /home/ubuntu/clawd/Antiskilled/qa_reports \
  --output summary.csv \
  --stats
```

---

## 文件结构

```
skills/antiskilled-qa/
├── SKILL.md                    # 完整评估框架文档
├── README.md                   # 本文件
├── evaluate.py                 # 评估脚本（单个/批量）
├── generate_report.py          # 报告生成脚本
├── evaluation_template.json    # 人工评估模板
└── examples/                   # 示例（可选）
    ├── example_qa.json
    └── example_report.html
```

---

## 输出文件说明

### 单个视频评估结果 (`*_qa.json`)

```json
{
  "video_id": "-yfJIVV8i7E",
  "evaluated_at": "2026-01-03T10:30:00Z",
  "evaluator": "anthropic/claude-sonnet-4",
  "scores": {
    "accuracy_score": 9.0,
    "completeness_score": 8.5,
    "readability_score": 9.5,
    "signal_quality_score": 8.0,
    "hype_assessment_score": 9.0,
    "structural_quality_score": 9.0,
    "claims_quality_score": 7.5
  },
  "total_score": 8.64,
  "grade": "B",
  "issues": {
    "accuracy": ["..."],
    "completeness": ["..."],
    ...
  },
  "recommendations": ["...", "..."],
  "strengths": ["...", "..."],
  "evaluation_duration_seconds": 12.5,
  "tokens_used": 3500
}
```

### 汇总报告 (`summary.json`)

```json
{
  "evaluated_at": "2026-01-03T11:00:00Z",
  "total_videos": 50,
  "successful": 48,
  "failed": 2,
  "failed_videos": ["video_id_1", "video_id_2"],
  "low_score_videos": [
    {
      "video_id": "abc123",
      "total_score": 5.2,
      "grade": "C"
    }
  ]
}
```

---

## 常用命令

### 查找最差的 5 个视频

```bash
cd /home/ubuntu/clawd/Antiskilled/qa_reports
ls *_qa.json | xargs -I {} jq -r '[.video_id, .total_score] | @csv' {} | sort -t, -k2 -n | head -5
```

### 统计平均分

```bash
find qa_reports -name "*_qa.json" -exec jq '.total_score' {} \; | \
  awk '{sum+=$1; count++} END {print "Average:", sum/count}'
```

### 查找特定问题

```bash
# 查找所有 accuracy 问题
grep -r "accuracy" qa_reports/*_qa.json | jq '.issues.accuracy[]'
```

---

## 集成到 Antiskilled 流程

### 自动化 QA（处理后立即评估）

在 `Antiskilled/core/business/video_analyzer.py` 的处理完成后添加：

```python
async def analyze_video_with_qa(video_url: str):
    # 原有处理流程
    result = await video_analyzer.process(video_url)
    
    # QA 评估
    try:
        qa_result = await qa_evaluator.evaluate(
            transcript=result['transcript'],
            audit_result=result['audit_output']
        )
        
        if qa_result.total_score < 7.0:
            logger.warning(f"⚠️ Low QA score: {qa_result.total_score}")
            # 可选：发送告警、标记重处理等
    
    except Exception as e:
        logger.error(f"QA evaluation failed: {e}")
    
    return result
```

### 定时批量评估

添加 cron job：

```bash
# 每天凌晨 2 点评估前一天的视频
0 2 * * * cd /home/ubuntu/clawd/skills/antiskilled-qa && \
  python evaluate.py batch \
    --video-dir /home/ubuntu/clawd/Antiskilled/temp \
    --output-dir /home/ubuntu/clawd/Antiskilled/qa_reports \
    --min-score 7.0 >> /tmp/qa.log 2>&1
```

---

## 成本估算

### Claude Sonnet 4（via OpenRouter）

- **输入**: ~4000 tokens（transcript 截断 + audit_result）
- **输出**: ~1500 tokens（评估结果 JSON）
- **单视频成本**: $0.015 - $0.025
- **100 视频**: ~$2.00

### 省钱技巧

1. **用 Claude Haiku 初筛**:
   ```bash
   python evaluate.py batch --model anthropic/claude-haiku-4
   ```
   成本降至 ~$0.003/视频

2. **仅评估异常情况**:
   - signals = 0
   - hype 极值（lexical > 8 或 < 2）
   - summary_sections < 3

3. **批量复用 embedding**（未来优化）

---

## Troubleshooting

### Q: `ModuleNotFoundError: No module named 'openai'`

A: 安装依赖
```bash
pip install openai
```

### Q: API 超时

A: 增加 timeout 或切换模型
```python
# 在 evaluate.py 中修改
response = await self.client.chat.completions.create(
    ...,
    timeout=60.0  # 增加到 60 秒
)
```

### Q: JSON 解析失败

A: Claude 输出格式不稳定，检查 prompt 或手动清洗：
```python
# 在 _parse_evaluation_result 中添加更多容错
```

---

## 贡献

欢迎提交 Issue 或 PR 改进评估框架！

---

**Maintained by**: Claude (OpenClaw Agent)  
**Last Updated**: 2026-01-03
