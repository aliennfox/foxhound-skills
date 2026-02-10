---
name: memory-management
description: >
  Four-layer memory architecture with automated consolidation, structured memory (Mem0),
  and Ebbinghaus forgetting curve decay. Use when setting up agent memory systems,
  automating memory maintenance, importing memories, searching structured memory,
  or cleaning up stale memories. Provides: (1) Automatic daily memory reflection/consolidation
  from daily notes into MEMORY.md, (2) Mem0 structured memory with semantic search
  (Gemini + local Qdrant, zero cost), (3) Memory decay based on Ebbinghaus forgetting curve,
  (4) Cron job automation for all of the above. Triggers on: "setup memory", "memory management",
  "memory consolidation", "memory decay", "mem0 setup", "install memory system",
  "automate memory", "memory architecture".
---

# Memory Management Skill

Four-layer memory architecture for OpenClaw agents:

1. **MEMORY.md** — curated long-term memory (manual + auto-consolidated)
2. **Daily notes** (`memory/YYYY-MM-DD.md`) — raw session logs
3. **Mem0** — structured memory with semantic search (auto-dedup, free Gemini stack)
4. **OpenClaw vector search** — built-in `memory_search` over all `.md` files

## Architecture Overview

```
Daily Notes ──→ memory-reflect.py ──→ MEMORY.md (consolidated)
     │                                      │
     └──→ mem0-import.py ──→ Mem0 (Qdrant) ←┘
                                │
                        mem0-search.sh (query)
                                │
                        memory-decay.py (cleanup)
```

## First-Time Setup

Run the setup script to deploy the entire system:

```bash
bash <skill_dir>/scripts/setup.sh
```

The setup script will:
1. Install Python dependencies (`mem0ai`, `python-dotenv`, `qdrant-client`)
2. Copy scripts to `$WORKSPACE/scripts/`
3. Generate Mem0 config from template
4. Create `memory/` directory if needed
5. Create initial cron jobs (reflection + decay)
6. Import existing MEMORY.md into Mem0
7. Verify the installation

### Prerequisites

- **Gemini API key** in `.env` as `GEMINI_API_KEY` (free tier works)
- Python 3.10+
- OpenClaw with cron support

### Environment Variable

Add to your workspace `.env`:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

## Scripts Reference

All scripts auto-detect the workspace root (parent of `scripts/` directory).

### memory-reflect.py — Automatic Consolidation

Scans recent daily notes and generates a structured report for LLM-driven consolidation into MEMORY.md.

```bash
python3 scripts/memory-reflect.py
```

- Scans last 3 days of daily notes by default
- Identifies entries worth adding to MEMORY.md
- Detects outdated MEMORY.md entries
- Syncs new findings to Mem0
- Designed to run via cron (agentTurn in isolated session)

### mem0-import.py — Import to Mem0

Imports MEMORY.md and/or daily notes into Mem0's structured memory store.

```bash
python3 scripts/mem0-import.py              # Import MEMORY.md only
python3 scripts/mem0-import.py --daily 3    # Import last 3 days of notes
python3 scripts/mem0-import.py --all        # Import everything
python3 scripts/mem0-import.py --stats      # Show current stats
```

### mem0-search.sh — Search Structured Memory

Fast semantic search across all Mem0 memories.

```bash
scripts/mem0-search.sh "query text" [user_id]
# Default user_id: "agent" (configurable in setup)
```

### memory-decay.py — Ebbinghaus Decay

Analyzes memory age and removes stale entries based on the forgetting curve.

```bash
python3 scripts/memory-decay.py                          # Report only
python3 scripts/memory-decay.py --cleanup --dry-run      # Preview cleanup
python3 scripts/memory-decay.py --cleanup                # Execute cleanup
python3 scripts/memory-decay.py --half-life 45           # Custom half-life (days)
python3 scripts/memory-decay.py --threshold 0.05         # Custom threshold (5%)
```

Default: half-life 30 days, threshold 10% retention (~69 days for cleanup).

## Cron Jobs (Auto-Created by Setup)

| Job | Schedule | Purpose |
|-----|----------|---------|
| `memory-reflect` | Every 6 hours | Consolidate daily notes → MEMORY.md, sync to Mem0 |
| `memory-decay-weekly` | Sunday UTC 06:00 | Clean up old Mem0 entries via Ebbinghaus curve |

To adjust frequency after setup, use `/cron list` and `/cron update`.

## Recommended AGENTS.md Addition

After install, add to your AGENTS.md memory section:

```markdown
### Memory Search Priority
1. OpenClaw vector search (`memory_search`) — default, automatic
2. Mem0 (`scripts/mem0-search.sh "query"`) — structured facts, precise recall
3. Daily notes (`memory/YYYY-MM-DD.md`) — raw recent context
```

## Customization

- **Reflection frequency**: Edit cron schedule (default every 6h, adjust to 2h for busy agents)
- **Decay half-life**: Default 30 days; increase for agents with slower-changing context
- **Mem0 user_id**: Default "agent"; change in setup or script args
- **Scan depth**: `DAYS_TO_SCAN` in memory-reflect.py (default 3 days)
