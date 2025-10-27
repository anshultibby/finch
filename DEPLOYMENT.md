# Deployment Guide

This guide will help you deploy Finch to Railway (backend) and Vercel (frontend).

## Prerequisites

1. **Railway Account**: Sign up at https://railway.app
2. **Vercel Account**: Sign up at https://vercel.com
3. **GitHub Repository**: Push your code to GitHub (recommended for both platforms)

## Part 1: Deploy Backend to Railway

### Step 1: Create a PostgreSQL Database

1. Go to https://railway.app/new
2. Click "New Project" → "Provision PostgreSQL"
3. Once created, Railway will automatically provide a `DATABASE_URL` environment variable

### Step 2: Deploy the Backend

1. In the same Railway project, click "New" → "GitHub Repo"
2. Connect your GitHub account and select your Finch repository
3. Railway will auto-detect it as a Python project
4. Set the **Root Directory** to `backend`

### Step 3: Configure Environment Variables

In Railway, go to your backend service → Variables tab and add:

```bash
# LLM Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4

# Encryption Key (generate with command below)
ENCRYPTION_KEY=your_encryption_key_here

# API Configuration
API_HOST=0.0.0.0
PORT=8000

# CORS Origins (add your Vercel domain after frontend deployment)
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000

# Optional: Robinhood credentials (or users can login via the app)
# ROBINHOOD_USERNAME=your_username
# ROBINHOOD_PASSWORD=your_password
```

**Generate Encryption Key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Note**: The `DATABASE_URL` should already be automatically set by Railway when you added PostgreSQL.

### Step 4: Run Database Migrations

1. In Railway, go to your backend service → Settings → Deploy Triggers
2. After the first deployment completes, open the service and note your deployment URL
3. You need to run migrations. Go to the service → Settings → Service Variables
4. Add a custom start command or use Railway's shell:
   - Click on your service → Three dots menu → Shell
   - Run: `alembic upgrade head`

**Alternative**: Add a deployment script:
- Create a `railway-migrate.sh` in backend folder with:
```bash
#!/bin/bash
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port $PORT
```
- Update `nixpacks.toml` or `Procfile` to use this script

### Step 5: Get Your Backend URL

1. Go to your backend service in Railway
2. Go to Settings → Domains
3. Click "Generate Domain" to get a public URL (e.g., `https://finch-backend.up.railway.app`)
4. Save this URL for the frontend configuration

## Part 2: Deploy Frontend to Vercel

### Step 1: Deploy to Vercel

1. Go to https://vercel.com/new
2. Import your GitHub repository
3. Configure the project:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
   - **Install Command**: `npm install`

### Step 2: Configure Environment Variables

In Vercel, go to your project → Settings → Environment Variables and add:

```bash
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app
```

Replace `your-backend.up.railway.app` with your actual Railway backend URL from Part 1, Step 5.

### Step 3: Redeploy

After adding the environment variable, trigger a new deployment:
1. Go to Deployments tab
2. Click on the latest deployment → Three dots → Redeploy

### Step 4: Update Backend CORS

1. Go back to Railway → Your backend service → Variables
2. Update the `CORS_ORIGINS` variable to include your Vercel domain:
```bash
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000
```
Replace `your-app.vercel.app` with your actual Vercel deployment URL.

## Part 3: Verify Deployment

### Test Backend

Visit your Railway backend URL:
```
https://your-backend.up.railway.app/health
```

You should see:
```json
{"status": "healthy"}
```

### Test Frontend

1. Visit your Vercel deployment URL: `https://your-app.vercel.app`
2. Try sending a message in the chat
3. If you configured Robinhood, try the Robinhood login

## Monitoring and Logs

### Railway (Backend)
- View logs: Railway Dashboard → Your Service → Deployments → View Logs
- View metrics: Railway Dashboard → Your Service → Metrics

### Vercel (Frontend)
- View deployments: Vercel Dashboard → Your Project → Deployments
- View function logs: Vercel Dashboard → Your Project → Logs

## Troubleshooting

### Backend Issues

**Database Connection Error**
- Ensure `DATABASE_URL` is set correctly in Railway
- Run migrations: `alembic upgrade head` in Railway shell

**CORS Error**
- Update `CORS_ORIGINS` to include your Vercel domain
- Ensure it's a comma-separated list with no spaces

**Import Errors**
- Railway should install from `requirements.txt` automatically
- Check build logs in Railway dashboard

### Frontend Issues

**API Connection Failed**
- Verify `NEXT_PUBLIC_API_URL` is set correctly in Vercel
- Ensure Railway backend is running and accessible
- Check Railway backend logs for errors

**Environment Variables Not Working**
- Environment variables must start with `NEXT_PUBLIC_` to be available in the browser
- Redeploy after adding environment variables

## Updating Your Deployment

### Automatic Deployments

Both Railway and Vercel support automatic deployments from GitHub:

1. **Push to GitHub**: Both platforms will detect changes
2. **Railway**: Automatically rebuilds and deploys backend
3. **Vercel**: Automatically rebuilds and deploys frontend

### Manual Deployments

**Railway:**
1. Go to your service → Deployments
2. Click "Deploy" button

**Vercel:**
1. Go to your project → Deployments
2. Click "Redeploy" on any deployment

## Cost Considerations

### Railway
- Free tier: $5 of usage per month
- Includes PostgreSQL database
- Pays for actual usage

### Vercel
- Free tier: Generous limits for hobby projects
- Includes: 100GB bandwidth, unlimited deployments
- Serverless functions included

## Security Best Practices

1. **Never commit `.env` files** - Use environment variables in Railway/Vercel
2. **Rotate encryption keys** - If compromised, generate new keys
3. **Use strong passwords** - For Robinhood and database
4. **Enable 2FA** - On Railway and Vercel accounts
5. **Monitor logs** - Regularly check for suspicious activity

## Support

- Railway Docs: https://docs.railway.app
- Vercel Docs: https://vercel.com/docs
- GitHub Issues: Create an issue in your repository

## Next Steps

- [ ] Set up custom domain (optional)
- [ ] Configure monitoring and alerts
- [ ] Set up CI/CD pipelines (if not using auto-deploy)
- [ ] Implement rate limiting
- [ ] Add analytics

