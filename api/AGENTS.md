# API Backend (Python/FastAPI)

**Parent:** `./AGENTS.md`

## OVERVIEW

FastAPI backend providing REST + WebSocket endpoints for wiki generation, RAG-based chat, and repository analysis.

## STRUCTURE

```
api/
├── main.py              # Entry point, app initialization
├── api.py               # FastAPI router, WebSocket registration
├── rag.py               # RAG retrieval + generation
├── websocket_wiki.py    # Real-time chat handler
├── data_pipeline.py     # Wiki generation pipeline
├── enhanced_pipeline.py # Enhanced wiki generation
├── prompts.py           # LLM prompts/templates
├── config/              # JSON configs
│   ├── generator.json   # LLM provider configs
│   ├── embedder.json    # Embedding configs
│   └── repo.json        # Repository settings
├── clients/             # LLM client wrappers
│   ├── google_client.py
│   ├── openai_client.py
│   ├── azureai_client.py
│   ├── ollama_client.py
│   └── dashscope_client.py
├── tools/               # Git operations, file processing
└── validators/          # Input validation
```

## KEY ENTRY POINTS

| File | Purpose |
|------|---------|
| `api/main.py` | App startup, logging setup |
| `api/api.py` | FastAPI app, routes, WebSocket |
| `api/websocket_wiki.py` | `handle_websocket_chat` - chat handler |

## CONVENTIONS

- All LLM clients follow same interface pattern
- Config loaded from JSON in `api/config/`
- Use `embedder_type` (NOT `is_ollama_embedder`)
- Response format: NO markdown fences, NO thinking

## ANTI-PATTERNS

- DO NOT wrap XML in ``` code blocks
- DO NOT include rationale/explanation in output
- NEVER respond "Continue the research"
- DEPRECATED: `is_ollama_embedder`

## COMMANDS

```bash
python -m api.main
# Runs on port 8001
```

## EXTERNAL DEPS

- `google-genai` (NOT `google-generativeai`)
- `google-adalflow` for embeddings
- FastAPI, uvicorn
