# Antiskilled QA - 视频处理输出质量评估体系

## 概述

Antiskilled 使用 AI（Grok via pydantic-ai）从 YouTube 财经视频中提取：
- **Trading Signals** — BUY/SELL/HOLD 信号（ticker, conviction, entry/target price）
- **Summary Sections** — 结构化摘要（3-7个板块）
- **Claims** — 可验证断言（方向、目标价、时间窗口）
- **Mentions** — 原文引用（quote + timestamp）

本 skill 提供**系统化质量评估框架**，用 Claude 审计 Grok 的输出，确保数据准确性和可用性。

---

## 评估维度（7 维度，每个 0-10 分）

### 1. 准确性 (Accuracy) 🎯
**核心问题**: 提取的数据是否与视频原文一致？

**评分标准**:
- **10分**: 所有数据完美匹配原文，价格/百分比/日期/ticker 无一错误
- **7-9分**: 主要数据正确，极少量拼写/格式问题（如 TSLA 写成 Tesla）
- **4-6分**: 关键信息正确，但有明显错误（如混淆不同股票的价格）
- **1-3分**: 多处编造数据，张冠李戴
- **0分**: 大面积虚构内容

**检查项**:
- ✅ ticker 符号是否正确（UBER vs UBER.US）
- ✅ 价格数据是否与原文一致（$81.50 vs $80）
- ✅ 百分比精度（35% vs 30%）
- ✅ 时间戳准确性（start_time/end_time 对应实际段落）
- ✅ 公司名称拼写（Alphabet vs Google）
- ✅ 是否编造博主未提及的数字

**扣分项**:
- 价格错误 -2分/处
- ticker 错误 -3分/处
- 时间戳偏差 >30秒 -1分/处
- 编造数据 -5分/处

---

### 2. 完整性 (Completeness) 📦
**核心问题**: 重要信号是否都提取了？有没有遗漏关键内容？

**评分标准**:
- **10分**: 所有重要观点、ticker、价格目标都提取，无遗漏
- **7-9分**: 主要内容完整，遗漏 1-2 个次要信息
- **4-6分**: 缺失明显重要的信号或断言（如博主明确 BUY，但未提取）
- **1-3分**: 提取量 <50%，大量重要内容丢失
- **0分**: 几乎空白或仅提取无关信息

**检查项**:
- ✅ 博主明确提及的所有 ticker 是否都在 signals 中？
- ✅ summary_sections 是否覆盖视频主要话题？
- ✅ 重要价格目标/支撑位/阻力位是否提取？
- ✅ 风险讨论是否记录（risks.mentioned）？
- ✅ 次要 ticker（secondary_tickers）是否完整？

**扣分项**:
- 遗漏主要 ticker -3分/个
- 遗漏明确价格目标 -2分/个
- summary_sections 覆盖率 <70% -2分
- 遗漏重要风险讨论 -1分

---

### 3. 可读性 (Readability) 📖
**核心问题**: 普通人能看懂吗？语言是否自然、简洁、无术语堆砌？

**评分标准**:
- **10分**: 摘要流畅自然，无冗余，普通人可理解
- **7-9分**: 整体清晰，偶有专业术语但不影响理解
- **4-6分**: 有明显的机器味、缩写滥用、逻辑跳跃
- **1-3分**: 充斥术语、语法错误、难以理解
- **0分**: 完全不可读

**检查项**:
- ✅ summary 是否自然流畅（避免"该股票具有高增长潜力"式机器文本）
- ✅ 缩写是否解释（ROIC 应写为 "ROIC (投资回报率)"）
- ✅ 数字格式统一（$81.50 vs 81.5 dollars）
- ✅ 中文翻译自然（如有）
- ✅ 避免重复冗余（"Uber 的 Uber 业务"）

**扣分项**:
- 未解释缩写 -1分/3处
- 机器味明显 -2分
- 语法错误 -1分/3处
- 逻辑不连贯 -2分

---

### 4. 信号质量 (Signal Quality) 📊
**核心问题**: conviction 合理吗？action 方向对吗？reasoning 有说服力吗？

**评分标准**:
- **10分**: conviction 精准反映博主语气，action 与论据一致，reasoning 全面
- **7-9分**: 大体合理，conviction 略有偏差（0.85 vs 0.9）
- **4-6分**: action 判断错误（博主 bullish 但提取为 SELL）或 reasoning 空洞
- **1-3分**: conviction 乱标（非常确定的预测标 0.3），logic_tags 乱贴
- **0分**: 信号与视频内容完全不符

