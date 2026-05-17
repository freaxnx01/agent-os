#!/usr/bin/env bash
# Runs on Claude Code Stop event.
# Reads a session summary from $CLAUDE_MEMORY_SUMMARY (env var) or stdin, then
# stores it in mem0 via the local MCP HTTP API.
#
# Register in ~/.claude-sN/settings.json under hooks.Stop[].command
# (see memory/hooks/README below, or agent-os CLAUDE.md).

set -euo pipefail

MEM0_URL="${MEM0_URL:-http://localhost:8765}"
USER_ID="${MEM0_USER_ID:-freax}"
PROJECT="${CLAUDE_PROJECT_NAME:-unknown}"
SLOT="${CLAUDE_SLOT:-}"

# Determine content source: env var → stdin → skip
if [[ -n "${CLAUDE_MEMORY_SUMMARY:-}" ]]; then
  SUMMARY="$CLAUDE_MEMORY_SUMMARY"
elif [[ ! -t 0 ]]; then
  SUMMARY="$(cat)"
else
  # Nothing to save; still record a session-end marker
  SUMMARY="Session ended for project: $PROJECT"
fi

[[ -z "$SUMMARY" ]] && exit 0

# Enrich with metadata
METADATA=$(python3 - <<PYEOF
import json, datetime, os
print(json.dumps({
    "project": os.environ.get("CLAUDE_PROJECT_NAME", "unknown"),
    "slot":    os.environ.get("CLAUDE_SLOT", ""),
    "ts":      datetime.datetime.utcnow().isoformat() + "Z",
    "type":    "session_summary",
}))
PYEOF
)

# POST to mem0-mcp add_memory tool via MCP JSON-RPC
PAYLOAD=$(python3 - <<PYEOF
import json, sys
summary  = """$SUMMARY"""
metadata = $METADATA
# MCP tool-call via streamable-http: send a tools/call request
req = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "add_memory",
        "arguments": {
            "content":  summary,
            "user_id":  "$USER_ID",
            "metadata": metadata,
        }
    }
}
print(json.dumps(req))
PYEOF
)

# Check mem0-mcp is reachable before attempting
if ! curl -sf "$MEM0_URL/health" > /dev/null 2>&1; then
  echo "[post-session] mem0-mcp not reachable at $MEM0_URL — skipping memory save" >&2
  exit 0
fi

# Send MCP initialize first (required by streamable-http)
INIT=$(curl -sf -X POST "$MEM0_URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"post-session-hook","version":"1"}}}') || true

curl -sf -X POST "$MEM0_URL/mcp" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" > /dev/null

echo "[post-session] Memory saved for project '$PROJECT'."
