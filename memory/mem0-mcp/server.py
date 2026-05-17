"""mem0 MCP server — semantic memory for Claude Code sessions."""

import json
import os
from typing import Optional

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

POSTGRES_URL = os.environ["POSTGRES_URL"]
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama3.2:3b")
MCP_PORT = int(os.environ.get("MCP_PORT", "8765"))

MEM0_CONFIG = {
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": EMBED_MODEL,
            "ollama_base_url": OLLAMA_URL,
        },
    },
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "connection_string": POSTGRES_URL,
            "collection_name": "memories",
            "embedding_model_dims": 768,
        },
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": LLM_MODEL,
            "ollama_base_url": OLLAMA_URL,
        },
    },
}

_memory = None


def get_memory():
    global _memory
    if _memory is None:
        from mem0 import Memory
        _memory = Memory.from_config(MEM0_CONFIG)
    return _memory


mcp = FastMCP("mem0-memory", instructions=(
    "Semantic memory store for Claude Code sessions. "
    "Use add_memory to persist facts, decisions, and procedures. "
    "Use search_memory to retrieve relevant context at session start."
))


@mcp.tool()
def add_memory(content: str, user_id: str = "freax", metadata: Optional[dict] = None) -> str:
    """Store a memory — a fact, decision, finding, or procedure from the current session."""
    result = get_memory().add(content, user_id=user_id, metadata=metadata or {})
    return json.dumps(result, default=str)


@mcp.tool()
def search_memory(query: str, user_id: str = "freax", limit: int = 5) -> str:
    """Retrieve memories relevant to a query via semantic search."""
    results = get_memory().search(query, filters={"user_id": user_id}, limit=limit)
    return json.dumps(results, default=str)


@mcp.tool()
def list_memories(user_id: str = "freax") -> str:
    """List all stored memories for a user (most recent first, up to 50)."""
    results = get_memory().get_all(filters={"user_id": user_id})
    entries = results if isinstance(results, list) else results.get("results", [])
    return json.dumps(entries[:50], default=str)


@mcp.tool()
def delete_memory(memory_id: str) -> str:
    """Delete a specific memory by its ID."""
    get_memory().delete(memory_id)
    return f"Deleted {memory_id}"


@mcp.tool()
def update_memory(memory_id: str, content: str) -> str:
    """Update the text of an existing memory."""
    result = get_memory().update(memory_id, content)
    return json.dumps(result, default=str)


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "models": {"embed": EMBED_MODEL, "llm": LLM_MODEL}})


_mcp_app = mcp.http_app()

app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/", app=_mcp_app),
    ],
    lifespan=_mcp_app.lifespan,
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=MCP_PORT)