**检查项**:
- ✅ conviction (0.0-1.0) 是否匹配博主语气强度？
  - 博主说 "I'm very confident" → 0.8-0.9
  - 博主说 "Maybe, not sure" → 0.3-0.5
- ✅ action (BUY/SELL/HOLD) 是否与论据一致？
  - 博主说 "deep undervaluation" → BUY
  - 博主说 "overpriced, wait" → HOLD/SELL
- ✅ reasoning 是否包含关键论据（财务数据、催化剂、风险）？
- ✅ logic_tags 是否准确（DCF_Undervalued, AV_Risk 等）？
- ✅ risk_level (LOW/MEDIUM/HIGH) 是否合理？

**扣分项**:
- conviction 明显偏差 -2分
- action 方向错误 -5分
- reasoning 空洞（<50字）-2分
- logic_tags 无关 -1分/个

---

### 5. Hype 评估准确性 (Hype Assessment) 🎪
**核心问题**: hype_dimensions 各维度打分合理吗？与视频实际风格匹配吗？

**hype_dimensions 定义**:
- **lexical** (1-10) — 煽动性词汇（"爆炸式增长！火箭🚀"）
- **urgency** (1-10) — 紧迫感（"今天不买明天涨！"）
- **certainty** (1-10) — 绝对化表述（"100% 会涨"）
- **evidence** (1-10) — 证据薄弱度（越高越弱）
- **risk** (1-10) — 风险忽略度（越高越危险）
- **disclosure** (1-10) — 利益冲突披露（越高越不透明）

**评分标准**:
- **10分**: 所有维度精准，与视频风格完美匹配
- **7-9分**: 大部分维度合理，1-2 个维度偏差 ±1
- **4-6分**: 多个维度偏差 ±2，或误判类型（理性型判成煽动型）
- **1-3分**: 维度乱打，与实际风格严重不符
- **0分**: 完全不符

**检查项**:
- ✅ **lexical**: 是否有"月球🌕"、"diamond hands💎"等词汇？
- ✅ **urgency**: 是否强调"立即行动"、"最后机会"？
- ✅ **certainty**: 是否用"肯定"、"一定"、"100%"？
- ✅ **evidence**: 是否缺乏财务数据支撑？
- ✅ **risk**: 是否完全不提风险？
- ✅ **disclosure**: 是否披露持仓/赞助关系？

**参考范围**:
- **理性型博主**（如本例 CFA）: lexical 2-4, urgency 1-2, certainty 4-6, evidence 1-3, risk 1-3, disclosure 1-3
- **煽动型博主**: lexical 7-10, urgency 8-10, certainty 8-10, evidence 7-10, risk 8-10, disclosure 6-10

**扣分项**:
- 单维度偏差 ±3 -1分/个
- 误判博主类型 -3分
- hype_reason 说明不清 -1分

---

### 6. 结构化质量 (Structural Quality) 🏗️
**核心问题**: summary_sections 数量合理吗？标题多样化吗？highlight_tokens 有用吗？

**评分标准**:
- **10分**: 3-7 个板块，标题准确多样，highlight_tokens 精准提取关键数字
- **7-9分**: 结构合理，标题略有重复，highlight_tokens 基本准确
- **4-6分**: 板块过多/过少（1个或10个），标题雷同，highlight_tokens 缺失
- **1-3分**: 结构混乱，标题无意义，highlight_tokens 错误
- **0分**: 完全无结构

**检查项**:
- ✅ summary_sections 数量: 3-7 个（理想 4-6）
- ✅ 标题多样性: 避免 "Section 1", "Section 2" 或重复词汇
- ✅ 内容覆盖: 是否涵盖视频主要话题？
- ✅ highlight_tokens: 是否提取关键数字/ticker？
  - ✅ 好: ["35%", "17%", "S&P 500"]
  - ❌ 差: ["the", "stock", "market"]
- ✅ emoji 使用合理（可选）

**扣分项**:
- 板块数量 <3 或 >7 -2分
- 标题重复 -1分/对
- highlight_tokens 无关 -1分/3个
- 内容覆盖率 <60% -2分

---

### 7. Claims 质量 (Claims Quality) ⚖️
**核心问题**: 可验证断言提取准确吗？方向、目标价、时间窗口合理吗？

**Claims 数据模型**:
```python
{
  "ticker": "UBER",
  "claim_type": "price_target",  # 或 direction, timeframe, catalyst 等
  "direction": "up",  # up/down/flat/volatile
  "target_price": 154.0,
  "horizon_days": 365,
  "conviction": 0.85,
  "is_falsifiable": True,  # 是否可证伪
  "timestamp_sec": 266.0,
  "source_quote": "DCF intrinsic value $154/share"
}
```

