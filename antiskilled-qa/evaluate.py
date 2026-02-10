#!/usr/bin/env python3
"""
Antiskilled QA Evaluator
使用 Claude 评估 Grok 视频处理输出质量
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import asyncio

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Antiskilled"))

try:
    from openai import AsyncOpenAI
except ImportError:
    print("❌ 请安装 openai: pip install openai")
    sys.exit(1)


@dataclass
class DimensionScore:
    """单个维度评分"""
    score: float  # 0-10
    issues: List[str]  # 问题列表
    examples: List[str]  # 具体示例


@dataclass
class QAResult:
    """完整评估结果"""
    video_id: str
    evaluated_at: str
    evaluator: str
    
    # 7 维度评分
    accuracy: DimensionScore
    completeness: DimensionScore
    readability: DimensionScore
    signal_quality: DimensionScore
    hype_assessment: DimensionScore
    structural_quality: DimensionScore
    claims_quality: DimensionScore
    
    # 总分
    total_score: float
    grade: str  # A/B/C/D/F
    
    # 综合反馈
    recommendations: List[str]
    strengths: List[str]
    
    # 元数据
    evaluation_duration_seconds: float
    tokens_used: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        result = asdict(self)
        # 将 DimensionScore 展开
        scores = {}
        issues = {}
        for dim in ['accuracy', 'completeness', 'readability', 'signal_quality', 
                    'hype_assessment', 'structural_quality', 'claims_quality']:
            dim_data = result.pop(dim)
            scores[f"{dim}_score"] = dim_data['score']
            issues[dim] = dim_data['issues']
        
        result['scores'] = scores
        result['issues'] = issues
        return result


class AntiskilledQAEvaluator:
    """QA 评估器"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "anthropic/claude-sonnet-4",
        base_url: str = "https://openrouter.ai/api/v1"
    ):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model
    
    async def evaluate(
        self,
        transcript: str,
        audit_result: Dict[str, Any],
        video_id: Optional[str] = None
    ) -> QAResult:
        """
        评估单个视频的 AI 输出质量
        
        Args:
            transcript: 原始转录文本
            audit_result: AI 输出 (audit_result.json)
            video_id: 视频 ID（可选）
        
        Returns:
            QAResult 评估结果
        """
        start_time = datetime.now()
        
        # 构建评估 prompt
        prompt = self._build_evaluation_prompt(transcript, audit_result)
        
        # 调用 Claude
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # 低温度保证一致性
            max_tokens=4000
        )
        
        # 解析响应
        result_text = response.choices[0].message.content
        result_data = self._parse_evaluation_result(result_text)
        
        # 计算总分和等级
        dimension_scores = [
            result_data['accuracy']['score'],
            result_data['completeness']['score'],
            result_data['readability']['score'],
            result_data['signal_quality']['score'],
            result_data['hype_assessment']['score'],
            result_data['structural_quality']['score'],
            result_data['claims_quality']['score']
        ]
        total_score = sum(dimension_scores) / len(dimension_scores)
        grade = self._calculate_grade(total_score)
        
        # 构建结果
        duration = (datetime.now() - start_time).total_seconds()
        
        qa_result = QAResult(
            video_id=video_id or audit_result.get('video_metadata', {}).get('video_id', 'unknown'),
            evaluated_at=datetime.now().isoformat(),
            evaluator=self.model,
            accuracy=DimensionScore(**result_data['accuracy']),
            completeness=DimensionScore(**result_data['completeness']),
            readability=DimensionScore(**result_data['readability']),
            signal_quality=DimensionScore(**result_data['signal_quality']),
            hype_assessment=DimensionScore(**result_data['hype_assessment']),
            structural_quality=DimensionScore(**result_data['structural_quality']),
            claims_quality=DimensionScore(**result_data['claims_quality']),
            total_score=round(total_score, 2),
            grade=grade,
            recommendations=result_data['recommendations'],
            strengths=result_data['strengths'],
            evaluation_duration_seconds=round(duration, 2),
            tokens_used=response.usage.total_tokens if response.usage else None
        )
        
        return qa_result
    
    def _get_system_prompt(self) -> str:
        """系统 prompt"""
        return """你是 Antiskilled 平台的 QA 审计员，负责评估 AI 从财经视频中提取的数据质量。

你的任务是按照 7 个维度严格评分（0-10 分），找出问题，提供改进建议。

评分标准：
- **准确性 (Accuracy)**: 数据与原文一致性（ticker, 价格, 百分比, 时间戳）
- **完整性 (Completeness)**: 是否遗漏重要信号或观点
- **可读性 (Readability)**: 语言自然流畅，无术语堆砌
- **信号质量 (Signal Quality)**: conviction/action/reasoning 是否合理
- **Hype 评估 (Hype Assessment)**: hype_dimensions 各维度打分是否准确
- **结构化质量 (Structural Quality)**: summary_sections 数量/标题/highlight_tokens
- **Claims 质量 (Claims Quality)**: 可验证断言提取准确性

输出格式：严格 JSON，包含每个维度的 score/issues/examples，以及 recommendations/strengths。

评分务必客观严格，不要因为整体不错就全打高分。"""

    def _build_evaluation_prompt(self, transcript: str, audit_result: Dict[str, Any]) -> str:
        """构建评估 prompt"""
        # 提取关键数据
        signals = audit_result.get('signals', [])
        summary_sections = audit_result.get('summary_sections', [])
        claims = audit_result.get('llm_response_processed', {}).get('claims', [])
        
        # 截断过长的 transcript（保留前 8000 字符）
        transcript_preview = transcript[:8000]
        if len(transcript) > 8000:
            transcript_preview += "\n\n[... 转录文本已截断，仅展示前 8000 字符 ...]"
        
        prompt = f"""请评估以下 AI 视频处理输出的质量。

# 原始转录文本
```
{transcript_preview}
```

# AI 输出数据

## Signals ({len(signals)} 个)
```json
{json.dumps(signals, indent=2, ensure_ascii=False)}
```

## Summary Sections ({len(summary_sections)} 个)
```json
{json.dumps(summary_sections, indent=2, ensure_ascii=False)}
```

## Claims (如有)
```json
{json.dumps(claims, indent=2, ensure_ascii=False) if claims else "[]"}
```

## Hype Dimensions
```json
{json.dumps(signals[0].get('hype_dimensions', {}) if signals else {}, indent=2, ensure_ascii=False)}
```

---

请按照以下 JSON 格式输出评估结果：

```json
{{
  "accuracy": {{
    "score": 9.0,
    "issues": ["价格 $81.50 正确，但 current_price 为字符串而非 Decimal"],
    "examples": ["✅ ROIC 21.8% 准确", "❌ current_price 应为数字类型"]
  }},
  "completeness": {{
    "score": 8.5,
    "issues": ["遗漏次要 ticker GOOGL 在 Claims 中"],
    "examples": ["✅ 主要 ticker UBER 完整", "⚠️ secondary_tickers 仅在 Signals 中"]
  }},
  "readability": {{
    "score": 9.5,
    "issues": [],
    "examples": ["✅ Summary 流畅自然", "✅ 无术语堆砌"]
  }},
  "signal_quality": {{
    "score": 8.0,
    "issues": ["conviction 0.85 略高，博主有 'not top buy for 2026' 保留"],
    "examples": ["✅ action=BUY 合理", "⚠️ conviction 可调至 0.75-0.8"]
  }},
  "hype_assessment": {{
    "score": 9.0,
    "issues": [],
    "examples": ["✅ lexical=3.2 准确（无煽动词汇）", "✅ certainty=4.8 合理（有数据支撑）"]
  }},
  "structural_quality": {{
    "score": 9.0,
    "issues": [],
    "examples": ["✅ 7 个 sections 合理", "✅ highlight_tokens 提取准确"]
  }},
  "claims_quality": {{
    "score": 7.5,
    "issues": ["DCF $154 目标价未提取为独立 Claim"],
    "examples": ["⚠️ fair_value 应同步生成 price_target Claim"]
  }},
  "recommendations": [
    "将 current_price 转为 Decimal 类型保持一致性",
    "从 fair_value=$154 生成独立 Claim (claim_type='price_target')",
    "conviction 微调至 0.75-0.8 以反映博主保留态度"
  ],
  "strengths": [
    "财务指标（ROIC, CAGR）提取精准",
    "风险讨论全面（AV 竞争, Tesla/Alphabet）",
    "Summary 可读性强，无机器味"
  ]
}}
```

务必客观严格，不要因为整体不错就全打高分。找出所有可改进之处。"""
        
        return prompt
    
    def _parse_evaluation_result(self, result_text: str) -> Dict[str, Any]:
        """解析 Claude 返回的评估结果"""
        # 提取 JSON（可能被 ```json 包裹）
        import re
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', result_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析整个文本
            json_str = result_text
        
        try:
            data = json.loads(json_str)
            
            # 验证必需字段
            required_dims = ['accuracy', 'completeness', 'readability', 'signal_quality',
                           'hype_assessment', 'structural_quality', 'claims_quality']
            for dim in required_dims:
                if dim not in data:
                    raise ValueError(f"Missing dimension: {dim}")
                if 'score' not in data[dim]:
                    raise ValueError(f"Missing score in {dim}")
            
            if 'recommendations' not in data:
                data['recommendations'] = []
            if 'strengths' not in data:
                data['strengths'] = []
            
            # 确保每个维度有 issues 和 examples
            for dim in required_dims:
                if 'issues' not in data[dim]:
                    data[dim]['issues'] = []
                if 'examples' not in data[dim]:
                    data[dim]['examples'] = []
            
            return data
        
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败: {e}")
            print(f"原始输出:\n{result_text}")
            raise
    
    def _calculate_grade(self, total_score: float) -> str:
        """计算等级"""
        if total_score >= 9.0:
            return 'A'
        elif total_score >= 7.0:
            return 'B'
        elif total_score >= 5.0:
            return 'C'
        elif total_score >= 3.0:
            return 'D'
        else:
            return 'F'


