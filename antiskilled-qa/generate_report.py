#!/usr/bin/env python3
"""
生成 QA 评估报告（CSV + 可视化）
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any
import argparse
from collections import defaultdict


def load_qa_results(qa_dir: Path) -> List[Dict[str, Any]]:
    """加载所有 QA 评估结果"""
    results = []
    
    for qa_file in qa_dir.glob("*_qa.json"):
        with open(qa_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            results.append(data)
    
    return results


def generate_csv_report(results: List[Dict[str, Any]], output_path: Path):
    """生成 CSV 报告"""
    if not results:
        print("⚠️  无数据可导出")
        return
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # 表头
        writer.writerow([
            'video_id',
            'total_score',
            'grade',
            'accuracy',
            'completeness',
            'readability',
            'signal_quality',
            'hype_assessment',
            'structural_quality',
            'claims_quality',
            'issues_count',
            'recommendations_count',
            'evaluated_at'
        ])
        
        # 数据行
        for result in results:
            scores = result['scores']
            issues_count = sum(len(v) for v in result['issues'].values())
            
            writer.writerow([
                result['video_id'],
                result['total_score'],
                result['grade'],
                scores['accuracy_score'],
                scores['completeness_score'],
                scores['readability_score'],
                scores['signal_quality_score'],
                scores['hype_assessment_score'],
                scores['structural_quality_score'],
                scores['claims_quality_score'],
                issues_count,
                len(result.get('recommendations', [])),
                result['evaluated_at']
            ])
    
    print(f"✅ CSV 报告已生成: {output_path}")


def generate_summary_stats(results: List[Dict[str, Any]]):
    """生成统计摘要"""
    if not results:
        print("⚠️  无数据可统计")
        return
    
    total = len(results)
    
    # 等级分布
    grade_counts = defaultdict(int)
    for result in results:
        grade_counts[result['grade']] += 1
    
    # 维度平均分
    dim_scores = defaultdict(list)
    for result in results:
        for dim, score in result['scores'].items():
            dim_scores[dim].append(score)
    
    dim_averages = {
        dim: sum(scores) / len(scores)
        for dim, scores in dim_scores.items()
    }
    
    # 最常见问题
    all_issues = defaultdict(int)
    for result in results:
        for dim, issues in result['issues'].items():
            for issue in issues:
                all_issues[issue] += 1
    
    top_issues = sorted(all_issues.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # 打印统计
    print(f"\n{'='*60}")
    print(f"📊 QA 评估统计摘要")
    print(f"{'='*60}")
    
    print(f"\n📦 总视频数: {total}")
    
    print(f"\n🎯 等级分布:")
    for grade in ['A', 'B', 'C', 'D', 'F']:
        count = grade_counts.get(grade, 0)
        pct = count / total * 100
        bar = '█' * int(pct / 5)
        print(f"  {grade}: {count:3d} ({pct:5.1f}%) {bar}")
    
    print(f"\n📈 维度平均分:")
    for dim in ['accuracy_score', 'completeness_score', 'readability_score',
                'signal_quality_score', 'hype_assessment_score',
                'structural_quality_score', 'claims_quality_score']:
        avg = dim_averages[dim]
        status = "✅" if avg >= 8.0 else "⚠️" if avg >= 6.0 else "❌"
        dim_name = dim.replace('_score', '')
        print(f"  {status} {dim_name:20s}: {avg:.2f}/10")
    
    print(f"\n🔥 Top 10 常见问题:")
    for i, (issue, count) in enumerate(top_issues, 1):
        pct = count / total * 100
        print(f"  {i:2d}. [{count:2d}个视频 {pct:4.1f}%] {issue[:70]}")
    
    print(f"\n{'='*60}\n")


def generate_html_report(results: List[Dict[str, Any]], output_path: Path):
    """生成 HTML 可视化报告"""
    if not results:
        print("⚠️  无数据可生成")
        return
    
    # 简单的 HTML 模板
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Antiskilled QA Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .summary { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .video-card { background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
        .score { font-size: 24px; font-weight: bold; }
        .grade-A { color: #22c55e; }
        .grade-B { color: #84cc16; }
        .grade-C { color: #eab308; }
        .grade-D { color: #f97316; }
        .grade-F { color: #ef4444; }
        .dimension { display: inline-block; margin: 5px; padding: 5px 10px; background: #e5e7eb; border-radius: 4px; }
        .issues { color: #dc2626; font-size: 14px; }
        .recommendations { color: #2563eb; font-size: 14px; }
    </style>
</head>
<body>
    <h1>📊 Antiskilled QA Evaluation Report</h1>
    
    <div class="summary">
        <h2>Summary</h2>
        <p>Total Videos: <strong>{total}</strong></p>
        <p>Average Score: <strong>{avg_score:.2f}/10</strong></p>
    </div>
    
    <h2>Videos</h2>
    {video_cards}
</body>
</html>
"""
    
    # 计算统计
    total = len(results)
    avg_score = sum(r['total_score'] for r in results) / total
    
    # 生成视频卡片
    video_cards = []
    for result in sorted(results, key=lambda x: x['total_score']):
        grade = result['grade']
        video_card = f"""
    <div class="video-card">
        <h3>{result['video_id']}</h3>
        <p>
            <span class="score grade-{grade}">{result['total_score']}/10</span>
            <span style="color: #666;">Grade: {grade}</span>
        </p>
        <div>
            {' '.join(f'<span class="dimension">{k.replace("_score", "")}: {v:.1f}</span>' for k, v in result['scores'].items())}
        </div>
        <div class="issues">
            <strong>Issues ({sum(len(v) for v in result["issues"].values())}):</strong>
            {', '.join(sum(result['issues'].values(), [])[:3])}
        </div>
        <div class="recommendations">
            <strong>Recommendations:</strong> {'; '.join(result.get('recommendations', [])[:2])}
        </div>
    </div>
"""
        video_cards.append(video_card)
    
    # 填充模板
    final_html = html.format(
        total=total,
        avg_score=avg_score,
        video_cards='\n'.join(video_cards)
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"✅ HTML 报告已生成: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="生成 QA 评估报告")
    parser.add_argument('--qa-dir', required=True, help='QA 评估结果目录')
    parser.add_argument('--output', required=True, help='输出路径（.csv 或 .html）')
    parser.add_argument('--stats', action='store_true', help='打印统计摘要')
    
    args = parser.parse_args()
    
    qa_dir = Path(args.qa_dir)
    output_path = Path(args.output)
    
    if not qa_dir.exists():
        print(f"❌ 目录不存在: {qa_dir}")
        return
    
    # 加载数据
    print(f"🔍 加载 QA 结果: {qa_dir}")
    results = load_qa_results(qa_dir)
    print(f"✅ 加载 {len(results)} 个评估结果")
    
    # 生成报告
    if output_path.suffix == '.csv':
        generate_csv_report(results, output_path)
    elif output_path.suffix == '.html':
        generate_html_report(results, output_path)
    else:
        print("❌ 不支持的输出格式（仅支持 .csv 和 .html）")
        return
    
    # 打印统计
    if args.stats or not results:
        generate_summary_stats(results)


if __name__ == '__main__':
    main()
