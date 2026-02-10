#!/usr/bin/env python3
"""
测试示例 - 使用现有视频快速验证 QA 系统
"""

import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from evaluate import AntiskilledQAEvaluator


async def test_with_existing_video():
    """使用已有视频测试"""
    
    # 使用示例视频
    video_dir = Path("/home/ubuntu/clawd/Antiskilled/temp/-yfJIVV8i7E")
    transcript_file = video_dir / "-yfJIVV8i7E_transcript.txt"
    audit_file = video_dir / "-yfJIVV8i7E_audit_result.json"
    
    if not transcript_file.exists() or not audit_file.exists():
        print("❌ 测试文件不存在，请先处理一个视频")
        print(f"   需要: {transcript_file}")
        print(f"   需要: {audit_file}")
        return
    
    print("📊 加载测试数据...")
    with open(transcript_file, 'r', encoding='utf-8') as f:
        transcript = f.read()
    
    with open(audit_file, 'r', encoding='utf-8') as f:
        audit_result = json.load(f)
    
    print(f"✅ Transcript 长度: {len(transcript)} 字符")
    print(f"✅ Signals 数量: {len(audit_result.get('signals', []))}")
    print(f"✅ Summary Sections: {len(audit_result.get('summary_sections', []))}")
    
    # 创建评估器（使用环境变量的 API Key）
    import os
    api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        print("\n❌ 请设置环境变量 OPENROUTER_API_KEY")
        print("   export OPENROUTER_API_KEY='sk-or-v1-...'")
        return
    
    print(f"\n🤖 使用模型: anthropic/claude-sonnet-4")
    print("⏳ 开始评估...\n")
    
    evaluator = AntiskilledQAEvaluator(
        api_key=api_key,
        model="anthropic/claude-sonnet-4"
    )
    
    # 执行评估
    result = await evaluator.evaluate(
        transcript=transcript,
        audit_result=audit_result,
        video_id="-yfJIVV8i7E"
    )
    
    # 打印结果
    print(f"{'='*60}")
    print(f"🎯 评估完成")
    print(f"{'='*60}")
    print(f"\n📹 Video ID: {result.video_id}")
    print(f"⏱️  Duration: {result.evaluation_duration_seconds}s")
    print(f"🔢 Tokens Used: {result.tokens_used}")
    print(f"\n🎯 Total Score: {result.total_score}/10")
    print(f"📊 Grade: {result.grade}")
    
    print(f"\n📈 Dimension Scores:")
    print(f"  ✓ Accuracy:          {result.accuracy.score}/10")
    print(f"  ✓ Completeness:      {result.completeness.score}/10")
    print(f"  ✓ Readability:       {result.readability.score}/10")
    print(f"  ✓ Signal Quality:    {result.signal_quality.score}/10")
    print(f"  ✓ Hype Assessment:   {result.hype_assessment.score}/10")
    print(f"  ✓ Structural:        {result.structural_quality.score}/10")
    print(f"  ✓ Claims Quality:    {result.claims_quality.score}/10")
    
    if result.accuracy.issues:
        print(f"\n❌ Accuracy Issues ({len(result.accuracy.issues)}):")
        for issue in result.accuracy.issues[:3]:
            print(f"  - {issue}")
    
    if result.completeness.issues:
        print(f"\n⚠️  Completeness Issues ({len(result.completeness.issues)}):")
        for issue in result.completeness.issues[:3]:
            print(f"  - {issue}")
    
    if result.recommendations:
        print(f"\n💡 Top Recommendations:")
        for i, rec in enumerate(result.recommendations[:5], 1):
            print(f"  {i}. {rec}")
    
    if result.strengths:
        print(f"\n✨ Strengths:")
        for i, strength in enumerate(result.strengths[:5], 1):
            print(f"  {i}. {strength}")
    
    print(f"\n{'='*60}")
    
    # 保存结果
    output_file = Path("/tmp/antiskilled_qa_test.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 完整报告已保存: {output_file}")
    print(f"\n✅ 测试完成！")


if __name__ == '__main__':
    asyncio.run(test_with_existing_video())
