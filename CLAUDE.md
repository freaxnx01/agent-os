# agent-os — Agentic OS for agent-dev

**Host:** LXC 201 (`agent-dev`, `192.168.1.108`, Ubuntu 24.04)
**Repo:** `github.com/freaxnx01/public/agent-os` (mirrored to `git.home.freaxnx01.ch/freax/agent-os`)

## Build order

| Phase | Directory | Status |
|---|---|---|
| 1. Semantic memory | `memory/` | in progress |
| 2. Skill registry | `skills/` | planned |
| 3. Tool registry | `tools/` | planned |
| 4. Observability | `observability/` | planned |
| 5. Orchestrator/specialist pipeline | `pipeline/` | planned |

---

## Phase 1 — Semantic Memory (`memory/`)

### Stack
- **postgres-memory** (`pgvector/pgvector:pg17`) — vector store
- **ollama** (`ollama/ollama`) — local embeddings + LLM, exposed on `127.0.0.1:11434`
- **ollama-init** — one-shot container that pulls `nomic-embed-text` and `llama3.2:3b`
- **mem0-mcp** — FastMCP server wrapping mem0ai, exposed on `127.0.0.1:8765/mcp`

### Deploy
```bash
cd ~/projects/repos/github/freaxnx01/public/agent-os/memory
cp .env.example .env    # first time only; .env is gitignored
# edit .env → set POSTGRES_PASSWORD
docker compose up -d
```

Ollama models pull automatically on first start (ollama-init container).
Watch progress: `docker logs -f memory-ollama-init`

### MCP config — add to `~/.claude.json` under `mcpServers`
```json
"mem0": {
  "type": "http",
  "url": "http://localhost:8765/mcp"
}
```

Or one-shot: `claude mcp add mem0 --transport http http://localhost:8765/mcp`

### Stop hook — already registered in `~/.claude-s1/settings.json`
Fires `memory/hooks/post-session.sh` when a Claude session exits.
To save a memory explicitly during a session, call the `add_memory` MCP tool.

### Useful commands
```bash
# Status
docker compose ps

# Logs
docker logs -f memory-mem0-mcp

# Test the MCP health endpoint
curl http://localhost:8765/health

# Manual memory add (smoke test)
curl -X POST http://localhost:8765/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search_memory","arguments":{"query":"test"}}}'

# Teardown (keeps volumes)
docker compose down

# Full teardown including data
docker compose down -v
```

### Ollama models
```bash
# Check loaded models
curl http://localhost:11434/api/tags

# Pull additional models manually
docker exec memory-ollama ollama pull <model>
```

---

## Memory usage patterns

At **session start**: call `search_memory` with the project name or task description to pull relevant context.

During a session: call `add_memory` whenever you learn something worth persisting:
- Architecture decisions and the reason behind them
- Non-obvious gotchas or workarounds
- Procedure steps that took effort to figure out
- Pointers to external resources

At **session end**: the Stop hook auto-fires. For richer context, call `add_memory` with a session summary before `/exit`.

---

## Infrastructure references
- MCP proxy: LXC 130, `https://mcp.home.freaxnx01.ch/<server>/mcp` — see homelab vault `Services/mcp-proxy.md`
- clrepo + slot system: `~/projects/repos/github/freaxnx01/public/clrepo/` — see homelab vault `Services/agent-dev.md`
- Forgejo: `git.home.freaxnx01.ch` (SSH auth via `~/.ssh/config`)
