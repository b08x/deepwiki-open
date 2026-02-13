# DeepWiki-Open Project Instructions

## Google Gen AI SDK Migration

**IMPORTANT**: This project uses the **new** `google-genai` package, NOT `google-generativeai`.

The old `google.generativeai` package is deprecated and no longer maintained. All code has been migrated to use `google-genai`.

### Package Installation

```bash
pip install google-genai
# NOT: pip install google-generativeai (deprecated!)
```

### API Migration Guide

**Old API (google.generativeai) - DEPRECATED:**
```python
import google.generativeai as genai
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-pro")
response = model.generate_content("prompt")
```

**New API (google.genai) - CURRENT:**
```python
from google import genai
from google.genai import types

client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='prompt',
    config=types.GenerateContentConfig(temperature=0.7)
)
```

### Migration Status

✅ **MIGRATION COMPLETE** - All files migrated to `google-genai` SDK:

- ✅ Dependencies updated in requirements.txt and pyproject.toml
- ✅ google_embedder_client.py - Embeddings fully migrated
- ✅ Tests updated for new API
- ✅ main.py and api.py cleaned up
- ✅ simple_chat.py - Chat/streaming migrated
- ✅ websocket_wiki.py - WebSocket chat/streaming migrated
- ✅ Test dependency checks updated

**All references to deprecated `google.generativeai` package have been removed.**

---

## Use Context7 MCP for Loading Documentation

Context7 MCP is available to fetch up-to-date documentation with code examples.

### Recommended library IDs

**Primary Documentation:**

- `/googleapis/python-genai` - Google Gen AI Python SDK
  - Official Python SDK for Google's Generative AI (Gemini) models
  - Includes Gemini Developer API and Vertex AI integration
  - 722 code snippets | Benchmark score: 83.9 | High reputation

- `/sylphai-inc/adalflow` - AdalFlow Library
  - PyTorch-like library for building and auto-optimizing language model workflows (Chatbots, RAG, Agents)
  - 1,128 code snippets | Source Reputation: High

**Additional Resources:**

- `/websites/ai_google_dev_gemini-api` - Gemini API Documentation
  - Comprehensive Gemini API reference with extensive examples
  - Covers text, image, speech, and video generation
  - 3,752 code snippets | Benchmark score: 72.6 | High reputation

### Usage

When working with Google Generative AI features:

1. **For SDK implementation questions**: Query `/googleapis/python-genai`
   ```
   Example: "How to initialize the Gemini client and make a request?"
   ```

2. **For API reference and capabilities**: Query `/websites/ai_google_dev_gemini-api`
   ```
   Example: "What are the available Gemini model parameters and options?"
   ```

### Context7 MCP Tools

- `mcp__plugin_context7_context7__resolve-library-id` - Find library IDs by name
- `mcp__plugin_context7_context7__query-docs` - Query documentation with semantic search

### Examples

```python
# Query for specific implementation:
# "How to use embeddings with google-genai SDK?"

# Query for API capabilities:
# "What multimodal capabilities does Gemini support?"
```
