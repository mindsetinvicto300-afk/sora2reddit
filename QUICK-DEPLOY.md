# 🚀 Quick Deploy Guide - Sora2 Radar

## Your GitHub Repository
```
git@github.com:nuSapb/sora2-invite-code.git
```

---

## Step 1: Push Code to GitHub (2 minutes)

Open your terminal in the project directory and run:

```bash
# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Sora2 Radar ready for deployment"

# Add your GitHub repository
git remote add origin git@github.com:nuSapb/sora2-invite-code.git

# Push to GitHub
git branch -M main
git push -u origin main
```

If you get an SSH key error, use HTTPS instead:
```bash
git remote remove origin
git remote add origin https://github.com/nuSapb/sora2-invite-code.git
git push -u origin main
```

---

## Step 2: Deploy on Render (3 minutes)

### Option A: One-Click Deploy (Easiest)

1. **Go to Render Dashboard**
   - Visit: https://dashboard.render.com/

2. **Click "New +"** → **"Web Service"**

3. **Connect GitHub Repository**
   - Click "Connect GitHub"
   - Search for: `nuSapb/sora2-invite-code`
   - Click "Connect"

4. **Render Auto-Detects Settings**

   Verify these are correct:
   ```
   Name: sora2-invite-code
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn backend.app:app --host 0.0.0.0 --port $PORT
   ```

5. **Select Plan**
   - Choose **"Hobby"** ($7/month) for always-on
   - Or **"Free"** (sleeps after 15 min inactivity)

6. **Click "Create Web Service"**

---

### Option B: Deploy with Blueprint (Advanced)

Render will auto-detect `render.yaml` and configure everything automatically!

Just click "Apply" when prompted.

---

## Step 3: Wait for Deployment ⏳

Render will:
1. ✅ Clone your repository
2. ✅ Install Python dependencies
3. ✅ Start FastAPI app
4. ✅ Provide HTTPS URL

**Deployment time:** 2-5 minutes

---

## Step 4: Your App is Live! 🎉

Your app will be available at:
```
https://sora2-invite-code.onrender.com
```

Or whatever name you chose!

---

## 🔧 Post-Deployment Tasks

### 1. Update SEO URLs

After deployment, update these files with your real URL:

**In `static/index.html`:** (lines 15, 19, 22, 27, 29, 45, 60)
- Replace: `https://your-domain.com/`
- With: `https://sora2-invite-code.onrender.com/`

**In `static/sitemap.xml`:**
- Replace: `https://your-domain.com/`
- With: `https://sora2-invite-code.onrender.com/`

**In `static/robots.txt`:**
- Replace: `https://your-domain.com/sitemap.xml`
- With: `https://sora2-invite-code.onrender.com/sitemap.xml`

Then push updates:
```bash
git add .
git commit -m "Update URLs after deployment"
git push
```

Render will auto-deploy in ~2 minutes!

### 2. Test Your App

Visit your URL and test:
- ✅ Code scanning works
- ✅ Sound alerts work
- ✅ Manual scan button works
- ✅ Share codes feature works
- ✅ All styles loading correctly

### 3. Submit to Google

**Google Search Console:**
1. Go to: https://search.google.com/search-console/
2. Add property: `https://sora2-invite-code.onrender.com`
3. Verify ownership (HTML tag method)
4. Submit sitemap: `https://sora2-invite-code.onrender.com/sitemap.xml`
5. Request indexing

**Bing Webmaster:**
1. Go to: https://www.bing.com/webmasters/
2. Add site and verify
3. Submit sitemap

### 4. Share Your App 📣

Share on:
- **Reddit**: r/OpenAI, r/SideProject
- **Twitter/X**: Use hashtags #Sora2 #OpenAI #InviteCodes
- **Product Hunt**: Launch your product
- **Hacker News**: Share in Show HN

---

## 🎯 Quick Commands Reference

### View Logs
```bash
# In Render Dashboard
Dashboard → Your Service → Logs
```

### Redeploy
```bash
# Push to GitHub
git push

# Or manual deploy in Render Dashboard
Dashboard → Your Service → Manual Deploy
```

### Add Environment Variables
```bash
# In Render Dashboard
Dashboard → Your Service → Environment → Add Environment Variable
```

Common variables:
```
# Multiple Reddit sources (comma-separated)
THREAD_URLS=https://www.reddit.com/r/OpenAI/comments/1nukmm2/open_ai_sora_2_invite_codes_megathread/,https://www.reddit.com/r/OpenAI/search.json?q=sora+invite+code&restrict_sr=1&sort=new&t=week,https://www.reddit.com/r/sora/search.json?q=invite+code&restrict_sr=1&sort=new&t=week

# Twitter/X sources (optional, requires SCRAPE_DO_TOKEN)
TWITTER_SEARCH_URLS=https://x.com/search?q=sora+invite+code&f=live

# ScraperAPI token for bypassing restrictions (optional)
SCRAPE_DO_TOKEN=your_scraperapi_token_here

# Scan interval
FETCH_INTERVAL_SECONDS=5

# Maximum codes to store
MAX_CODES=200
```

---

## 🆘 Troubleshooting

### Issue: Build Failed
**Solution:**
```bash
# Test locally first
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

### Issue: App Not Starting
**Solution:**
- Check logs in Render Dashboard
- Verify start command is correct
- Make sure port uses `$PORT` variable

### Issue: Static Files 404
**Solution:**
- Verify `static` folder is in your repo
- Check FastAPI static files mount
- Clear browser cache

### Issue: Can't Push to GitHub
**Solution:**
```bash
# Use HTTPS instead of SSH
git remote set-url origin https://github.com/nuSapb/sora2-invite-code.git
git push -u origin main
```

---

## 💡 Pro Tips

1. **Auto-Deploy**: Every push to `main` auto-deploys
2. **Branch Deploys**: Create `develop` branch for testing
3. **Custom Domain**: Add in Render → Settings → Custom Domains
4. **Monitoring**: Enable alerts in Render → Settings → Alerts
5. **Performance**: Check metrics in Render → Metrics tab

---

## 📊 Expected Performance

**Hobby Plan:**
- ⚡ Always-on (no cold starts)
- 🚀 Fast response times
- 💪 Handles moderate traffic
- 🔒 Free SSL certificate

**Free Plan:**
- ⏱️ 30-60s cold start after 15 min idle
- 💰 $0/month
- ⚠️ Good for testing only

---

## 🎉 Success Checklist

- [ ] Code pushed to GitHub
- [ ] Render service created
- [ ] Deployment completed successfully
- [ ] App accessible via Render URL
- [ ] All features working
- [ ] URLs updated with real domain
- [ ] Submitted to Google Search Console
- [ ] Shared on social media

---

## 🚀 Your App URLs

**Live App:**
```
https://sora2-invite-code.onrender.com
```

**GitHub Repo:**
```
https://github.com/nuSapb/sora2-invite-code
```

**Render Dashboard:**
```
https://dashboard.render.com/
```

---

## 📞 Support

- **Render Docs**: https://render.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **GitHub Issues**: https://github.com/nuSapb/sora2-invite-code/issues

---

Good luck with your deployment! 🚀🎉