**评分标准**:
- **10分**: Claims 精准可验证，方向/目标价/时间窗口完整准确
- **7-9分**: 主要 Claims 正确，时间窗口略模糊
- **4-6分**: 遗漏重要 Claims，或 is_falsifiable 误判
- **1-3分**: Claims 编造或与原文严重不符
- **0分**: 无 Claims 或完全错误

**检查项**:
- ✅ **完整性**: 博主所有明确预测是否都有 Claim？
- ✅ **可验证性**: is_falsifiable 是否正确？
  - ✅ "UBER will hit $154" → True
  - ❌ "Market is uncertain" → False（太模糊）
- ✅ **方向准确性**: direction 与博主观点一致？
- ✅ **目标价**: target_price 是否提取正确？
- ✅ **时间窗口**: horizon_days 合理吗？
  - 博主说 "this week" → 7 days
  - 博主说 "long-term" → 365-730 days
- ✅ **引用准确**: source_quote 是否为原文？

**扣分项**:
- 遗漏明确 Claim -3分/个
- is_falsifiable 误判 -2分/个
- direction 错误 -3分/个
- target_price 错误 -2分/个
- horizon_days 不合理 -1分/个

---

## 总分计算

**总分** = (Σ 各维度得分) / 7 × 10

**等级划分**:
- **A (9.0-10.0)**: 卓越质量，可直接上线
- **B (7.0-8.9)**: 良好，仅需微调
- **C (5.0-6.9)**: 合格，需改进
- **D (3.0-4.9)**: 不合格，需重新处理
- **F (0.0-2.9)**: 失败，需检查 prompt/模型

---

## 评估方法

### 自动化评估（推荐）

使用 **Claude** 审计 Grok 输出：

**输入**:
- 原始转录文本（transcript.txt）
- AI 输出（audit_result.json）

**输出**:
- 7 维度评分 + 总分
- 具体问题清单（accuracy_issues, completeness_gaps 等）
- 改进建议（recommendations）

**实现**: 见 `evaluate.py`

---

### 手动评估（仅用于标注样本）

1. 观看视频 + 阅读转录文本
2. 对照 AI 输出逐项检查
3. 填写评估表（见 `evaluation_template.json`）

---

## 使用方法

### 单视频评估

```bash
python evaluate.py \
  --transcript /path/to/transcript.txt \
  --audit-result /path/to/audit_result.json \
  --output evaluation.json
```

### 批量评估

```bash
# 评估所有已处理视频
python batch_evaluate.py \
  --video-dir /home/ubuntu/clawd/Antiskilled/temp \
  --output-dir /home/ubuntu/clawd/Antiskilled/qa_reports \
  --min-score 7.0  # 仅输出低于此分数的报告
```

### 生成报告

```bash
# 生成 CSV 报告
python generate_report.py \
  --qa-dir /home/ubuntu/clawd/Antiskilled/qa_reports \
  --output summary.csv

# 生成可视化仪表板
python dashboard.py --qa-dir qa_reports
```

---

## 评估输出格式

```json
{
  "video_id": "-yfJIVV8i7E",
  "evaluated_at": "2026-01-03T10:30:00Z",
  "evaluator": "claude-sonnet-4",
  "scores": {
    "accuracy": 9.0,
    "completeness": 8.5,
    "readability": 9.5,
    "signal_quality": 8.0,
    "hype_assessment": 9.0,
    "structural_quality": 9.0,
    "claims_quality": 7.5
  },
  "total_score": 8.64,
  "grade": "B",
  "issues": {
    "accuracy": [
      "Price $81.50 correct, but current_price also listed as string instead of decimal"
    ],
    "completeness": [
      "Missing secondary ticker GOOGL in Claims (only in Signals)"
    ],
    "claims_quality": [
      "No explicit Claim for '$154 target price', only in Signal.fair_value"
    ]
  },
  "recommendations": [
    "Convert current_price to Decimal type for consistency",
    "Extract DCF $154 target as separate Claim with claim_type='price_target'",
    "Add horizon_days to existing Claims based on '5+ years long-term' mention"
  ],
  "strengths": [
    "Excellent accuracy in financial metrics (ROIC, CAGR)",
    "Comprehensive risk discussion captured",
    "Natural, readable summaries without jargon overload"
  ]
}
```

---

## 持续改进

### Prompt 优化

根据评估结果调整 Grok prompt：
- **准确性低** → 增加"严格按原文提取，禁止编造"指令
- **完整性低** → 添加"遍历所有 ticker，不遗漏任何明确信号"
- **Hype 评估偏差** → 提供更多博主类型示例

### 模型切换