async def evaluate_video(
    transcript_path: Path,
    audit_result_path: Path,
    output_path: Path,
    api_key: str,
    model: str = "anthropic/claude-sonnet-4"
):
    """评估单个视频"""
    print(f"📊 评估视频: {audit_result_path.name}")
    
    # 读取数据
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript = f.read()
    
    with open(audit_result_path, 'r', encoding='utf-8') as f:
        audit_result = json.load(f)
    
    # 创建评估器
    evaluator = AntiskilledQAEvaluator(api_key=api_key, model=model)
    
    # 执行评估
    result = await evaluator.evaluate(transcript, audit_result)
    
    # 输出结果
    output_data = result.to_dict()
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # 打印摘要
    print(f"\n{'='*60}")
    print(f"📹 Video: {result.video_id}")
    print(f"⏱️  Duration: {result.evaluation_duration_seconds}s")
    print(f"🎯 Total Score: {result.total_score}/10 (Grade: {result.grade})")
    print(f"\n📈 Dimension Scores:")
    for dim in ['accuracy', 'completeness', 'readability', 'signal_quality',
                'hype_assessment', 'structural_quality', 'claims_quality']:
        score = output_data['scores'][f"{dim}_score"]
        issues_count = len(output_data['issues'][dim])
        status = "✅" if score >= 8.0 else "⚠️" if score >= 6.0 else "❌"
        print(f"  {status} {dim:20s}: {score}/10  ({issues_count} issues)")
    
    print(f"\n💡 Key Recommendations:")
    for i, rec in enumerate(result.recommendations[:3], 1):
        print(f"  {i}. {rec}")
    
    print(f"\n✨ Strengths:")
    for i, strength in enumerate(result.strengths[:3], 1):
        print(f"  {i}. {strength}")
    
    print(f"\n💾 Report saved: {output_path}")
    print(f"{'='*60}\n")
    
    return result


