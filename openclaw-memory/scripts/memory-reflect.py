#!/usr/bin/env python3
"""
Memory Reflect — Automatic memory consolidation

Scans recent daily notes, generates a structured report for LLM-driven
consolidation into MEMORY.md, and optionally syncs to Mem0.

Usage:
  python3 scripts/memory-reflect.py              # Full report
  python3 scripts/memory-reflect.py --days 5     # Scan last 5 days
  python3 scripts/memory-reflect.py --json       # JSON output for piping
"""

import os
import json
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# --- Auto-detect workspace ---
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = Path(os.environ.get("WORKSPACE", SCRIPT_DIR.parent))

# Try to find workspace root (has MEMORY.md or memory/ dir)
for candidate in [WORKSPACE, SCRIPT_DIR.parent, SCRIPT_DIR.parent.parent]:
    if (candidate / "MEMORY.md").exists() or (candidate / "memory").is_dir():
        WORKSPACE = candidate
        break

load_dotenv(WORKSPACE / ".env")

MEMORY_DIR = WORKSPACE / "memory"
MEMORY_MD = WORKSPACE / "MEMORY.md"
CONFIG_PATH = WORKSPACE / "config" / "mem0_config.json"

DAYS_TO_SCAN = 3
DAYS_OLD_THRESHOLD = 14


def get_recent_daily_notes(days=DAYS_TO_SCAN):
    """Get last N days of daily notes"""
    notes = []
    today = datetime.utcnow().date()
    for i in range(days):
        date = today - timedelta(days=i)
        filename = MEMORY_DIR / f"{date.isoformat()}.md"
        if filename.exists():
            content = filename.read_text(encoding='utf-8')
            notes.append({
                'date': date.isoformat(),
                'path': str(filename),
                'content': content,
                'size': len(content),
                'lines': content.count('\n') + 1
            })
    return notes


def get_memory_md():
    """Read MEMORY.md"""
    if MEMORY_MD.exists():
        content = MEMORY_MD.read_text(encoding='utf-8')
        return {
            'path': str(MEMORY_MD),
            'content': content,
            'size': len(content),
            'lines': content.count('\n') + 1
        }
    return None


def get_old_daily_notes(threshold_days=DAYS_OLD_THRESHOLD):
    """Find daily notes older than threshold"""
    old_notes = []
    today = datetime.utcnow().date()
    for f in sorted(MEMORY_DIR.glob("202[0-9]-[0-9][0-9]-[0-9][0-9].md")):
        try:
            note_date = datetime.strptime(f.stem, "%Y-%m-%d").date()
            age_days = (today - note_date).days
            if age_days > threshold_days:
                old_notes.append({
                    'date': f.stem,
                    'path': str(f),
                    'age_days': age_days,
                    'size': f.stat().st_size
                })
        except ValueError:
            continue
    return old_notes


def get_all_memory_files():
    """Get stats for all memory files"""
    files = []
    if MEMORY_DIR.exists():
        for f in sorted(MEMORY_DIR.glob("*.md")):
            files.append({
                'name': f.name,
                'size': f.stat().st_size,
                'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
    return files


def generate_reflect_report():
    """Generate the full reflection report"""
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'workspace': str(WORKSPACE),
        'recent_notes': get_recent_daily_notes(),
        'memory_md': get_memory_md(),
        'old_notes': get_old_daily_notes(),
        'all_files': get_all_memory_files(),
        'stats': {}
    }

    report['stats']['total_memory_files'] = len(report['all_files'])
    report['stats']['total_size_kb'] = sum(f['size'] for f in report['all_files']) / 1024
    report['stats']['memory_md_lines'] = report['memory_md']['lines'] if report['memory_md'] else 0
    report['stats']['recent_notes_count'] = len(report['recent_notes'])
    report['stats']['old_notes_count'] = len(report['old_notes'])

    # Build LLM prompt
    recent_content = ""
    for note in report['recent_notes']:
        recent_content += f"\n--- {note['date']} ({note['lines']} lines) ---\n"
        recent_content += note['content'][:3000]
        if len(note['content']) > 3000:
            recent_content += "\n... (truncated)"

    memory_content = report['memory_md']['content'] if report['memory_md'] else "(empty)"

    report['reflect_prompt'] = f"""You are the memory consolidation module. Analyze the following and output suggestions.

## Current MEMORY.md ({report['stats']['memory_md_lines']} lines)
{memory_content[:5000]}

## Recent {DAYS_TO_SCAN} Days of Daily Notes
{recent_content}

## Tasks
1. Find entries in daily notes worth adding to MEMORY.md (decisions, lessons, new projects, preference changes)
2. Check MEMORY.md for outdated/inaccurate entries that need updating
3. Check for duplicate information that can be merged

Output format (JSON):
{{
  "additions": ["entries to add to MEMORY.md..."],
  "updates": [{{"section": "...", "old": "...", "new": "..."}}],
  "removals": ["outdated entries to remove..."],
  "summary": "one-line summary of this consolidation"
}}"""

    return report


def sync_to_mem0(additions):
    """Sync new findings to Mem0"""
    if not additions or not CONFIG_PATH.exists():
        return 0
    try:
        from mem0 import Memory
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        config["llm"]["config"]["api_key"] = os.getenv("GEMINI_API_KEY")
        config["embedder"]["config"]["api_key"] = os.getenv("GEMINI_API_KEY")
        m = Memory.from_config(config)
        synced = 0
        user_id = os.environ.get("MEM0_USER", "agent")
        for text in additions:
            if len(text) < 10:
                continue
            try:
                r = m.add(text, user_id=user_id, metadata={
                    "source": "reflect",
                    "date": datetime.utcnow().date().isoformat()
                })
                synced += len(r.get('results', []))
                time.sleep(1)
            except Exception as e:
                print(f"  Mem0 sync error: {e}")
        return synced
    except ImportError:
        print("  Mem0 not installed, skipping sync")
        return 0
    except Exception as e:
        print(f"  Mem0 sync failed: {e}")
        return 0


if __name__ == "__main__":
    # Parse args
    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            DAYS_TO_SCAN = int(sys.argv[idx + 1])

    report = generate_reflect_report()

    if "--json" in sys.argv:
        # Strip large content for JSON output
        for note in report['recent_notes']:
            note['content'] = note['content'][:500]
        if report['memory_md']:
            report['memory_md']['content'] = report['memory_md']['content'][:500]
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("=" * 60)
        print("Memory Reflect Report")
        print("=" * 60)
        print(f"Workspace: {WORKSPACE}")
        print(f"Time: {report['timestamp']}")
        print(f"Memory files: {report['stats']['total_memory_files']}")
        print(f"Total size: {report['stats']['total_size_kb']:.1f} KB")
        print(f"MEMORY.md: {report['stats']['memory_md_lines']} lines")
        print(f"Recent {DAYS_TO_SCAN}-day notes: {report['stats']['recent_notes_count']}")
        print(f"Old notes (>{DAYS_OLD_THRESHOLD}d): {report['stats']['old_notes_count']}")

        if report['old_notes']:
            print("\nArchive candidates:")
            for n in report['old_notes']:
                print(f"  - {n['date']} ({n['age_days']}d old, {n['size']}B)")

        print("\n" + "=" * 60)
        print("Reflect Prompt (for LLM):")
        print("=" * 60)
        print(report['reflect_prompt'][:2000])
        if len(report['reflect_prompt']) > 2000:
            print("... (truncated for display)")
