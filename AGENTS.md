# PROJECT KNOWLEDGE BASE

**Generated:** 2026-02-16
**Commit:** f56684b
**Branch:** development

## OVERVIEW

Hybrid Python/TypeScript project: AI-powered documentation generator (like GitHub Wiki). Uses FastAPI backend + Next.js frontend. Supports multiple LLM providers (Google Gemini, OpenAI, OpenRouter, Azure, Ollama) for code analysis and wiki generation.

## STRUCTURE

```
./
├── api/                 # Python FastAPI backend (port 8001)
│   ├── main.py         # Entry point
│   ├── api.py          # FastAPI + WebSocket routes
│   ├── rag.py          # RAG implementation
│   ├── websocket_wiki.py  # Real-time chat
│   ├── config/         # JSON configs (generator, embedder, repo)
│   ├── tools/          # Git clone, file processing
│   ├── validators/     # Input validation
│   └── clients/        # LLM client wrappers
├── src/                # Next.js frontend (port 3000)
│   ├── app/            # Next.js app router
│   ├── components/     # React components
│   ├── hooks/          # Custom React hooks
│   └── contexts/       # React contexts
├── tests/              # pytest test suites
├── Dockerfile          # Main container
└── docker-compose.yml  # Local dev
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| API routes | `api/api.py` | FastAPI endpoints + WebSocket |
| RAG logic | `api/rag.py` | Retrieval + generation |
| LLM clients | `api/*_client.py` | google, openai, azure, ollama, dashscope |
| Embeddings | `api/google_embedder_client.py` | google-genai SDK |
| Config | `api/config/*.json` | generator, embedder, repo settings |
| Frontend | `src/app/` | Next.js pages |
| Tests | `tests/` | unit/, api/, integration/ |

## CODE MAP

| Symbol | Type | Location | Refs |
|--------|------|----------|------|
| `app` | FastAPI | api/api.py | Main router |
| `handle_websocket_chat` | func | api/websocket_wiki.py | WebSocket handler |
| `get_embedding` | func | api/google_embedder_client.py | Embeddings |
| `generate_wiki` | func | api/data_pipeline.py | Wiki generation |

## CONVENTIONS

- **Python**: pyproject.toml in `api/`, pytest for tests
- **Frontend**: ESLint, Next.js app router
- **Response format**: NO markdown fences, NO thinking in output
- **RAG**: Always use when embedded docs available
- **Multi-provider**: Google Gemini default, configurable

## ANTI-PATTERNS (THIS PROJECT)

- DO NOT wrap XML in markdown code blocks
- DO NOT include thinking/reasoning in final output
- DO NOT use triple backticks in response start/end
- NEVER respond with just "Continue the research"
- NEVER start responses with markdown headers
- DEPRECATED: `is_ollama_embedder` → use `embedder_type`

## COMMANDS

```bash
# Backend
python -m api.main

# Frontend
npm run dev

# Tests
pytest

# Docker
docker-compose up
```

## NOTES

- Uses `google-genai` SDK (NOT deprecated `google-generativeai`)
- Context7 MCP available for docs lookup
- Supports private repo via tokens
- Embedder types: openai, google, ollama
