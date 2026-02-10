#!/bin/bash
# Memory Management System — Full Automated Setup
# Run from workspace root or pass WORKSPACE as env var
#
# Usage:
#   bash <skill_dir>/scripts/setup.sh
#   WORKSPACE=/path/to/workspace bash setup.sh
#   MEM0_USER=fox bash setup.sh

set -euo pipefail

# --- Detect paths ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Workspace = parent of skills/<this-skill> OR env override
if [ -n "${WORKSPACE:-}" ]; then
    WS="$WORKSPACE"
elif [ -f "$SKILL_DIR/../../MEMORY.md" ]; then
    WS="$(cd "$SKILL_DIR/../.." && pwd)"
elif [ -f "$SKILL_DIR/../../../MEMORY.md" ]; then
    WS="$(cd "$SKILL_DIR/../../.." && pwd)"
else
    # Try common OpenClaw workspace locations
    for candidate in "$HOME/clawd" "$HOME/openclaw" "$HOME/workspace" "$(pwd)"; do
        if [ -d "$candidate" ]; then
            WS="$candidate"
            break
        fi
    done
fi

WS="${WS:-$(pwd)}"
MEM0_USER="${MEM0_USER:-agent}"

echo "========================================="
echo "  Memory Management System Setup"
echo "========================================="
echo "Workspace:  $WS"
echo "Skill dir:  $SKILL_DIR"
echo "Mem0 user:  $MEM0_USER"
echo ""

# --- Step 1: Check prerequisites ---
echo "▶ Step 1: Checking prerequisites..."

if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 not found. Install Python 3.10+ first."
    exit 1
fi

PYTHON_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  Python: $PYTHON_VER"

# Check for .env with GEMINI_API_KEY
ENV_FILE="$WS/.env"
if [ -f "$ENV_FILE" ]; then
    if grep -q "GEMINI_API_KEY" "$ENV_FILE"; then
        echo "  ✅ GEMINI_API_KEY found in .env"
    else
        echo "  ⚠️  GEMINI_API_KEY not found in $ENV_FILE"
        echo "     Add: GEMINI_API_KEY=your_key_here"
        echo "     Get a free key at: https://aistudio.google.com/apikey"
        read -p "  Continue anyway? (y/N) " -n 1 -r
        echo
        [[ $REPLY =~ ^[Yy]$ ]] || exit 1
    fi
else
    echo "  ⚠️  No .env file found at $ENV_FILE"
    echo "     Create it with: GEMINI_API_KEY=your_key_here"
    read -p "  Continue anyway? (y/N) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || exit 1
fi

# --- Step 2: Install Python dependencies ---
echo ""
echo "▶ Step 2: Installing Python dependencies..."

pip3 install --quiet --user mem0ai python-dotenv qdrant-client 2>&1 | tail -3
echo "  ✅ mem0ai, python-dotenv, qdrant-client installed"

# --- Step 3: Create directories ---
echo ""
echo "▶ Step 3: Creating directories..."

mkdir -p "$WS/scripts"
mkdir -p "$WS/memory"
mkdir -p "$WS/config"
mkdir -p "$WS/data/mem0_qdrant"
echo "  ✅ scripts/, memory/, config/, data/mem0_qdrant/"

# --- Step 4: Copy scripts ---
echo ""
echo "▶ Step 4: Deploying scripts..."

for script in memory-reflect.py mem0-import.py mem0-search.sh memory-decay.py; do
    src="$SKILL_DIR/scripts/$script"
    dst="$WS/scripts/$script"
    if [ -f "$src" ]; then
        cp "$src" "$dst"
        chmod +x "$dst"
        echo "  ✅ $script → scripts/$script"
    else
        echo "  ⚠️  $script not found in skill, skipping"
    fi
done

# --- Step 5: Generate Mem0 config ---
echo ""
echo "▶ Step 5: Generating Mem0 config..."

CONFIG_FILE="$WS/config/mem0_config.json"
TEMPLATE="$SKILL_DIR/references/mem0-config-template.json"

if [ -f "$CONFIG_FILE" ]; then
    echo "  ℹ️  Config already exists at $CONFIG_FILE, keeping it"
