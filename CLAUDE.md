# Finch — Development Notes

## Adding a new API key

When you add a new external API key to the project, you must update **three** places or it won't reach the E2B sandbox:

1. **`backend/core/config.py`** — add the field to `Settings` so it loads from `.env`
2. **`backend/.env`** — add the actual key value
3. **`backend/modules/tools/skills_registry.py` → `SKILL_ENV_KEYS`** — add the env var to the whitelist so `_build_sandbox_env()` forwards it to the sandbox

If you skip step 3, the key will be available on the backend server but **not** inside the E2B sandbox where skills and user code run.

Example entry in `SKILL_ENV_KEYS`:
```python
"MY_NEW_API_KEY": ("MY_SERVICE", "system"),
```

Use `"system"` for keys shared across all users (from `.env`). Use `"user"` for per-user keys stored in the DB.
