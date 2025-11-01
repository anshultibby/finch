# Google OAuth Setup Guide with Supabase

Your Finch app now uses Google OAuth for authentication via Supabase! Follow these steps to complete the setup.

## 🚀 Quick Setup

### 1. Create a Supabase Project

1. Go to [https://app.supabase.com](https://app.supabase.com)
2. Click "New Project"
3. Choose your organization (or create one)
4. Fill in:
   - **Project Name**: `finch` (or any name you prefer)
   - **Database Password**: Generate a secure password
   - **Region**: Choose closest to your users
5. Click "Create new project" and wait ~2 minutes for it to initialize

### 2. Enable Google OAuth in Supabase

1. In your Supabase project, go to **Authentication** → **Providers**
2. Find **Google** in the list and click on it
3. Toggle **Enable Sign in with Google** to ON
4. You'll need to set up Google OAuth credentials:

#### Get Google OAuth Credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Go to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth client ID**
5. If prompted, configure the OAuth consent screen:
   - Choose **External** (unless you have a Google Workspace)
   - Fill in:
     - App name: `Finch`
     - User support email: Your email
     - Developer contact: Your email
   - Click **Save and Continue** through the scopes and test users
6. Back at Create OAuth client ID:
   - Application type: **Web application**
   - Name: `Finch Web Client`
   - **Authorized JavaScript origins**:
     - `http://localhost:3000` (for development)
     - Your production domain (when deploying)
   - **Authorized redirect URIs**:
     - `https://YOUR_PROJECT_REF.supabase.co/auth/v1/callback`
     - (You'll find YOUR_PROJECT_REF in your Supabase project URL)
7. Click **Create**
8. Copy the **Client ID** and **Client Secret**

#### Configure in Supabase:

1. Back in Supabase, paste:
   - **Client ID** (from Google)
   - **Client Secret** (from Google)
2. **Authorized Client IDs**: Leave empty (optional)
3. Click **Save**

### 3. Configure Your Frontend

1. In your Supabase project, go to **Settings** → **API**
2. Copy these values:
   - **Project URL**
   - **anon/public key** (under Project API keys)

3. Create a `.env.local` file in the `frontend` directory:

```bash
cd frontend
cp .env.local.example .env.local
```

4. Edit `.env.local` with your values:

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-public-key-here

# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4. Test Your Setup

1. Start your backend:
```bash
./start-backend.sh
```

2. In a new terminal, start your frontend:
```bash
./start-frontend.sh
```

3. Open [http://localhost:3000](http://localhost:3000)
4. Click **"Continue with Google"**
5. Sign in with your Google account
6. You should be redirected back and logged in!

## ✨ What Changed

### Frontend Changes

- ✅ **Installed** `@supabase/supabase-js`
- ✅ **Created** `lib/supabase.ts` - Supabase client configuration
- ✅ **Created** `contexts/AuthContext.tsx` - Auth state management
- ✅ **Updated** `components/PasswordGate.tsx` → Now `AuthGate` with Google OAuth
- ✅ **Updated** `components/ChatContainer.tsx` - Uses Supabase user ID
- ✅ **Updated** `app/layout.tsx` - Wrapped with AuthProvider
- ✅ **Created** `app/auth/callback/page.tsx` - OAuth callback handler
- ✅ **Added** Sign out button in header

### User Experience

- 🔐 **Secure Authentication**: Users sign in with their Google account
- 🎨 **Beautiful UI**: Modern Google sign-in button with branding
- 👤 **User Identity**: Each user gets a unique ID from Supabase
- 🚪 **Easy Sign Out**: Sign out button in the top-right corner
- 📧 **Email Display**: Shows user's email in the header

## 🔒 Security Benefits

1. **No Password Storage**: Google handles authentication
2. **JWT Tokens**: Secure session management via Supabase
3. **User Isolation**: Each user has their own data (user ID is from Supabase)
4. **Easy to Extend**: Add more OAuth providers (GitHub, Facebook, etc.) later

## 🎯 Next Steps (Optional)

### Add Backend JWT Verification

For production, you should verify Supabase JWT tokens in your backend:

1. Install Supabase Python SDK in backend:
```bash
cd backend
source venv/bin/activate
pip install supabase
```

2. Add JWT verification middleware to validate requests
3. This ensures only authenticated users can access your API

### Add More OAuth Providers

Supabase supports many providers:
- GitHub
- Azure
- Facebook
- Twitter/X
- Apple
- Discord
- And more!

Just enable them in **Authentication → Providers** in Supabase.

## 📝 Notes

- **Development**: OAuth callback is `http://localhost:3000/auth/callback`
- **Production**: Update Google OAuth redirect URIs with your production domain
- **User Data**: User info is stored in Supabase (email, metadata, etc.)
- **Session Storage**: Sessions are automatically managed by Supabase

## 🐛 Troubleshooting

### "Invalid client" error
- Make sure your Google OAuth redirect URI matches exactly: `https://YOUR_PROJECT_REF.supabase.co/auth/v1/callback`

### Sign-in button doesn't work
- Check browser console for errors
- Verify `.env.local` has correct Supabase URL and anon key
- Make sure Google OAuth is enabled in Supabase

### Gets stuck on "Completing sign in..."
- Check that the callback page is working
- Open browser DevTools → Network tab to see if there are any failed requests

### "Supabase environment variables not set"
- Make sure `.env.local` exists in the `frontend` directory
- Restart the Next.js dev server after creating `.env.local`

## 🎉 Done!

Your app now has professional Google OAuth authentication! Users can sign in with one click and their data is secure and isolated.