async def batch_evaluate(
    video_dir: Path,
    output_dir: Path,
    api_key: str,
    model: str = "anthropic/claude-sonnet-4",
    min_score: float = 0.0,
    max_videos: Optional[int] = None
):
    """批量评估所有视频"""
    print(f"🔍 扫描视频目录: {video_dir}")
    
    # 查找所有 audit_result.json
    audit_files = list(video_dir.glob("*/*_audit_result.json"))
    
    if not audit_files:
        print("❌ 未找到任何 audit_result.json 文件")
        return
    
    if max_videos:
        audit_files = audit_files[:max_videos]
    
    print(f"📦 找到 {len(audit_files)} 个视频，开始评估...\n")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    failed = []
    
    for i, audit_file in enumerate(audit_files, 1):
        video_id = audit_file.stem.replace('_audit_result', '')
        transcript_file = audit_file.parent / f"{video_id}_transcript.txt"
        
        if not transcript_file.exists():
            print(f"⚠️  [{i}/{len(audit_files)}] 跳过 {video_id}: 缺少 transcript")
            failed.append(video_id)
            continue
        
        output_file = output_dir / f"{video_id}_qa.json"
        
        try:
            result = await evaluate_video(
                transcript_file,
                audit_file,
                output_file,
                api_key,
                model
            )
            
            # 仅保存低分视频
            if result.total_score < min_score:
                results.append(result)
            else:
                print(f"✅ [{i}/{len(audit_files)}] {video_id}: {result.total_score}/10 (达标，不保存)")
                output_file.unlink()  # 删除高分报告
        
        except Exception as e:
            print(f"❌ [{i}/{len(audit_files)}] 评估失败 {video_id}: {e}")
            failed.append(video_id)
    
    # 生成汇总报告
    summary_file = output_dir / "summary.json"
    summary = {
        "evaluated_at": datetime.now().isoformat(),
        "total_videos": len(audit_files),
        "successful": len(results),
        "failed": len(failed),
        "failed_videos": failed,
        "low_score_videos": [
            {
                "video_id": r.video_id,
                "total_score": r.total_score,
                "grade": r.grade
            }
            for r in sorted(results, key=lambda x: x.total_score)
        ]
    }
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"📊 批量评估完成")
    print(f"  总视频数: {len(audit_files)}")
    print(f"  成功评估: {len(results)}")
    print(f"  失败: {len(failed)}")
    print(f"  低分视频 (<{min_score}): {len(results)}")
    print(f"\n📄 汇总报告: {summary_file}")
    print(f"{'='*60}")


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Antiskilled QA Evaluator - 评估 AI 视频处理质量"
    )
    
    # 通用参数
    parser.add_argument(
        '--api-key',
        help='OpenRouter API Key (或设置环境变量 OPENROUTER_API_KEY)',
        default=None
    )
    parser.add_argument(
        '--model',
        help='Claude 模型',
        default='anthropic/claude-sonnet-4'
    )
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # single 命令：评估单个视频
    single_parser = subparsers.add_parser('single', help='评估单个视频')
    single_parser.add_argument('--transcript', required=True, help='转录文本路径')
    single_parser.add_argument('--audit-result', required=True, help='审计结果 JSON 路径')
    single_parser.add_argument('--output', required=True, help='输出评估报告路径')
    
    # batch 命令：批量评估
    batch_parser = subparsers.add_parser('batch', help='批量评估视频')
    batch_parser.add_argument('--video-dir', required=True, help='视频目录（包含子文件夹）')
    batch_parser.add_argument('--output-dir', required=True, help='输出目录')
    batch_parser.add_argument('--min-score', type=float, default=7.0, help='仅保存低于此分数的报告')
    batch_parser.add_argument('--max-videos', type=int, help='最多评估多少个视频')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 获取 API Key
    api_key = args.api_key or os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ 请提供 API Key: --api-key 或设置环境变量 OPENROUTER_API_KEY")
        sys.exit(1)
    
    # 执行命令
    if args.command == 'single':
        asyncio.run(evaluate_video(
            Path(args.transcript),
            Path(args.audit_result),
            Path(args.output),
            api_key,
            args.model
        ))
    
    elif args.command == 'batch':
        asyncio.run(batch_evaluate(
            Path(args.video_dir),
            Path(args.output_dir),
            api_key,
            args.model,
            args.min_score,
            args.max_videos
        ))


if __name__ == '__main__':
    import os
    main()
