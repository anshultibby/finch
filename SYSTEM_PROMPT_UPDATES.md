# System Prompt & Agent Config Updates

## Changes Made

### 1. System Prompt (`backend/modules/agent/prompts.py`)

**Added Section 6: Financial Code Generation**
```
6. **Financial Code Generation** (generate_financial_code) - NEW!:
   → Generate Python code from natural language for financial analysis
   → When user asks to:
     * "Create code to analyze revenue growth"
     * "Write a function to screen stocks"
     * "Generate code to calculate profitability metrics"
   → The tool will:
     * Generate validated Python code using AI
     * Test it with sample data
     * Save it to a file in the chat
     * Show progress with todo.md tracking
   ...
```

**Added Section 7: Execute Generated Code**
```
7. **Execute Generated Code** (execute_financial_code):
   → Run previously generated code on tickers
   → Example: execute_financial_code(filename="screen_growth.py", ticker="AAPL")
   → Automatically fetches needed FMP data
   → Returns analysis results
   → For batch analysis: use batch_execute_code on multiple tickers
```

**Added Section 8: File Management**
```
8. **File Management**:
   → Files are saved in the current chat directory
   → Users can see all files created
   → Use read_chat_file to inspect generated code
   → Use replace_in_chat_file to fix/modify code
   → Use find_in_chat_file to search for functions/patterns
```

**Added Complete Example Workflow**
Shows Finch exactly how to:
1. Generate code from user request
2. Show progress (todo.md steps)
3. Execute code on tickers
4. Present results in table format

### 2. Agent Config (`backend/modules/agent/agent_config.py`)

**Added Tools to MAIN_AGENT_TOOLS:**
```python
# Financial Code Generation (NEW - Manus-inspired)
'generate_financial_code',     # Generate Python code from description
'execute_financial_code',      # Execute code on ticker
'batch_execute_code',          # Execute code on multiple tickers

# File Management (Enhanced)
'replace_in_chat_file',        # Edit files (Manus-style)
'find_in_chat_file',           # Search files with regex
```

## What Finch Now Knows

### 1. When to Generate Code
✅ User asks: "Create code to...", "Generate a function to...", "Write code for..."
✅ Complex analysis that needs custom calculations
✅ Screening stocks with specific criteria
✅ Reusable analysis that can run on multiple tickers

### 2. How to Use the Tools
✅ Call `generate_financial_code` with clear description
✅ Wait for 5-step validation (shown via todo.md)
✅ Code is automatically saved to chat directory
✅ Execute code with `execute_financial_code` or `batch_execute_code`

### 3. File Management
✅ Can read generated code files
✅ Can edit/fix code files
✅ Can search for patterns in code
✅ All files visible to user in chat sidebar

## Example Conversation Flow

**User:** "Create code to find stocks with high profit margins"

**Finch Response:**
```
I'll generate code to screen for stocks with high profit margins.

[Calls generate_financial_code with description:
"Find stocks with net profit margin >20% and operating margin >15%"]

✓ Creating code...
  → Step 1/5: Analyzing requirements ✓
  → Step 2/5: Generating code ✓
  → Step 3/5: Validating ✓
  → Step 4/5: Testing ✓
  → Step 5/5: Saving to profit_margin_screen.py ✓

Created `profit_margin_screen.py` - a function that analyzes profit margins.
Let me test it on some stocks.

[Calls batch_execute_code on ["AAPL", "MSFT", "GOOGL"]]

Here are the results:

| Ticker | Net Margin | Operating Margin | Result |
|--------|------------|------------------|--------|
| AAPL   | 25.3%      | 30.1%           | ✓ BUY  |
| MSFT   | 36.2%      | 42.5%           | ✓ BUY  |
| GOOGL  | 21.2%      | 25.8%           | ✓ BUY  |

All three meet the criteria with exceptional profitability! MSFT leads with 
36% net margin.
```

## Benefits

1. **Finch is now code-aware** - Can generate, execute, and manage Python code
2. **Transparent progress** - Shows 5-step validation with todo.md
3. **Reusable analysis** - Generated code works on any ticker
4. **File-based** - All code saved for user to download/inspect
5. **Batch-capable** - Can analyze 100+ stocks with one code file

## Testing

Test with these prompts:
- "Create code to calculate revenue growth over 3 years"
- "Generate a function to find undervalued stocks"
- "Write code to analyze profitability metrics"
- "Create a stock screener for high-growth companies"

Finch should:
1. Call `generate_financial_code`
2. Show progress (todo.md steps)
3. Save code to file
4. Optionally execute on tickers
5. Present results clearly

