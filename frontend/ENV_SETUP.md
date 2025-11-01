# Frontend Environment Setup

## Required Environment Variables

Create a `.env.local` file in the `frontend` directory with the following variables:

### 1. Copy the Template

```bash
cp env.template .env.local
```

### 2. Configure Supabase (Required for Authentication)

Get these values from your Supabase project:
1. Go to [https://app.supabase.com](https://app.supabase.com)
2. Select your project
3. Go to **Settings** → **API**

```env
# Your Supabase Project URL (from Settings -> API -> Project URL)
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co

# Your Supabase Anon/Public Key (from Settings -> API -> Project API keys -> anon public)
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3. Configure Backend API URL

```env
# For local development
NEXT_PUBLIC_API_URL=http://localhost:8000

# For production, use your deployed backend URL
# NEXT_PUBLIC_API_URL=https://api.yourapp.com
```

## Complete Example

Your `.env.local` file should look like this:

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://abcdefghijklmnop.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprbG1ub3AiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTYxNjI4OTMyMCwiZXhwIjoxOTMxODY1MzIwfQ.kCW0kdKv_abcdefghijklmnopqrstuvwxyz123456789

# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Important Notes

### Security
- ✅ **NEXT_PUBLIC_SUPABASE_ANON_KEY is safe to expose** - It's designed to be public (that's what "anon/public" means)
- ⚠️ **Never commit `.env.local`** - It's already in `.gitignore`
- ⚠️ **Never use the service_role key** in the frontend - Only use the anon/public key

### Variable Naming
- All frontend env vars **must** start with `NEXT_PUBLIC_` to be accessible in the browser
- Without this prefix, Next.js won't include them in the build

### After Creating .env.local
- **Restart your dev server** - Next.js only loads env vars on startup
```bash
# Stop the server (Ctrl+C) then restart
npm run dev
```

## Troubleshooting

### "Supabase environment variables not set"
- Make sure you created `.env.local` in the `frontend` directory (not the project root)
- Make sure variable names start with `NEXT_PUBLIC_`
- Restart your dev server

### "Invalid API key" or "Failed to connect"
- Double-check you copied the **anon/public key**, not the service_role key
- Make sure you copied the full key (they're very long, ~200+ characters)
- Verify the Supabase URL is correct (should end with `.supabase.co`)

### Changes not taking effect
- Environment variables are loaded at build time
- Always restart the dev server after changing `.env.local`
- In production, redeploy your app after changing environment variables

## Production Deployment

When deploying to production (Vercel, Netlify, etc.), add these environment variables in your hosting platform's dashboard:

1. **Vercel**: Project Settings → Environment Variables
2. **Netlify**: Site Settings → Build & Deploy → Environment
3. **Docker**: Pass via `-e` flag or docker-compose.yml

Make sure to use your production Supabase project URL and keys!

