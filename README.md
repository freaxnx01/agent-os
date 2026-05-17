# agent-os

Personal Agentic OS running on `claude-dev` (LXC 201). Claude Code CLI as execution layer, Forgejo as Git backend.

## Phases

1. **Semantic memory** — pgvector + mem0 + Ollama, exposed as MCP server (`memory/`)
2. **Skill registry** — centralised `claude-skills` repo on Forgejo
3. **Tool registry** — `tools.json` / MCP inventory
4. **Observability** — session log + cost dashboard
5. **Orchestrator/specialist pipeline** — GitHub Actions

## Quick start (Phase 1)

```bash
cd memory
cp .env.example .env   # set POSTGRES_PASSWORD
docker compose up -d
# wait ~5 min for Ollama models to pull, then:
claude mcp add mem0 --transport http http://localhost:8765/mcp
```

See `CLAUDE.md` for full operational details.
