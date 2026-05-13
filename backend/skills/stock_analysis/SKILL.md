---
name: stock_analysis
description: "Stock research notes system. Write analysis to stocks/{SYMBOL}/*.md and it auto-syncs to the database for display on the stock page Analysis tab. Supports multiple notes per stock, each shown as a collapsible card."
metadata:
  emoji: "📝"
  category: research
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---

# Stock Analysis Notes

Write research notes about stocks. Any `.md` file written to `stocks/{SYMBOL}/` via `write_chat_file` is automatically saved to the database and displayed on that stock's Analysis tab.

## How it works

1. Write your analysis as a markdown file using `write_chat_file`
2. The backend auto-detects the `stocks/{SYMBOL}/*.md` pattern and syncs to the database
3. The note appears on the stock's Analysis tab in the frontend
4. The stock is automatically added to the user's watchlist
5. The stock also appears in the user's Research section on the Watchlist page

No extra tool call needed — just write the file. This is also the way to add stocks to the user's watchlist: writing any research note for a stock automatically adds it.

## File conventions

```
stocks/
├── NVDA/
│   ├── analysis.md          # Main research note
│   ├── earnings-q1-2026.md  # Earnings-specific note
│   └── peer-comparison.md   # Comparison note
├── AAPL/
│   ├── analysis.md
│   └── valuation.md
```

- One folder per symbol under `stocks/`
- Each `.md` file becomes a separate note on the Analysis tab
- The first `# Heading` in the file becomes the note title
- Notes are shown newest-first, with the latest expanded by default
- You can store supporting data files (JSON, CSV) in the same folder — only `.md` files become notes

## Writing a note

```python
# Use write_chat_file — the sync happens automatically
write_chat_file(
    filename="stocks/NVDA/analysis.md",
    file_content="""# NVDA — AI Infrastructure Play

## Thesis
NVIDIA dominates AI training and inference hardware...

## Valuation
Trading at 35x forward P/E vs 5-year avg of 45x...

## Catalysts
- Q2 earnings on Aug 28
- Blackwell Ultra ramp in H2

## Risks
- Customer concentration (hyperscalers)
- Export controls on China
"""
)
```

## Updating existing notes

Use `replace_in_chat_file` to update specific sections of an existing note. The database automatically syncs the updated content.

```python
# Read current note first
read_chat_file(filename="stocks/NVDA/analysis.md")

# Update a section
replace_in_chat_file(
    filename="stocks/NVDA/analysis.md",
    old_str="## Catalysts\n- Q2 earnings on Aug 28",
    new_str="## Catalysts\n- Q2 earnings beat: $0.82 vs $0.74 est\n- Blackwell Ultra shipping ahead of schedule"
)
```

## Building on prior analysis

When the user asks to research a stock that already has notes:
1. Read existing notes first: `read_chat_file(filename="stocks/NVDA/analysis.md")`
2. Build on what's there — extend weak sections, correct outdated info, add new developments
3. Create a new note file for distinct topics (e.g., `earnings-q2-2026.md`) rather than cramming everything into one file

## Using data from other skills

Pull data from FMP, Polygon, ORATS, etc. to inform your analysis:

```python
# Fetch fundamentals
from skills.financial_modeling_prep.scripts.market.quote import get_quote_snapshot
from skills.financial_modeling_prep.scripts.company.profile import get_company_profile

quote = get_quote_snapshot("NVDA")
profile = get_company_profile("NVDA")

# Fetch earnings data
from skills.financial_modeling_prep.scripts.earnings.history import get_earnings_history
earnings = get_earnings_history("NVDA", limit=8)

# Store raw data alongside the analysis
import json
write_chat_file(filename="stocks/NVDA/financials.json", file_content=json.dumps(profile, indent=2))

# Write the analysis note (this is what gets synced to DB and shown to user)
write_chat_file(filename="stocks/NVDA/analysis.md", file_content=analysis_markdown)
```

## When to use

- User asks to "research", "analyze", or "look into" a stock
- User asks to save findings or create a research note
- User asks to add a stock to their watchlist — write a brief note to auto-add it
- Building a thesis for a potential trade
- Documenting earnings reactions or event analysis
- Any time you produce substantive stock analysis worth keeping
