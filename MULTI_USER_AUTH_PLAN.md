# Multi-User Authentication Implementation Plan

## Current Limitation

**Problem**: `robin_stocks` uses a single global pickle file (`~/.tokens/robinhood.pickle`) for session storage.

**Impact**:
- ❌ Only 1 Robinhood user can be logged in at a time
- ❌ User A logging in overwrites User B's session
- ❌ Not production-ready for multi-tenant applications

## Solution Architecture

### Option 1: Per-User Session Files (EASIEST)
**Complexity**: 🟢 Low (2-3 hours)

**Implementation**:
1. Patch `robin_stocks` to accept custom pickle file path
2. Store separate pickle files per session_id: `~/.tokens/robinhood_{session_id}.pickle`
3. Before each `rh` call, temporarily redirect the library's pickle path

**Code Changes**:
```python
# In robinhood_tools.py

def _set_user_session_file(self, session_id: str):
    """Temporarily switch robin_stocks to use per-user session file"""
    import robin_stocks.robinhood.authentication as auth
    auth.PICKLE_PATH = f"~/.tokens/robinhood_{session_id}.pickle"

def get_portfolio(self, session_id: str):
    self._set_user_session_file(session_id)  # Switch context
    holdings = rh.build_holdings()           # Use user's session
    # ...
```

**Pros**:
- ✅ Minimal code changes
- ✅ Leverages existing `robin_stocks` session management
- ✅ No database required

**Cons**:
- ⚠️ File-based storage (not great for containerized/serverless)
- ⚠️ No encryption at rest
- ⚠️ Monkey-patching library internals (brittle)

---

### Option 2: Database Token Storage (RECOMMENDED)
**Complexity**: 🟡 Medium (1-2 days)

**Implementation**:
1. Add database table for storing encrypted tokens per user
2. Manually call Robinhood API endpoints (bypass `robin_stocks` session management)
3. Handle token refresh logic ourselves

**Database Schema**:
```sql
CREATE TABLE robinhood_sessions (
    session_id VARCHAR PRIMARY KEY,
    encrypted_access_token TEXT NOT NULL,
    encrypted_refresh_token TEXT NOT NULL,
    token_expires_at TIMESTAMP NOT NULL,
    device_token TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity TIMESTAMP DEFAULT NOW()
);
```

**Code Structure**:
```python
# New file: backend/modules/robinhood_auth.py

from cryptography.fernet import Fernet
import requests

class RobinhoodAuthManager:
    def __init__(self, encryption_key: str):
        self.cipher = Fernet(encryption_key)
        self.base_url = "https://api.robinhood.com"
    
    def store_tokens(self, session_id: str, access_token: str, refresh_token: str):
        """Encrypt and store tokens in database"""
        encrypted_access = self.cipher.encrypt(access_token.encode())
        encrypted_refresh = self.cipher.encrypt(refresh_token.encode())
        # Save to DB...
    
    def get_valid_token(self, session_id: str) -> str:
        """Get token, refreshing if needed"""
        session = self._get_session_from_db(session_id)
        if session.is_expired():
            return self._refresh_token(session)
        return self._decrypt_token(session.access_token)
    
    def make_authenticated_request(self, session_id: str, endpoint: str):
        """Make API call with user's token"""
        token = self.get_valid_token(session_id)
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{self.base_url}{endpoint}", headers=headers)
        return response.json()
```

**Migration Steps**:
1. Add dependencies: `pip install sqlalchemy cryptography`
2. Create migration for `robinhood_sessions` table
3. Implement `RobinhoodAuthManager` class
4. Replace `rh.login()` with manual OAuth flow
5. Replace `rh.build_holdings()` with direct API calls
6. Update `robinhood_tools.py` to use new auth manager

**Pros**:
- ✅ Production-ready
- ✅ Encrypted token storage
- ✅ Works in containerized environments
- ✅ Full control over token lifecycle
- ✅ Can add audit logging, token revocation, etc.

