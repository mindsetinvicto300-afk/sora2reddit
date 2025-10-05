# Deploy Sora2 Radar to Render (Hobby Plan)

## 🚀 Quick Deployment Guide

### Prerequisites
- GitHub account
- Render account ([Sign up here](https://dashboard.render.com/register))
- Your code pushed to GitHub

---

## Step-by-Step Deployment

### 1️⃣ Push Code to GitHub

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Sora2 Radar ready for deployment"

# Create repository on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/sora2-radar.git
git branch -M main
git push -u origin main
```

### 2️⃣ Deploy on Render

1. **Go to Render Dashboard**
   - Visit: https://dashboard.render.com/select-plan?plan=hobby
   - Or go to: https://dashboard.render.com/

2. **Create New Web Service**
   - Click **"New +"** → **"Web Service"**
   - Or use direct link: https://dashboard.render.com/create?type=web

3. **Connect GitHub Repository**
   - Click **"Connect GitHub"** (if not already connected)
   - Authorize Render to access your repositories
   - Select your `sora2-radar` repository
   - Click **"Connect"**

4. **Configure Your Service**

   Fill in these settings:

   | Setting | Value |
   |---------|-------|
   | **Name** | `sora2-radar` (or your choice) |
   | **Region** | Choose closest to your users |
   | **Branch** | `main` |
   | **Runtime** | `Python 3` (auto-detected) |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `uvicorn backend.app:app --host 0.0.0.0 --port $PORT` |
   | **Plan** | **Hobby** ($7/month) |

5. **Environment Variables** (Optional)

   Click **"Advanced"** → **"Add Environment Variable"**

   Add these if needed:
   ```
   THREAD_URL = https://www.reddit.com/r/OpenAI/comments/1nukmm2/open_ai_sora_2_invite_codes_megathread/
   FETCH_INTERVAL_SECONDS = 5
   ```

6. **Deploy**
   - Click **"Create Web Service"**
   - Render will start building and deploying
   - Wait 2-5 minutes for deployment to complete

### 3️⃣ Access Your App

Once deployed, your app will be available at:
```
https://sora2-radar.onrender.com
```
(Replace with your actual service name)

---

## ⚙️ Configuration Options

### Auto-Deploy from GitHub
✅ **Enabled by default** - Every push to `main` branch auto-deploys

To disable:
- Go to service settings
- Turn off "Auto-Deploy"

### Custom Domain (Optional)
1. Go to service **Settings** → **Custom Domains**
2. Click **"Add Custom Domain"**
3. Enter your domain (e.g., `sora2radar.com`)
4. Follow DNS configuration instructions
5. Wait for SSL certificate (automatic)

### Health Checks
Render automatically checks: `https://your-app.onrender.com/`

If you want custom health check endpoint, modify in `render.yaml`:
```yaml
healthCheckPath: /health
```

### Logs
View real-time logs:
- Dashboard → Your Service → **Logs** tab
- Or use Render CLI

---

## 💰 Hobby Plan Details

**Price**: $7/month

**Includes**:
- ✅ 512 MB RAM
- ✅ Shared CPU
- ✅ Always-on (no sleep)
- ✅ Auto-deploy from Git
- ✅ Free SSL certificate
- ✅ Custom domains
- ✅ 100 GB bandwidth/month

**Perfect for:**
- Production apps
- Apps that need 24/7 uptime
- Apps with moderate traffic

---

## 🆓 Alternative: Free Plan

If you want to start with **Free**:

**Limitations**:
- ⚠️ Spins down after 15 min of inactivity
- ⚠️ Slower startup (cold starts)
- ⚠️ 512 MB RAM
- ⚠️ 100 GB bandwidth/month

To use Free plan:
1. Select **"Free"** instead of "Hobby" during setup
2. Everything else is the same

---

## 🔧 Troubleshooting

### Build Fails
**Issue**: Deployment fails during build

**Solution**:
```bash
# Locally test that requirements install
pip install -r requirements.txt

# Make sure all dependencies are listed
pip freeze > requirements.txt
```

### App Not Starting
**Issue**: Service shows "Deploy failed" or keeps restarting

**Solutions**:
1. Check logs in Render Dashboard
2. Verify start command is correct
3. Test locally:
   ```bash
   uvicorn backend.app:app --host 0.0.0.0 --port 8000
   ```

### Static Files Not Loading
**Issue**: CSS/JS files return 404

**Solution**: Verify your FastAPI app mounts static files:
```python
app.mount("/static", StaticFiles(directory="static"), name="static")
```

### Reddit API Issues
**Issue**: Codes not updating

**Solutions**:
1. Check `THREAD_URL` environment variable
2. Verify Reddit thread is still active
3. Check rate limiting

---

## 📊 Monitoring

### View Metrics
Dashboard → Service → **Metrics** tab

Shows:
- CPU usage
- Memory usage
- Request count
- Response times

### Set Up Alerts
1. Go to **Settings** → **Alerts**
2. Add email for notifications
3. Configure alert thresholds

---

## 🔄 Updates & Redeployment

### Automatic Updates
Push to GitHub `main` branch:
```bash
git add .
git commit -m "Update features"
git push
```
Render auto-deploys in ~2-5 minutes

### Manual Deploy
Dashboard → Service → **Manual Deploy** → Select branch

### Rollback
Dashboard → Service → **Events** → Click previous deploy → **Rollback**

---

## 🌐 Update SEO After Deployment

1. **Get Your URL**
   - Copy from Render Dashboard
   - Example: `https://sora2-radar.onrender.com`

2. **Update HTML Files**
   - Replace `your-domain.com` with actual URL
   - Update in:
     - `index.html` (meta tags)
     - `sitemap.xml`
     - `robots.txt`

3. **Submit to Google**
   - [Google Search Console](https://search.google.com/search-console/)
   - Add your property
   - Submit sitemap: `https://your-app.onrender.com/sitemap.xml`

---

## 🎯 Post-Deployment Checklist

- [ ] App is accessible at Render URL
- [ ] All features working (code scanning, sharing, etc.)
- [ ] Static files loading (CSS, JS)
- [ ] Reddit integration working
- [ ] Sound alerts functioning
- [ ] Update SEO meta tags with real URL
- [ ] Submit to Google Search Console
- [ ] Set up custom domain (optional)
- [ ] Share on social media
- [ ] Monitor logs for errors

---

## 💡 Tips for Success

1. **Monitor First 24 Hours**
   - Watch logs for errors
   - Test all features
   - Check Reddit API calls

2. **Optimize Costs**
   - Free plan for testing
   - Hobby plan for production
   - Monitor bandwidth usage

3. **Improve Performance**
   - Enable caching
   - Optimize images
   - Minify CSS/JS

4. **Scale Later**
   - Upgrade to Standard plan if needed
   - Add Redis for caching
   - Use CDN for static files

---

## 📞 Need Help?

- **Render Docs**: https://render.com/docs
- **Render Support**: support@render.com
- **Community**: https://community.render.com/

---

## 🎉 Success!

Your Sora2 Radar is now live! 🚀

Share it with the world:
- Reddit: r/OpenAI
- Twitter: #Sora2 #OpenAI
- Product Hunt
- Hacker News

Good luck! 💪
