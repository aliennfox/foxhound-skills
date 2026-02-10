#!/usr/bin/env python3
"""
将 QA 评估结果保存到 Supabase 数据库
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any
import asyncio

# 添加 Antiskilled 项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Antiskilled"))

try:
    from database.db_manager import db_manager
except ImportError:
    print("❌ 无法导入 db_manager，请确保在 Antiskilled 环境中运行")
    sys.exit(1)


async def save_qa_result_to_db(qa_result: Dict[str, Any]) -> str:
    """
    保存 QA 结果到数据库
    
    Args:
        qa_result: QA 评估结果字典（来自 evaluate.py 的输出）
    
    Returns:
        插入的记录 ID
    """
    # 查询 video_id 对应的 UUID
    video_id_str = qa_result['video_id']
    
    # 如果是 YouTube ID，查询数据库获取 UUID
    if len(video_id_str) <= 20:  # YouTube ID 通常 11 字符
        result = await db_manager.supabase.table('videos').select('id').eq(
            'youtube_video_id', video_id_str
        ).limit(1).execute()
        
        if not result.data:
            raise ValueError(f"Video not found in database: {video_id_str}")
        
        video_uuid = result.data[0]['id']
    else:
        # 已经是 UUID
        video_uuid = video_id_str
    
    # 构建插入数据
    insert_data = {
        'video_id': video_uuid,
        'evaluated_at': qa_result['evaluated_at'],
        'evaluator': qa_result['evaluator'],
        
        # 评分
        'accuracy_score': qa_result['scores']['accuracy_score'],
        'completeness_score': qa_result['scores']['completeness_score'],
        'readability_score': qa_result['scores']['readability_score'],
        'signal_quality_score': qa_result['scores']['signal_quality_score'],
        'hype_assessment_score': qa_result['scores']['hype_assessment_score'],
        'structural_quality_score': qa_result['scores']['structural_quality_score'],
        'claims_quality_score': qa_result['scores']['claims_quality_score'],
        
        'total_score': qa_result['total_score'],
        'grade': qa_result['grade'],
        
        # JSONB 字段
        'issues': qa_result['issues'],
        'recommendations': qa_result.get('recommendations', []),
        'strengths': qa_result.get('strengths', []),
        
        # 元数据
        'evaluation_duration_seconds': int(qa_result['evaluation_duration_seconds']),
        'tokens_used': qa_result.get('tokens_used')
    }
    
    # 插入数据库
    result = await db_manager.supabase.table('qa_evaluations').insert(
        insert_data
    ).execute()
    
    if not result.data:
        raise Exception("Failed to insert QA evaluation")
    
    record_id = result.data[0]['id']
    print(f"✅ QA 评估已保存到数据库: {record_id}")
    
    return record_id


async def batch_save_qa_results(qa_dir: Path):
    """批量保存 QA 结果"""
    qa_files = list(qa_dir.glob("*_qa.json"))
    
    if not qa_files:
        print(f"❌ 未找到 QA 结果文件: {qa_dir}")
        return
    
    print(f"📦 找到 {len(qa_files)} 个 QA 结果文件")
    
    success = 0
    failed = []
    
    for qa_file in qa_files:
        try:
            with open(qa_file, 'r', encoding='utf-8') as f:
                qa_result = json.load(f)
            
            await save_qa_result_to_db(qa_result)
            success += 1
        
        except Exception as e:
            print(f"❌ 保存失败 {qa_file.name}: {e}")
            failed.append(qa_file.name)
    
    print(f"\n{'='*60}")
    print(f"📊 批量保存完成")
    print(f"  成功: {success}")
    print(f"  失败: {len(failed)}")
    if failed:
        print(f"  失败文件: {', '.join(failed)}")
    print(f"{'='*60}")


async def query_qa_summary():
    """查询 QA 评估汇总"""
    result = await db_manager.supabase.table('qa_evaluation_summary').select('*').limit(10).execute()
    
    if not result.data:
        print("⚠️  暂无评估数据")
        return
    
    print(f"\n{'='*60}")
    print(f"📊 QA 评估汇总（最近 10 天）")
    print(f"{'='*60}")
    
    for row in result.data:
        print(f"\n📅 {row['evaluation_date']} - {row['evaluator']}")
        print(f"  评估数量: {row['total_evaluations']}")
        print(f"  平均分: {row['avg_total_score']:.2f}/10")
        print(f"  等级分布: A={row['grade_a_count']} B={row['grade_b_count']} C={row['grade_c_count']} D={row['grade_d_count']} F={row['grade_f_count']}")
        print(f"  维度平均分:")
        print(f"    Accuracy: {row['avg_accuracy']:.2f}")
        print(f"    Completeness: {row['avg_completeness']:.2f}")
        print(f"    Signal Quality: {row['avg_signal_quality']:.2f}")


async def query_worst_videos(limit: int = 10):
    """查询最差的视频"""
    result = await db_manager.supabase.rpc(
        'get_worst_qa_videos',
        {'limit_count': limit}
    ).execute()
    
    if not result.data:
        print("⚠️  暂无评估数据")
        return
    
    print(f"\n{'='*60}")
    print(f"📉 最差的 {limit} 个视频")
    print(f"{'='*60}")
    
    for i, row in enumerate(result.data, 1):
        print(f"\n{i}. Video: {row['video_id']}")
        print(f"   Score: {row['total_score']}/10 (Grade: {row['grade']})")
        print(f"   Evaluated: {row['evaluated_at']}")
        if row['main_issues']:
            print(f"   Issues:")
            for issue in row['main_issues'][:3]:
                print(f"     - {issue}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="保存 QA 结果到数据库")
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # save 命令
    save_parser = subparsers.add_parser('save', help='保存单个 QA 结果')
    save_parser.add_argument('--qa-file', required=True, help='QA 结果 JSON 文件')
    
    # batch 命令
    batch_parser = subparsers.add_parser('batch', help='批量保存 QA 结果')
    batch_parser.add_argument('--qa-dir', required=True, help='QA 结果目录')
    
    # query 命令
    query_parser = subparsers.add_parser('query', help='查询评估统计')
    query_parser.add_argument('--type', choices=['summary', 'worst'], default='summary', help='查询类型')
    query_parser.add_argument('--limit', type=int, default=10, help='限制数量（仅用于 worst）')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 执行命令
    if args.command == 'save':
        qa_file = Path(args.qa_file)
        if not qa_file.exists():
            print(f"❌ 文件不存在: {qa_file}")
            sys.exit(1)
        
        with open(qa_file, 'r', encoding='utf-8') as f:
            qa_result = json.load(f)
        
        asyncio.run(save_qa_result_to_db(qa_result))
    
    elif args.command == 'batch':
        qa_dir = Path(args.qa_dir)
        if not qa_dir.exists():
            print(f"❌ 目录不存在: {qa_dir}")
            sys.exit(1)
        
        asyncio.run(batch_save_qa_results(qa_dir))
    
    elif args.command == 'query':
        if args.type == 'summary':
            asyncio.run(query_qa_summary())
        elif args.type == 'worst':
            asyncio.run(query_worst_videos(args.limit))


if __name__ == '__main__':
    main()
