# Finch Backend

FastAPI backend for the Finch portfolio chatbot.

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp env.template .env
# Add your API key to .env
```

3. Run the server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Documentation

Visit `http://localhost:8000/docs` for interactive Swagger UI documentation.

## Agent Architecture

The agent (`agent.py`) uses **LiteLLM** for conversational AI, which provides a unified interface for:
- OpenAI (GPT-5, GPT-4, etc.)
- Anthropic (Claude 3.5 Sonnet, Opus, etc.)
- Google (Gemini Pro, etc.)
- And 100+ other providers!

### Switching LLM Providers

Simply change the model name in your `.env`:

**Anthropic Claude 4.5 (Default):**
```env
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-sonnet-4-5-20250929
```

**OpenAI GPT-5:**
```env
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-5
```

**Anthropic Claude 3.5:**
```env
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-5-sonnet-20241022
```

**Google Gemini:**
```env
GOOGLE_API_KEY=...
LLM_MODEL=gemini-pro
```

No code changes needed! LiteLLM handles all the differences.

## Features

- Conversation history per session
- System prompt for portfolio assistant persona
- Extensible tool calling interface (ready for Robinhood integration)
- Provider-agnostic LLM integration

## Environment Variables

- `LLM_MODEL` - Model to use (default: claude-sonnet-4-20250514)
- `ANTHROPIC_API_KEY` - Required for Claude models
- `OPENAI_API_KEY` - Required for OpenAI models
- `GOOGLE_API_KEY` - Required for Gemini models
- `API_HOST` - Server host (default: 0.0.0.0)
- `API_PORT` - Server port (default: 8000)
- `CORS_ORIGINS` - Allowed CORS origins

## Development

Run with auto-reload:
```bash
uvicorn main:app --reload
```

Run on different port:
```bash
uvicorn main:app --port 8080
```

## Supported Models

LiteLLM supports 100+ models. Popular ones:

### OpenAI
- `gpt-5`, `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`

### Anthropic
- `claude-sonnet-4-5-20250929` (Claude 4.5 Sonnet), `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`, `claude-3-sonnet-20240229`

### Google
- `gemini-pro`, `gemini-1.5-pro`

### Open Source (via various providers)
- `llama-3`, `mistral-large`, `mixtral-8x7b`

See full list: https://docs.litellm.ai/docs/providers
