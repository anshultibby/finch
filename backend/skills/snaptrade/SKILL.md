---
name: snaptrade
description: Internal server-side SnapTrade client. NOT usable from the sandbox — use the connected_accounts skill (finch_api) instead for brokerage data.
metadata:
  emoji: "🏦"
  category: brokerage
  is_system: true
  auto_on: false
  requires:
    env:
      - SNAPTRADE_CLIENT_ID
      - SNAPTRADE_CONSUMER_KEY
    bins: []
---

# SnapTrade (Internal — Do Not Use From Sandbox)

This skill contains server-side SnapTrade client code used by backend routes. It requires credentials (`user_secret`) that are NOT available in the sandbox.

**For brokerage data in the sandbox, use the `connected_accounts` skill instead:**

```python
from skills.finch_api.scripts import sync_transactions, get_transactions
```

See the `connected_accounts` skill SKILL.md for full documentation.
