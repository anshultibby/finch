# Credits System

A token-based usage tracking system that charges users based on actual LLM API costs with a 20% premium.

## Overview

The credits system:
- **Tracks actual token usage** from LLM calls via LiteLLM
- **Calculates real costs** using up-to-date pricing for each model
- **Applies 20% premium** on top of base costs
- **Converts to credits** at 1000 credits = $1 USD (base cost)
- **Deducts automatically** after each chat turn
- **Prevents usage** when balance reaches zero

## Architecture

### Database Schema

#### `snaptrade_users` table (extended)
```sql
ALTER TABLE snaptrade_users
ADD COLUMN credits INTEGER NOT NULL DEFAULT 500,
ADD COLUMN total_credits_used INTEGER NOT NULL DEFAULT 0;
```

#### `credit_transactions` table (new)
```sql
CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    amount INTEGER NOT NULL,              -- Positive for additions, negative for deductions
    balance_after INTEGER NOT NULL,       -- Balance after this transaction
    transaction_type VARCHAR NOT NULL,    -- 'chat_turn', 'admin_adjustment', 'initial_credit'
    description VARCHAR NOT NULL,         -- Human-readable description
    chat_id VARCHAR,                      -- Optional link to chat
    tool_name VARCHAR,                    -- Optional tool name
    metadata JSONB,                       -- Token counts, model, costs, etc.
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_credit_transactions_user_id ON credit_transactions(user_id);
CREATE INDEX idx_credit_transactions_chat_id ON credit_transactions(chat_id);
CREATE INDEX idx_credit_transactions_created_at ON credit_transactions(created_at DESC);
```

### Components

1. **`services/credits.py`** - Core credits service
   - Token → USD cost calculation
   - USD → credits conversion (with 20% premium)
   - Credit deduction/addition
   - Transaction logging

2. **`routes/credits.py`** - API endpoints
   - `GET /credits/balance/{user_id}` - Check balance
   - `GET /credits/history/{user_id}` - View transaction history
   - `POST /credits/add` - Add credits (admin)
   - `GET /credits/pricing` - View pricing info

3. **`modules/chat_service.py`** - Integration
   - Pre-check: Blocks chat if credits = 0
   - Post-processing: Deducts credits after each turn

4. **`modules/agent/llm_handler.py`** - Token tracking
   - Already tracks tokens via LiteLLM
   - Provides session-level usage data
   - Calculates costs with cache handling

## Pricing

### Model Costs (per million tokens)

| Model | Input | Output | Cache Read | Cache Write |
|-------|-------|--------|------------|-------------|
| Claude Sonnet 4.5 | $3.00 | $15.00 | $0.30 | $3.75 |
| Claude Opus 4.5 | $15.00 | $75.00 | $1.50 | $18.75 |
| GPT-4o | $2.50 | $10.00 | $1.25 | $2.50 |
| GPT-4o Mini | $0.15 | $0.60 | $0.075 | $0.15 |
| Gemini 2.5 Pro | $1.25 | $5.00 | $0.125 | $1.5625 |

### Credit Calculation

```python
# Step 1: Calculate USD cost
usd_cost = (uncached_input_tokens / 1M * input_price) + 
           (cache_read_tokens / 1M * cache_read_price) + 
           (cache_creation_tokens / 1M * cache_write_price) + 
           (output_tokens / 1M * output_price)

# Step 2: Apply 20% premium
cost_with_premium = usd_cost * 1.2

# Step 3: Convert to credits (1000 credits = $1)
credits = ceil(cost_with_premium * 1000)
```

### Example Calculation

**Scenario:** Chat turn with Claude Sonnet 4.5
- 100,000 input tokens (uncached)
- 10,000 output tokens
- No caching

**Calculation:**
```
Input cost:  (100K / 1M) * $3.00  = $0.30
Output cost: (10K / 1M)  * $15.00 = $0.15
Total cost:                        = $0.45
With 20% premium:                  = $0.54
Credits charged:                   = 540 credits
```

## Setup

### 1. Run Migration

```bash
cd backend
python scripts/migrate_add_credits.py
```

This will:
- Add `credits` and `total_credits_used` columns to `snaptrade_users`
- Create `credit_transactions` table
- Set 500 default credits for existing users
- Create initial transaction records

### 2. Verify Installation

```bash
# Check the API is running
curl http://localhost:8000/health

# Check pricing info
curl http://localhost:8000/credits/pricing

# Check a user's balance (replace with actual user_id)
curl http://localhost:8000/credits/balance/YOUR_USER_ID
```

## Usage

### API Endpoints

#### Get Credit Balance
```bash
GET /credits/balance/{user_id}

Response:
{
  "user_id": "abc-123",
  "credits": 500,
  "total_credits_used": 0
}
```

#### Get Transaction History
```bash
GET /credits/history/{user_id}?limit=50

Response:
{
  "user_id": "abc-123",
  "transactions": [
    {
      "id": "uuid",
      "amount": -50,
      "balance_after": 450,
      "transaction_type": "chat_turn",
      "description": "Chat turn (2 LLM calls, 15,432 tokens)",
      "chat_id": "chat-xyz",
      "metadata": {
        "model": "claude-sonnet-4-5",
        "prompt_tokens": 12000,
        "completion_tokens": 3432,
        "usd_cost": 0.0415,
        "premium_rate": 1.2
      },
      "created_at": "2025-01-23T10:30:00Z"
    }
  ],
  "count": 1
}
```

