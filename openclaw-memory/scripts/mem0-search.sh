#!/bin/bash
# Mem0 Search — Fast semantic search across structured memories
# Usage: ./scripts/mem0-search.sh "query" [user_id]
# Example: ./scripts/mem0-search.sh "investment preferences" agent

set -euo pipefail

QUERY="${1:?Usage: mem0-search.sh 'query' [user_id]}"
USER_ID="${2:-${MEM0_USER:-agent}}"

# Auto-detect workspace
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="${WORKSPACE:-$(cd "$SCRIPT_DIR/.." && pwd)}"

# Try to find workspace root
for candidate in "$WORKSPACE" "$SCRIPT_DIR/.."; do
    if [ -f "$candidate/.env" ] || [ -f "$candidate/MEMORY.md" ]; then
        WORKSPACE="$(cd "$candidate" && pwd)"
        break
    fi
done

CONFIG_FILE="$WORKSPACE/config/mem0_config.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Config not found: $CONFIG_FILE"
    echo "   Run setup.sh first."
    exit 1
fi

python3 << PYEOF
import os, json
from dotenv import load_dotenv
load_dotenv("$WORKSPACE/.env")
from mem0 import Memory

with open("$CONFIG_FILE") as f:
    config = json.load(f)
config["llm"]["config"]["api_key"] = os.getenv("GEMINI_API_KEY")
config["embedder"]["config"]["api_key"] = os.getenv("GEMINI_API_KEY")

m = Memory.from_config(config)
results = m.search("$QUERY", user_id="$USER_ID")

hits = results.get('results', [])
if not hits:
    print("No results found.")
else:
    for r in hits:
        score = r.get('score', 0)
        memory = r.get('memory', '')
        print(f"[{score:.3f}] {memory}")
PYEOF
