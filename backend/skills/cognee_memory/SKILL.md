---
name: cognee_memory
description: "Persistent stock knowledge memory powered by Cognee. Remembers news, analysis, and insights about stocks the user discusses. Builds a knowledge graph that improves over time — the more you chat about a stock, the smarter Finch gets about it."
homepage: https://github.com/topoteretes/cognee
metadata:
  emoji: "🧠"
  category: memory
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---

# Cognee Memory Skill

Persistent stock knowledge memory that builds a knowledge graph from conversations. The more the user discusses a stock, the richer the context becomes for future conversations.

## How It Works

Cognee builds a **knowledge graph** connecting stocks, events, sectors, people, and themes. When you store information about AAPL, it doesn't just save text — it extracts entities and relationships so later queries can traverse the graph (e.g., "What do I know about Tim Cook?" finds AAPL context too).

## When To Use

- **REMEMBER** after gathering news, analysis, or data about a stock the user is interested in
- **RECALL** at the start of any conversation about a stock to pull in accumulated knowledge
- **IMPROVE** periodically to consolidate session learnings into the permanent knowledge graph

## Quick Start

```python
from skills.cognee_memory.scripts.remember import remember_stock
from skills.cognee_memory.scripts.recall import recall_stock
from skills.cognee_memory.scripts.improve import improve_memory

# Store knowledge about a stock
await remember_stock(
    ticker="AAPL",
    content="Apple reported Q1 2025 earnings beating estimates. Revenue $124B vs $118B expected. Services revenue hit all-time high. Tim Cook highlighted Vision Pro adoption.",
    session_id="chat_123"
)

# Recall what we know about a stock
results = await recall_stock(
    query="What are the recent earnings and growth drivers for Apple?",
    ticker="AAPL"
)
for r in results:
    print(r)

# Consolidate session memory into permanent knowledge graph
await improve_memory(ticker="AAPL", session_ids=["chat_123"])
```

## Scripts

### remember_stock(ticker, content, session_id=None)

Store stock-related knowledge. Pass `session_id` for fast session storage (syncs to graph later), or omit for immediate permanent storage.

```python
from skills.cognee_memory.scripts.remember import remember_stock

# Permanent storage (slower, builds graph immediately)
await remember_stock("TSLA", "Tesla Q4 deliveries exceeded 500k units...")

# Session storage (fast, bridges to graph via improve())
await remember_stock("TSLA", "Tesla Q4 deliveries exceeded 500k units...", session_id="chat_456")
```

### recall_stock(query, ticker=None, session_id=None)

Retrieve relevant knowledge. Optionally scope to a ticker's dataset or a session.

```python
from skills.cognee_memory.scripts.recall import recall_stock

# Broad recall across all stock knowledge
results = await recall_stock("What semiconductor stocks have strong earnings?")

# Scoped to a specific stock
results = await recall_stock("Recent catalysts and risks", ticker="NVDA")

# Session-aware (checks session cache first, falls through to graph)
results = await recall_stock("What did we discuss?", session_id="chat_789")
```

### improve_memory(ticker=None, session_ids=None)

Bridge session memory into the permanent knowledge graph. Run this after a productive research session.

```python
from skills.cognee_memory.scripts.improve import improve_memory

# Improve a specific stock's knowledge
await improve_memory(ticker="AAPL", session_ids=["chat_123", "chat_456"])

# Improve all stock knowledge
await improve_memory()
```

### list_datasets()

See what stocks have accumulated knowledge.

```python
from skills.cognee_memory.scripts.datasets import list_datasets

datasets = await list_datasets()
print(datasets)  # ['stock_AAPL', 'stock_TSLA', 'stock_NVDA', ...]
```

## Architecture

- **Backend-hosted**: Cognee runs on the Finch backend (single instance, shared knowledge graph)
- **Sandbox scripts call backend API**: Scripts use HTTP calls to `/memory/*` endpoints
- **Auto-seeding**: When a user opens a stock page, the frontend triggers `/memory/seed/{symbol}` which fetches 60 days of FMP news, earnings, analyst targets and stores them in the graph
- **LLM**: Uses OPENAI_API_KEY for entity extraction during `remember()`
- **Knowledge Graph**: Entities (companies, people, events, metrics) connected by typed relationships
- **Self-improvement**: `improve()` promotes session observations into permanent graph with relationship enrichment

## Tips

- Always `recall_stock()` before answering questions about a stock — the graph may already have seeded knowledge from the stock page
- Store both raw news AND your analysis/interpretation — the graph connects them
- Use `session_id` (the chat ID) for in-conversation memory, then `improve()` at the end
- Ticker-scoped datasets keep the graph focused and queries fast
