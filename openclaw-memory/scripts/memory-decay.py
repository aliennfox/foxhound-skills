#!/usr/bin/env python3
"""
Memory Decay — Ebbinghaus forgetting curve for Mem0

Analyzes memory age and removes stale entries based on exponential decay.

Usage:
  python3 scripts/memory-decay.py                          # Report only
  python3 scripts/memory-decay.py --cleanup --dry-run      # Preview cleanup
  python3 scripts/memory-decay.py --cleanup                # Execute cleanup
  python3 scripts/memory-decay.py --half-life 45           # Custom half-life
  python3 scripts/memory-decay.py --threshold 0.05         # Custom threshold

Decay formula:
  retention = e^(-age_days / half_life)
  Default: half_life=30d, threshold=10% → cleanup at ~69 days
"""

import os
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# --- Auto-detect workspace ---
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = Path(os.environ.get("WORKSPACE", SCRIPT_DIR.parent))
for candidate in [WORKSPACE, SCRIPT_DIR.parent, SCRIPT_DIR.parent.parent]:
    if (candidate / "MEMORY.md").exists() or (candidate / "memory").is_dir():
        WORKSPACE = candidate
        break

load_dotenv(WORKSPACE / ".env")

CONFIG_PATH = WORKSPACE / "config" / "mem0_config.json"
DEFAULT_HALF_LIFE = 30
DEFAULT_THRESHOLD = 0.1


def get_mem0():
    from mem0 import Memory
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    config["llm"]["config"]["api_key"] = os.getenv("GEMINI_API_KEY")
    config["embedder"]["config"]["api_key"] = os.getenv("GEMINI_API_KEY")
    return Memory.from_config(config)


def calculate_retention(created_at, half_life=DEFAULT_HALF_LIFE):
    """Calculate memory retention based on age"""
    if not created_at:
        return 1.0
    try:
        if isinstance(created_at, str):
            created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        else:
            created = created_at
        age_days = (datetime.now(created.tzinfo) - created).total_seconds() / 86400
        return math.exp(-age_days / half_life)
    except Exception:
        return 1.0


def analyze_memories(user_id, half_life=DEFAULT_HALF_LIFE, threshold=DEFAULT_THRESHOLD):
    """Analyze all memories and calculate decay scores"""
    m = get_mem0()
    all_mem = m.get_all(user_id=user_id)
    results = all_mem.get('results', [])

    analysis = {
        'total': len(results),
        'keep': [],
        'decay_candidates': [],
        'no_timestamp': []
    }

    for mem in results:
        memory_text = mem.get('memory', '')
        mem_id = mem.get('id', '')
        created_at = mem.get('created_at', '')
        updated_at = mem.get('updated_at', '')
        timestamp = updated_at or created_at
        retention = calculate_retention(timestamp, half_life)

        entry = {
            'id': mem_id,
            'memory': memory_text[:100],
            'created_at': str(created_at)[:19] if created_at else 'N/A',
            'retention': round(retention, 3)
        }

        if not timestamp:
            analysis['no_timestamp'].append(entry)
        elif retention < threshold:
            analysis['decay_candidates'].append(entry)
        else:
            analysis['keep'].append(entry)

    return analysis, m


def print_report(analysis):
    """Print decay analysis report"""
    print("=" * 60)
    print("Memory Decay Analysis")
    print("=" * 60)
    print(f"Total memories: {analysis['total']}")
    print(f"Keep: {len(analysis['keep'])}")
    print(f"Decay candidates: {len(analysis['decay_candidates'])}")
    print(f"No timestamp: {len(analysis['no_timestamp'])}")

    if analysis['decay_candidates']:
        print(f"\n🗑️  Decay candidates (below threshold):")
        for mem in analysis['decay_candidates']:
            print(f"  [{mem['retention']:.1%}] {mem['memory']}")

    if analysis['keep']:
        print(f"\n✅ Keeping ({len(analysis['keep'])}):")
        for mem in sorted(analysis['keep'], key=lambda x: x['retention']):
            print(f"  [{mem['retention']:.1%}] {mem['memory']}")


def cleanup(analysis, m, user_id, dry_run=True):
    """Remove decayed memories"""
    candidates = analysis['decay_candidates']
    if not candidates:
        print("No memories to clean up.")
        return 0
    if dry_run:
        print(f"\n🔍 DRY RUN: Would remove {len(candidates)} memories")
        return 0
    removed = 0
    for mem in candidates:
        try:
            m.delete(mem['id'])
            removed += 1
            print(f"  Removed: {mem['memory']}")
        except Exception as e:
            print(f"  Error removing {mem['id']}: {e}")
    print(f"\n✅ Removed {removed} decayed memories")
    return removed


if __name__ == "__main__":
    half_life = DEFAULT_HALF_LIFE
    threshold = DEFAULT_THRESHOLD
    user_id = os.environ.get("MEM0_USER", "agent")
    do_cleanup = "--cleanup" in sys.argv
    dry_run = "--dry-run" in sys.argv or not do_cleanup

    for i, arg in enumerate(sys.argv):
        if arg == "--half-life" and i + 1 < len(sys.argv):
            half_life = float(sys.argv[i + 1])
        elif arg == "--threshold" and i + 1 < len(sys.argv):
            threshold = float(sys.argv[i + 1])
        elif arg == "--user" and i + 1 < len(sys.argv):
            user_id = sys.argv[i + 1]

    print(f"Half-life: {half_life}d | Threshold: {threshold:.0%} | User: {user_id}")
    print(f"Workspace: {WORKSPACE}")

    analysis, m = analyze_memories(user_id, half_life, threshold)
    print_report(analysis)

    if do_cleanup or dry_run:
        cleanup(analysis, m, user_id, dry_run=dry_run)