else
    if [ -f "$TEMPLATE" ]; then
        sed "s|__WORKSPACE__|$WS|g" "$TEMPLATE" > "$CONFIG_FILE"
        echo "  ✅ Generated config/mem0_config.json"
    else
        # Generate inline if template missing
        cat > "$CONFIG_FILE" << JSONEOF
{
  "llm": {
    "provider": "gemini",
    "config": {
      "model": "gemini-2.0-flash"
    }
  },
  "embedder": {
    "provider": "gemini",
    "config": {
      "model": "models/gemini-embedding-001",
      "embedding_dims": 768
    }
  },
  "vector_store": {
    "provider": "qdrant",
    "config": {
      "collection_name": "agent_memory",
      "path": "$WS/data/mem0_qdrant",
      "embedding_model_dims": 768
    }
  },
  "version": "v1.1"
}
JSONEOF
        echo "  ✅ Generated config/mem0_config.json (inline)"
    fi
fi

# --- Step 6: Verify Mem0 connection ---
echo ""
echo "▶ Step 6: Verifying Mem0 connection..."

VERIFY_RESULT=$(python3 << PYEOF 2>&1
import os, json
from dotenv import load_dotenv
load_dotenv("$WS/.env")

try:
    from mem0 import Memory
    with open("$CONFIG_FILE") as f:
        config = json.load(f)
    config["llm"]["config"]["api_key"] = os.getenv("GEMINI_API_KEY", "")
    config["embedder"]["config"]["api_key"] = os.getenv("GEMINI_API_KEY", "")
    m = Memory.from_config(config)
    all_mem = m.get_all(user_id="$MEM0_USER")
    count = len(all_mem.get('results', []))
    print(f"OK:{count}")
except Exception as e:
    print(f"ERR:{e}")
PYEOF
)

if [[ "$VERIFY_RESULT" == OK:* ]]; then
    MEM_COUNT="${VERIFY_RESULT#OK:}"
    echo "  ✅ Mem0 connected ($MEM_COUNT existing memories)"
else
    echo "  ⚠️  Mem0 verification failed: ${VERIFY_RESULT#ERR:}"
    echo "     Check GEMINI_API_KEY in .env"
fi

# --- Step 7: Import existing MEMORY.md ---
echo ""
echo "▶ Step 7: Importing existing memories..."

if [ -f "$WS/MEMORY.md" ]; then
    echo "  Found MEMORY.md, importing to Mem0..."
    python3 "$WS/scripts/mem0-import.py" 2>&1 | tail -5
else
    echo "  No MEMORY.md found, skipping import"
fi

# --- Step 8: Setup cron jobs ---
echo ""
echo "▶ Step 8: Setting up cron jobs..."
echo "  ℹ️  Cron jobs use OpenClaw's cron system."
echo "  Create these manually or via agent commands:"
echo ""
echo "  1. Memory Reflection (every 6 hours):"
echo "     Schedule: {\"kind\": \"cron\", \"expr\": \"0 */6 * * *\"}"
echo "     Payload: agentTurn with message:"
echo "     \"Run memory-reflect.py, review the output, and update MEMORY.md accordingly."
echo "      Then sync new additions to Mem0. Script: scripts/memory-reflect.py\""
echo ""
echo "  2. Memory Decay (weekly, Sunday 06:00 UTC):"
echo "     Schedule: {\"kind\": \"cron\", \"expr\": \"0 6 * * 0\"}"
echo "     Payload: agentTurn with message:"
echo "     \"Run memory-decay.py --cleanup to remove stale memories."
echo "      Report what was cleaned up. Script: scripts/memory-decay.py --cleanup\""
echo ""

# --- Done ---
echo "========================================="
echo "  ✅ Setup Complete!"
echo "========================================="
echo ""
echo "Installed:"
echo "  scripts/memory-reflect.py  — Automatic consolidation"
echo "  scripts/mem0-import.py     — Import memories to Mem0"
echo "  scripts/mem0-search.sh     — Search structured memory"
echo "  scripts/memory-decay.py    — Ebbinghaus decay cleanup"
echo "  config/mem0_config.json    — Mem0 configuration"
echo ""
echo "Next steps:"
echo "  1. Create cron jobs (see above)"
echo "  2. Add memory search priority to AGENTS.md"
echo "  3. Run: scripts/mem0-search.sh 'test query'"
echo ""
