# 🚀 Final Migration Steps

All code has been updated! Follow these steps to complete the migration:

## 1. Run Database Migration

```bash
cd /Users/anshul/code/finch/backend
alembic upgrade head
```

This will rename the `session_id` column to `user_id` in the `snaptrade_users` table.

## 2. Restart Backend

```bash
# Stop backend (Ctrl+C if running)
cd /Users/anshul/code/finch
./start-backend.sh
```

## 3. Test Everything

1. **Sign in with Google** ✅
2. **Connect brokerage** ✅  
3. **Send chat message** ✅
4. **Check resources** ✅

## What Was Changed

### ✅ Database
- Column renamed: `snaptrade_users.session_id` → `snaptrade_users.user_id`

### ✅ Backend
- **Models**: All use `user_id`
- **CRUD**: Functions renamed (`get_user_by_session` → `get_user_by_id`)
- **Routes**: All accept `user_id` parameter
- **SnapTrade Tools**: All methods use `user_id`
- **Tool System**: `ToolContext` and `AgentContext` use `user_id`
- **Agents**: Updated to use `user_id`

### ✅ Frontend  
- **API calls**: All send `user_id` instead of `session_id`
- **TypeScript interfaces**: Use `user_id`

## Verification

After migration, check the database:

```sql
-- Verify column was renamed
\d snaptrade_users

-- Check data is intact
SELECT user_id, is_connected FROM snaptrade_users;
```

## If Something Goes Wrong

Rollback the migration:

```bash
cd backend
alembic downgrade -1
```

Then restart backend and try again.

---

**Status**: ✅ Code updated, ready to migrate!