#### Add Credits (Admin)
```bash
POST /credits/add
Content-Type: application/json

{
  "user_id": "abc-123",
  "credits": 1000,
  "description": "Bonus credits for early adopter"
}

Response:
{
  "success": true,
  "user_id": "abc-123",
  "credits_added": 1000,
  "new_balance": 1500,
  "message": "Bonus credits for early adopter"
}
```

#### Get Pricing Information
```bash
GET /credits/pricing

Response:
{
  "credits_per_dollar": 1000,
  "premium_multiplier": 1.2,
  "info": "Credits are calculated based on actual token usage with a 20% premium.",
  "model_pricing": { ... },
  "example": { ... }
}
```

### CLI Tool

```bash
# Check balance
python scripts/manage_credits.py balance <user_id>

# Add credits
python scripts/manage_credits.py add <user_id> <amount> "Optional description"

# View history
python scripts/manage_credits.py history <user_id> [limit]
```

**Examples:**
```bash
# Check balance
python scripts/manage_credits.py balance abc-123

# Add 1000 credits
python scripts/manage_credits.py add abc-123 1000 "Bonus credits"

# View last 50 transactions
python scripts/manage_credits.py history abc-123 50
```

## How It Works

### Chat Flow with Credits

1. **User sends message**
   ```
   POST /chat/stream
   ```

2. **Pre-check: Verify credits**
   ```python
   user_credits = await CreditsService.get_user_credits(db, user_id)
   if user_credits <= 0:
       return error("Insufficient credits")
   ```

3. **Process message**
   - LLMHandler tracks tokens in real-time
   - UsageTracker accumulates token counts
   - Chat streaming happens normally

4. **Post-processing: Deduct credits**
   ```python
   usage_tracker = LLMHandler.get_session_usage(chat_id)
   
   # Calculate credits based on actual tokens
   credits = calculate_credits_for_llm_call(
       model=usage_tracker.model,
       prompt_tokens=usage_tracker.total_prompt_tokens,
       completion_tokens=usage_tracker.total_completion_tokens,
       cache_read_tokens=usage_tracker.total_cache_read_tokens,
       cache_creation_tokens=usage_tracker.total_cache_creation_tokens
   )
   
   # Deduct and log transaction
   await CreditsService.deduct_credits(
       db=db,
       user_id=user_id,
       credits=credits,
       transaction_type="chat_turn",
       description=f"Chat turn ({tokens:,} tokens)",
       chat_id=chat_id,
       metadata={...}
   )
   ```

### Transaction Logging

Every credit change creates a `CreditTransaction` record with:
- **amount**: Positive for additions, negative for deductions
- **balance_after**: Snapshot of balance after transaction
- **transaction_type**: Categorizes the transaction
- **description**: Human-readable summary
- **metadata**: Detailed context (tokens, model, costs, etc.)

This provides:
- ✅ Complete audit trail
- ✅ Debugging transparency
- ✅ User-facing transaction history
- ✅ Analytics on usage patterns

## Cost Analysis

### What 500 credits gets you

With **Claude Sonnet 4.5** (most common model):

| Activity | Approx. Tokens | Credits | Chat Turns |
|----------|---------------|---------|------------|
| Simple question | 5K in + 1K out | ~6 | ~83 turns |
| Code generation | 10K in + 5K out | ~15 | ~33 turns |
| Complex analysis | 50K in + 10K out | ~60 | ~8 turns |
| Strategy deployment | 100K in + 20K out | ~120 | ~4 turns |

### Premium Justification

The 20% premium covers:
- Infrastructure costs (hosting, databases, monitoring)
- Support and maintenance
- Feature development
- Reasonable profit margin

Base cost is transparent in transaction metadata so users can see:
- Actual API cost: $0.045
- With premium: $0.054
- Credits charged: 54

## Monitoring

### For Developers

```python
# Check session usage before finalization
usage = LLMHandler.get_session_usage(chat_id)
print(f"Tokens: {usage.total_prompt_tokens + usage.total_completion_tokens}")
print(f"Cost: ${usage.calculate_cost()['total_cost']:.4f}")

# Check user balance
credits = await CreditsService.get_user_credits(db, user_id)
print(f"User has {credits} credits")
```

### For Admins

```bash
# Monitor recent transactions across all users
psql -d finch -c "
  SELECT user_id, SUM(amount) as total_spent, COUNT(*) as transactions
  FROM credit_transactions
  WHERE created_at > NOW() - INTERVAL '24 hours'
  GROUP BY user_id
  ORDER BY total_spent;
"

# Check users with low credits
psql -d finch -c "
  SELECT user_id, credits, total_credits_used
  FROM snaptrade_users
  WHERE credits < 100
  ORDER BY credits;
"
```

## Future Enhancements

- [ ] Payment integration (Stripe) for automatic top-ups
- [ ] Credit packages (500, 1000, 5000 credits)
- [ ] Email notifications at low balance thresholds
- [ ] Usage analytics dashboard
- [ ] Per-tool credit tracking (not just LLM calls)
- [ ] Referral credits
- [ ] Enterprise plans with negotiated rates

## Notes

- Default allocation: **500 credits** = ~$0.42 base cost = ~$0.50 with premium
- Free tier for testing, but requires users to top up for continued use
- All costs are transparent via transaction metadata
- Credits never expire
- Admin can add credits manually via API or CLI