**Cons**:
- ❌ More code to write and maintain
- ❌ Need to handle OAuth refresh logic manually
- ❌ Requires database setup

---

### Option 3: Context Manager Integration (SIMPLEST FOR NOW)
**Complexity**: 🟢 Very Low (30 minutes)

**Implementation**:
Store tokens in existing `ContextManager` (in-memory only, for development)

**Code Changes**:
```python
# In robinhood_tools.py

from modules.context_manager import context_manager

def setup_robinhood_connection(self, username: str, password: str, session_id: str, mfa_code=None):
    login_result = rh.login(...)
    
    # Store tokens in context manager (in-memory)
    context_manager.set_context(session_id, "rh_access_token", login_result['access_token'])
    context_manager.set_context(session_id, "rh_refresh_token", login_result['refresh_token'])
    context_manager.set_context(session_id, "rh_expires_at", login_result['expires_in'])
    
    # Mark as logged in
    self._sessions[session_id] = RobinhoodSession(logged_in=True, ...)

def get_portfolio(self, session_id: str):
    # Get token from context
    access_token = context_manager.get_context(session_id, "rh_access_token")
    
    # Make API call with stored token
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://api.robinhood.com/positions/", headers=headers)
    # Parse and return...
```

**Pros**:
- ✅ Quick to implement
- ✅ Uses existing infrastructure
- ✅ Separates concerns (tokens in context, not in session state)

**Cons**:
- ❌ In-memory only (lost on restart)
- ❌ Still doesn't solve multi-user with `robin_stocks` library
- ❌ Not production-ready

---

## Recommended Approach

### **Phase 1: Now (Development)**
- ✅ Keep current implementation
- ✅ Document limitation
- ✅ Add warning log when multiple users detected

### **Phase 2: Pre-Production (Before Real Users)**
- 🔨 Implement **Option 2** (Database Token Storage)
- 🔨 Add proper encryption using environment variable key
- 🔨 Set up token refresh background job

### **Phase 3: Production Hardening**
- 🔨 Add token revocation on logout
- 🔨 Implement rate limiting per user
- 🔨 Add audit logging for all Robinhood API calls
- 🔨 Set up monitoring for token expiry/refresh failures

---

## Effort Estimate

| Task | Time | Difficulty |
|------|------|------------|
| Database schema + migrations | 1 hour | Easy |
| Encryption setup | 1 hour | Easy |
| OAuth flow implementation | 4 hours | Medium |
| Token refresh logic | 2 hours | Medium |
| Replace robin_stocks calls with direct API | 4 hours | Medium |
| Testing + debugging | 4 hours | Medium |
| **TOTAL** | **~2 days** | **Medium** |

---

## Security Notes

**Current State**:
- ✅ Credentials never passed to LLM
- ✅ Tokens never logged
- ⚠️ Tokens stored unencrypted in pickle file
- ❌ Single global session file

**After Implementation**:
- ✅ Credentials never passed to LLM
- ✅ Tokens never logged
- ✅ Tokens encrypted at rest in database
- ✅ Per-user session isolation
- ✅ Token rotation and expiry handling
- ✅ Audit trail of all API calls

---

## Quick Win: Add Warning for Now

Add this to detect multi-user scenario:

```python
# In robinhood_tools.py

def setup_robinhood_connection(self, username: str, password: str, session_id: str, mfa_code=None):
    # Warn if another user is already logged in
    if len(self._sessions) > 0:
        print("⚠️ WARNING: Multiple users detected. Current robin_stocks implementation "
              "uses global session storage. New login will overwrite previous user's session. "
              "See MULTI_USER_AUTH_PLAN.md for production implementation.", flush=True)
    
    # ... rest of implementation
```

---

## References

- **Robinhood API Documentation**: https://github.com/sanko/Robinhood
- **robin_stocks Source**: https://github.com/jmfernandes/robin_stocks
- **OAuth 2.0 Refresh Token Flow**: https://oauth.net/2/grant-types/refresh-token/

