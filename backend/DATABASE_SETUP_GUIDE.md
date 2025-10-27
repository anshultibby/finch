# Database Setup Guide

Complete guide for setting up Supabase PostgreSQL database with encrypted token storage.

---

## Quick Start (5 Minutes)

### Step 1: Get Your Supabase Database URL

1. Go to https://supabase.com/dashboard
2. Select your project (or create new)
3. Click **⚙️ Settings** → **Database**
4. Scroll to **"Connection String"** → Click **"URI"** tab
5. Copy the URL (replace `[YOUR-PASSWORD]` with your actual password):
   ```
   postgresql://postgres:YourPassword@db.xxx.supabase.co:5432/postgres
   ```

**Has special characters like `@` in password?** URL-encode it:
```bash
python scripts/encode_password.py "MyP@ssword"
# Use the encoded version in your DATABASE_URL
```

### Step 2: Generate Encryption Key

**Option A: Quick command**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Option B: Use the script**
```bash
python scripts/generate_encryption_key.py
```

Copy the output (looks like: `abcd1234efgh5678...xyz=`)

### Step 3: Configure Environment

```bash
cd backend
cp env.template .env
```

Edit `.env` and add:
```env
DATABASE_URL=postgresql://postgres:YourPassword@db.xxx.supabase.co:5432/postgres
ENCRYPTION_KEY=your_generated_key_from_step_2
```

### Step 4: Install Dependencies & Run Migration

```bash
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

**Done!** ✅ You should see:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Create robinhood_sessions table
```

### Step 5: Verify

Check Supabase Dashboard → **Table Editor** → You should see `robinhood_sessions` table!

---

## What This Does

### Security Features
- ✅ **Tokens encrypted at rest** (Fernet AES-128)
- ✅ **Per-user token isolation** (no more single-user limitation!)
- ✅ **Automatic token expiry tracking**
- ✅ **No credentials passed to LLM**

### Database Schema

**`robinhood_sessions` table:**
```sql
session_id              VARCHAR  (Primary Key)
encrypted_access_token  TEXT     (Fernet encrypted)
encrypted_refresh_token TEXT     (Fernet encrypted)
token_expires_at        TIMESTAMP
device_token           VARCHAR  (for 2FA)
logged_in              BOOLEAN
created_at             TIMESTAMP
last_activity          TIMESTAMP
```

---

## Common Commands

```bash
# Check current migration version
alembic current

# View migration history
alembic history

# Rollback last migration
alembic downgrade -1

# Create new migration after model changes
alembic revision --autogenerate -m "description"
```

---

## Troubleshooting

### "Can't connect to database"
- ✅ Check `DATABASE_URL` is correct in `.env`
- ✅ Verify password is URL-encoded if it has special chars
- ✅ Use port **5432** (connection pooler, not 6543)
- ✅ Check Supabase project is active

### "ENCRYPTION_KEY not set"
```bash
# Generate a new key
python scripts/generate_encryption_key.py

# Add to .env
ENCRYPTION_KEY=paste_key_here
```

### "Table already exists"
```bash
# Check current state
alembic current

# If no migrations run, mark as applied without executing
alembic stamp head
```

### Test your connection
```bash
python -c "from database import engine; print('✅ Connected!', engine.connect())"
```

---

## File Structure

```
backend/
├── alembic/                    # Database migrations
│   └── versions/
│       └── 001_create_robinhood_sessions.py
├── crud/                       # Database operations
│   └── robinhood_session.py
├── models/
│   └── db.py                   # SQLAlchemy models
├── services/
│   └── encryption.py           # Token encryption
├── scripts/
│   ├── generate_encryption_key.py
│   ├── encode_password.py
│   └── setup_database.sh       # Automated setup
├── database.py                 # DB connection
└── alembic.ini                 # Migration config
```

---

## Automated Setup Script

Run everything at once:
```bash
cd backend
source venv/bin/activate
./scripts/setup_database.sh
```

This will:
1. Check `.env` configuration
2. Install dependencies
3. Run migrations
4. Verify setup

---

## Security Best Practices

### ⚠️ Never Commit These:
- `.env` file (contains DATABASE_URL and ENCRYPTION_KEY)
- Database passwords
- Encryption keys

### ✅ Always:
- Use different encryption keys for dev/staging/prod
- Backup your encryption key securely (losing it = losing all encrypted data)
- Rotate database passwords regularly
- Use connection pooler (port 5432) for better performance

---

## Next Steps

After database setup:
1. ✅ Restart backend server
2. ✅ Test Robinhood login through frontend
3. ✅ Check Supabase Table Editor for encrypted tokens
4. ✅ Verify portfolio fetch works

See `MULTI_USER_AUTH_PLAN.md` for architecture details.

---

## Need Help?

**Connection Issues**
- Verify Supabase project is running
- Check firewall/network settings
- Try direct connection test: `psql "your_database_url"`

**Migration Issues**
```bash
# View full migration status
alembic history --verbose

# Force apply migrations (⚠️ use carefully)
alembic stamp head
```

**Encryption Issues**
```bash
# Test encryption service
python -c "
from services import encryption_service
token = 'test_token'
encrypted = encryption_service.encrypt(token)
print('Encrypted:', encrypted)
decrypted = encryption_service.decrypt(encrypted)
print('Decrypted:', decrypted)
assert token == decrypted
print('✅ Encryption working!')
"
```