若某类视频持续低分，考虑：
- 长视频（>30min）→ Claude Opus（更强理解力）
- 煽动型博主 → 专门 prompt 模板
- 中文视频 → 添加双语验证

### 质量监控

设置自动化监控：
```bash
# 每日定时评估新处理视频
crontab -e
0 2 * * * /home/ubuntu/clawd/skills/antiskilled-qa/daily_qa.sh
```

若总分 <7.0，自动通知：
```python
if total_score < 7.0:
    send_telegram_alert(f"⚠️ Video {video_id} QA failed: {total_score}/10")
```

---

## 评估数据存储

### 数据库表设计

```sql
CREATE TABLE qa_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID REFERENCES videos(id),
    evaluated_at TIMESTAMPTZ DEFAULT NOW(),
    evaluator VARCHAR(50),  -- 'claude-sonnet-4', 'manual', etc.
    
    -- 评分
    accuracy_score DECIMAL(3,1),
    completeness_score DECIMAL(3,1),
    readability_score DECIMAL(3,1),
    signal_quality_score DECIMAL(3,1),
    hype_assessment_score DECIMAL(3,1),
    structural_quality_score DECIMAL(3,1),
    claims_quality_score DECIMAL(3,1),
    total_score DECIMAL(3,1),
    grade VARCHAR(1),  -- A/B/C/D/F
    
    -- 详细数据 (JSONB)
    issues JSONB,
    recommendations JSONB,
    strengths JSONB,
    
    -- 元数据
    evaluation_duration_seconds INTEGER,
    tokens_used INTEGER,
    
    CONSTRAINT valid_scores CHECK (
        accuracy_score BETWEEN 0 AND 10 AND
        completeness_score BETWEEN 0 AND 10 AND
        total_score BETWEEN 0 AND 10
    )
);

CREATE INDEX idx_qa_evaluations_video_id ON qa_evaluations(video_id);
CREATE INDEX idx_qa_evaluations_grade ON qa_evaluations(grade);
CREATE INDEX idx_qa_evaluations_total_score ON qa_evaluations(total_score);
```

### 查询示例

```sql
-- 最差的 10 个视频
SELECT video_id, total_score, grade 
FROM qa_evaluations 
ORDER BY total_score ASC 
LIMIT 10;

-- 各维度平均分
SELECT 
    AVG(accuracy_score) as avg_accuracy,
    AVG(completeness_score) as avg_completeness,
    AVG(signal_quality_score) as avg_signal_quality
FROM qa_evaluations;

-- 需要重新处理的视频（C 级及以下）
SELECT video_id, total_score, issues
FROM qa_evaluations
WHERE grade IN ('C', 'D', 'F')
ORDER BY total_score ASC;
```

---

## 最佳实践

1. **评估样本选择**:
   - 初期：每批处理 20% 随机抽样评估
   - 稳定后：仅评估异常情况（如 signals=0, hype 极值）

2. **人工复核**:
   - 总分 <5.0 → 100% 人工复核
   - 总分 5.0-7.0 → 30% 抽样复核
   - 总分 >7.0 → 仅异常情况复核

3. **迭代周期**:
   - 每周生成 QA 报告
   - 每月优化 prompt（基于 TOP 10 问题）
   - 每季度评估是否需要切换模型

4. **成本控制**:
   - 使用 Claude Haiku 做初筛（便宜快速）
   - 仅低分视频用 Sonnet 详细评估
   - 批量评估时复用 transcript embedding

---

## Troubleshooting

### Q: 评估分数普遍偏低怎么办？
A: 
1. 检查 transcript 质量（Whisper 转录错误率）
2. 查看是否为特殊类型视频（如中文、印度英语口音）
3. 调整评分标准（可能初期标准过严）

### Q: 评估与人工感知不符？
A: 
1. 收集人工标注样本（至少 50 个）
2. 对比 AI 评估与人工评估的偏差
3. 微调 prompt 或引入人工校准系数

### Q: 评估耗时过长？
A:
1. 启用批量并发（asyncio）
2. 缓存 transcript embedding
3. 仅评估关键维度（accuracy + signal_quality）

---

## 参考资料

- Antiskilled 项目文档: `/home/ubuntu/clawd/Antiskilled/README.md`
- 数据模型定义: `/home/ubuntu/clawd/Antiskilled/models/`
- Prompt 模板: `/home/ubuntu/clawd/Antiskilled/core/business/prompts/`
- 学术论文: `docs/research/FINFLUENCERS_PAPER_ALIGNMENT.md`

---

**版本**: 1.0.0  
**作者**: Claude (OpenClaw Agent)  
**更新**: 2026-01-03
