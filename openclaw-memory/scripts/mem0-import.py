#!/usr/bin/env python3
"""
Mem0 Import — Import MEMORY.md and daily notes into Mem0

Usage:
  python3 scripts/mem0-import.py                  # Import MEMORY.md
  python3 scripts/mem0-import.py --daily 3        # Import last 3 days
  python3 scripts/mem0-import.py --all            # Import everything
  python3 scripts/mem0-import.py --stats          # Show stats
"""

import os
import json
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# --- Auto-detect workspace ---
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = Path(os.environ.get("WORKSPACE", SCRIPT_DIR.parent))
for candidate in [WORKSPACE, SCRIPT_DIR.parent, SCRIPT_DIR.parent.parent]:
    if (candidate / "MEMORY.md").exists() or (candidate / "memory").is_dir():
        WORKSPACE = candidate
        break

load_dotenv(WORKSPACE / ".env")

MEMORY_DIR = WORKSPACE / "memory"
MEMORY_MD = WORKSPACE / "MEMORY.md"
CONFIG_PATH = WORKSPACE / "config" / "mem0_config.json"
USER_ID = os.environ.get("MEM0_USER", "agent")


def get_mem0():
    """Initialize Mem0 from config"""
    from mem0 import Memory
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    config["llm"]["config"]["api_key"] = os.getenv("GEMINI_API_KEY")
    config["embedder"]["config"]["api_key"] = os.getenv("GEMINI_API_KEY")
    return Memory.from_config(config)


def split_into_chunks(text, max_chars=500):
    """Split text into paragraph-based chunks"""
    chunks = []
    current = ""
    for line in text.split('\n'):
        if line.startswith('#') or not line.strip():
            if current.strip():
                chunks.append(current.strip())
                current = ""
            continue
        if len(current) + len(line) > max_chars:
            if current.strip():
                chunks.append(current.strip())
            current = line + '\n'
        else:
            current += line + '\n'
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if len(c) > 20]


def import_memory_md(m):
    """Import MEMORY.md"""
    if not MEMORY_MD.exists():
        print("MEMORY.md not found!")
        return 0
    content = MEMORY_MD.read_text(encoding='utf-8')
    chunks = split_into_chunks(content, max_chars=400)
    print(f"MEMORY.md: {len(content)} chars → {len(chunks)} chunks")
    imported = 0
    for i, chunk in enumerate(chunks):
        try:
            r = m.add(chunk, user_id=USER_ID, metadata={"source": "MEMORY.md"})
            count = len(r.get('results', []))
            imported += count
            print(f"  [{i+1}/{len(chunks)}] +{count} memories ({chunk[:60]}...)")
            time.sleep(0.5)
        except Exception as e:
            print(f"  [{i+1}/{len(chunks)}] ERROR: {e}")
    return imported


def import_daily_notes(m, days=3):
    """Import last N days of daily notes"""
    today = datetime.utcnow().date()
    imported = 0
    for i in range(days):
        date = today - timedelta(days=i)
        filepath = MEMORY_DIR / f"{date.isoformat()}.md"
        if not filepath.exists():
            continue
        content = filepath.read_text(encoding='utf-8')
        chunks = split_into_chunks(content, max_chars=400)
        print(f"\n{date}: {len(content)} chars → {len(chunks)} chunks")
        for j, chunk in enumerate(chunks):
            try:
                r = m.add(chunk, user_id=USER_ID, metadata={
                    "source": f"daily:{date}",
                    "date": date.isoformat()
                })
                count = len(r.get('results', []))
                imported += count
                print(f"  [{j+1}/{len(chunks)}] +{count} ({chunk[:50]}...)")
                time.sleep(0.5)
            except Exception as e:
                print(f"  [{j+1}/{len(chunks)}] ERROR: {e}")
    return imported


def import_all(m):
    """Import all memory files"""
    imported = import_memory_md(m)
    for f in sorted(MEMORY_DIR.glob("202[0-9]-[0-9][0-9]-[0-9][0-9].md")):
        content = f.read_text(encoding='utf-8')
        chunks = split_into_chunks(content, max_chars=400)
        print(f"\n{f.name}: {len(content)} chars → {len(chunks)} chunks")
        for j, chunk in enumerate(chunks):
            try:
                r = m.add(chunk, user_id=USER_ID, metadata={
                    "source": f"daily:{f.stem}",
                    "date": f.stem
                })
                count = len(r.get('results', []))
                imported += count
                time.sleep(0.5)
            except Exception as e:
                print(f"  ERROR: {e}")
    return imported


def show_stats(m):
    """Show Mem0 stats"""
    result = m.get_all(user_id=USER_ID)
    count = len(result.get('results', []))
    print(f"\n📊 Mem0 Stats:")
    print(f"  User: {USER_ID}")
    print(f"  Memories: {count}")
    print(f"  Config: {CONFIG_PATH}")
    print(f"  Workspace: {WORKSPACE}")


if __name__ == "__main__":
    m = get_mem0()
    print(f"✅ Mem0 connected (user: {USER_ID})\n")

    if "--all" in sys.argv:
        n = import_all(m)
        print(f"\n✅ Imported {n} memories (all files)")
    elif "--daily" in sys.argv:
        days = 3
        idx = sys.argv.index("--daily")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])
        n = import_daily_notes(m, days)
        print(f"\n✅ Imported {n} memories (last {days} days)")
    elif "--stats" in sys.argv:
        pass  # Just show stats below
    else:
        n = import_memory_md(m)
        print(f"\n✅ Imported {n} memories from MEMORY.md")

    show_stats(m)
