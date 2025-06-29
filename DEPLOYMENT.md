# 🚀 Deployment Guide - Audio Comic Reader

## Deploy to Railway (Recommended)

Railway is the easiest platform to deploy your Audio Comic Reader application.

### Prerequisites
- GitHub account
- Railway account (free at railway.app)
- Your API keys (OpenAI, Murf AI)

### Step-by-Step Deployment

#### 1. **Push Your Code to GitHub**
```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

#### 2. **Deploy on Railway**
1. Go to [railway.app](https://railway.app)
2. Sign up/Login with GitHub
3. Click "Start a New Project"
4. Select "Deploy from GitHub repo"
5. Choose your `audio-comic-reader` repository
6. Click "Deploy Now"

#### 3. **Set Environment Variables**
In Railway dashboard, go to your project → Variables tab and add:

```
OPENAI_API_KEY=your_openai_api_key_here
MURF_API_KEY=your_murf_api_key_here
PORT=8000
DEBUG=false
MAX_FILE_SIZE_MB=50
```

#### 4. **Add Custom Domain (Optional)**
1. In Railway dashboard, go to Settings
2. Click "Generate Domain" for a free railway.app subdomain
3. Or add your custom domain

#### 5. **Monitor Deployment**
- Check the "Deployments" tab for build logs
- Your app will be live at the generated URL

### 🎉 Your App is Live!
Once deployed, your Audio Comic Reader will be accessible worldwide at your Railway URL.

## Alternative Platforms

### Render.com
- Similar to Railway
- Good free tier
- Easy GitHub integration

### Vercel
- Excellent for frontend
- Supports Python/FastAPI
- Great performance

### Heroku
- Classic platform
- More expensive now
- Good documentation

## Troubleshooting

### Common Issues:
1. **Build fails**: Check requirements.txt has all dependencies
2. **API keys not working**: Verify environment variables are set
3. **File upload issues**: Check file size limits and storage

### Support:
- Check Railway logs in dashboard
- Review deployment guide
- Contact support if needed

## Production Considerations

1. **File Storage**: Consider using cloud storage (AWS S3, Cloudinary) for uploaded files
2. **Database**: Add a proper database for session management
3. **Caching**: Implement Redis for better performance
4. **Monitoring**: Add application monitoring (Sentry, LogRocket)
5. **CDN**: Use a CDN for static assets 