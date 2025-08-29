# Railway Deployment Guide

## Overview
This guide explains how to deploy both the backend API and frontend application to Railway for a complete cloud-hosted solution.

## Current Status
- ✅ **Backend API**: Already deployed at `https://hockey-analytics-production.up.railway.app`
- 🚀 **Frontend**: Ready to deploy

## Frontend Deployment Steps

### 1. Create a New Service in Railway

1. Go to your Railway project dashboard
2. Click "New Service"
3. Choose "GitHub Repo"
4. Select your repository
5. **IMPORTANT**: Set the root directory to `/frontend`

### 2. Configure Environment Variables

In the Railway service settings, add these environment variables:

```env
# Backend API URL (your deployed backend)
NEXT_PUBLIC_API_URL=https://hockey-analytics-production.up.railway.app

# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://ghtzaarvfrpplgyxdppy.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key

# Node environment
NODE_ENV=production
```

### 3. Configure Build Settings

Railway should auto-detect Next.js, but verify these settings:

- **Build Command**: `npm install && npm run build`
- **Start Command**: `npm start`
- **Root Directory**: `/frontend`
- **Watch Paths**: `/frontend/**`

### 4. Deploy

1. Push your code to GitHub
2. Railway will automatically deploy
3. Wait for the build to complete (~3-5 minutes)
4. Get your frontend URL from Railway

## Two-Service Architecture

Your Railway project will have two services:

```
Railway Project
├── hockey-analytics (Backend API)
│   ├── URL: https://hockey-analytics-production.up.railway.app
│   ├── Root: /backend
│   └── Port: 8080
│
└── hockey-analytics-frontend (Frontend)
    ├── URL: https://hockey-analytics-frontend-production.up.railway.app
    ├── Root: /frontend
    └── Port: 3000
```

## Testing the Deployed Application

### 1. Backend Health Check
```bash
curl https://hockey-analytics-production.up.railway.app/health
```

### 2. Frontend Access
Open your browser to:
```
https://hockey-analytics-frontend-production.up.railway.app
```

### 3. Full Flow Test
1. Upload a video through the frontend
2. Watch processing status
3. View the processed video with HLS streaming
4. Interact with events and timeline

## Environment Variables Reference

### Backend (already configured)
- `SUPABASE_URL`
- `SUPABASE_KEY` (service role key)
- `RAILWAY_ENVIRONMENT=production`
- `PORT=8080`

### Frontend (needs configuration)
- `NEXT_PUBLIC_API_URL` - Your backend Railway URL
- `NEXT_PUBLIC_SUPABASE_URL` - Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Supabase anon key
- `NODE_ENV=production`

## Troubleshooting

### Frontend can't connect to backend
- Verify `NEXT_PUBLIC_API_URL` is set correctly
- Check CORS settings in backend (should allow all origins)
- Ensure both services are running

### Build fails
- Check build logs in Railway
- Verify Node version compatibility
- Ensure all dependencies are in package.json

### Upload fails
- Check Supabase storage bucket permissions
- Verify file size limits
- Check network timeouts

## Monitoring

### Backend Logs
```bash
railway logs -s hockey-analytics
```

### Frontend Logs
```bash
railway logs -s hockey-analytics-frontend
```

## Cost Optimization

- Frontend and backend together should use < 1GB RAM
- Enable auto-sleep for development environments
- Use Railway's usage-based pricing efficiently

## Next Steps

1. Set up custom domains
2. Configure SSL certificates (automatic with Railway)
3. Set up monitoring and alerts
4. Configure auto-scaling if needed

---

*Note: Railway provides $5 free credits monthly, which should cover development usage.*