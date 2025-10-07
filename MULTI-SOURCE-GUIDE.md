# 🔄 Multi-Source Scanning Guide

Your Sora2 Radar now supports **multiple sources** for finding invite codes!

## ✨ What's New

Instead of relying on a single Reddit thread (which can get blocked or deleted), the app now scans:

1. **Multiple Reddit threads** - Original megathread + search results
2. **Reddit search queries** - Real-time searches across subreddits
3. **Twitter/X posts** - Live search results (optional, requires API token)

---

## 🎯 Default Sources (No Setup Required)

By default, the app scans these 3 Reddit sources:

1. **Original Megathread**
   ```
   https://www.reddit.com/r/OpenAI/comments/1nukmm2/open_ai_sora_2_invite_codes_megathread/
   ```

2. **r/OpenAI Search** (last week)
   ```
   https://www.reddit.com/r/OpenAI/search.json?q=sora+invite+code&restrict_sr=1&sort=new&t=week
   ```

3. **r/sora Search** (last week)
   ```
   https://www.reddit.com/r/sora/search.json?q=invite+code&restrict_sr=1&sort=new&t=week
   ```

---

## 🚀 Quick Start

### Option 1: Use Defaults (Recommended)

No configuration needed! Just deploy as normal. The app will automatically scan all 3 Reddit sources.

### Option 2: Add More Sources

Set the `THREAD_URLS` environment variable with comma-separated URLs:

```bash
THREAD_URLS=https://www.reddit.com/r/OpenAI/comments/abc/,https://www.reddit.com/r/sora/search.json?q=code
```

### Option 3: Add Twitter/X Sources

1. Get a ScraperAPI token (free tier available): https://www.scraperapi.com/
2. Set environment variables:
   ```bash
   SCRAPE_DO_TOKEN=your_token_here
   TWITTER_SEARCH_URLS=https://x.com/search?q=sora+invite+code&f=live
   ```

---

## 📝 Configuration Examples

### Example 1: Reddit Only (Multiple Threads)

```bash
THREAD_URLS=https://www.reddit.com/r/OpenAI/comments/thread1/,https://www.reddit.com/r/OpenAI/comments/thread2/,https://www.reddit.com/r/sora/comments/thread3/
```

### Example 2: Reddit Searches

```bash
THREAD_URLS=https://www.reddit.com/r/OpenAI/search.json?q=sora+code&restrict_sr=1&sort=new&t=day,https://www.reddit.com/r/singularity/search.json?q=sora+invite&restrict_sr=1&sort=new&t=week
```

### Example 3: Reddit + Twitter

```bash
THREAD_URLS=https://www.reddit.com/r/OpenAI/search.json?q=sora+invite
TWITTER_SEARCH_URLS=https://x.com/search?q=sora+invite+code&f=live,https://x.com/search?q=openai+sora+code&f=live
SCRAPE_DO_TOKEN=abc123xyz
```

---

## 🔍 Finding More Sources

### Reddit Sources

**Option A: Specific Threads**
1. Find any Reddit thread with invite codes
2. Copy the URL
3. Add to `THREAD_URLS`

**Option B: Search Queries**
1. Go to Reddit and search for "sora invite code"
2. Add `.json` to the URL
3. Example: `https://www.reddit.com/r/OpenAI/search.json?q=sora+invite+code&restrict_sr=1&sort=new&t=week`

**Popular Subreddits to Search:**
- r/OpenAI
- r/sora
- r/singularity
- r/ArtificialIntelligence
- r/MachineLearning

### Twitter/X Sources

**Search URLs Format:**
```
https://x.com/search?q=YOUR_SEARCH&f=live
```

**Good Search Terms:**
- `sora invite code`
- `openai sora code`
- `sora 2 invite`
- `sora access code`

**Note:** Twitter requires `SCRAPE_DO_TOKEN` to work.

---

## ⚙️ How It Works

### Scanning Process

1. **Every 5 seconds** (configurable with `FETCH_INTERVAL_SECONDS`)
2. The app scans **all configured sources** in parallel
3. Extracts **6-character codes** (letters + numbers)
4. Filters out **common words** (blacklist)
5. Stores **unique codes** with metadata (author, timestamp, permalink)
6. Keeps **newest 200 codes** (configurable with `MAX_CODES`)

### Error Handling

- If one source fails, others continue working
- Automatic retry with exponential backoff for 403/429 errors
- Logs warnings but doesn't crash the app
- Uses CORS proxy as fallback for blocked IPs

---

## 🛠️ Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `THREAD_URLS` | Comma-separated Reddit URLs | 3 Reddit sources | No |
| `TWITTER_SEARCH_URLS` | Comma-separated Twitter URLs | Empty | No |
| `SCRAPE_DO_TOKEN` | ScraperAPI token | None | Only for Twitter |
| `FETCH_INTERVAL_SECONDS` | Scan frequency (seconds) | 5 | No |
| `MAX_CODES` | Max codes to store | 200 | No |
| `CORS_ALLOW_ORIGINS` | CORS allowed origins | * | No |

---

## 📊 Monitoring Sources

### Check Logs

In your deployment logs, you'll see:

```
INFO: Scanning Reddit source: https://www.reddit.com/r/OpenAI/...
INFO: Scanning Reddit source: https://www.reddit.com/r/sora/...
INFO: Scan complete. Found 5 new codes from 3 sources
```

### Health Check Endpoint

```bash
curl https://your-app.onrender.com/api/health
```

Returns:
```json
{
  "status": "ok",
  "codes_cached": 42,
  "last_fetch": 1234567890.123,
  "interval_seconds": 5
}
```

---

## 🚨 Troubleshooting

### No New Codes Found

**Possible causes:**
1. All sources are blocked/rate-limited
2. No new codes posted recently
3. Invalid source URLs

**Solutions:**
1. Add `SCRAPE_DO_TOKEN` to bypass IP blocks
2. Check source URLs are valid
3. Add more sources
4. Verify sources in browser first

### One Source Failing

**Check logs for:**
```
WARNING: Failed to scan Reddit source https://...: 403 Forbidden
```

**Solutions:**
1. That source might be blocking your IP
2. Other sources continue working
3. Add `SCRAPE_DO_TOKEN` or remove the failing source

### Twitter Not Working

**Requirements:**
1. Must set `SCRAPE_DO_TOKEN`
2. Must set `TWITTER_SEARCH_URLS`
3. Both are required for Twitter

---

## 💡 Best Practices

### Source Selection

1. **Mix thread types:**
   - Static threads (megathreads)
   - Search queries (real-time results)
   - Multiple subreddits

2. **Avoid duplicates:**
   - The app handles duplicates, but it's more efficient to avoid them

3. **Monitor performance:**
   - More sources = more API calls
   - Start with 3-5 sources
   - Add more if needed

### Rate Limiting

1. **Default interval: 5 seconds**
   - Scans all sources every 5 seconds
   - Add random jitter to avoid pattern detection

2. **Increase interval if rate-limited:**
   ```bash
   FETCH_INTERVAL_SECONDS=10
   ```

3. **Use ScraperAPI for high-frequency scanning:**
   - Free tier: 1,000 requests/month
   - Paid tier: More requests + better success rate

---

## 🎯 Recommended Setup

### For Production

```bash
# Multiple Reddit sources for redundancy
THREAD_URLS=https://www.reddit.com/r/OpenAI/comments/1nukmm2/megathread/,https://www.reddit.com/r/OpenAI/search.json?q=sora+invite+code&restrict_sr=1&sort=new&t=week,https://www.reddit.com/r/sora/search.json?q=invite+code&restrict_sr=1&sort=new&t=week

# ScraperAPI for bypassing blocks
SCRAPE_DO_TOKEN=your_token_here

# Moderate scan frequency
FETCH_INTERVAL_SECONDS=5

# Large cache
MAX_CODES=200
```

### For Development/Testing

```bash
# Single source for testing
THREAD_URLS=https://www.reddit.com/r/OpenAI/search.json?q=sora

# Slower scanning
FETCH_INTERVAL_SECONDS=10

# Smaller cache
MAX_CODES=50
```

---

## 🔄 Migration from Single Source

### Old Configuration (Deprecated)

```bash
THREAD_URL=https://www.reddit.com/r/OpenAI/comments/1nukmm2/megathread/
```

### New Configuration (Current)

```bash
THREAD_URLS=https://www.reddit.com/r/OpenAI/comments/1nukmm2/megathread/,https://www.reddit.com/r/OpenAI/search.json?q=sora+invite
```

**Note:** The old `THREAD_URL` variable is no longer used. Use `THREAD_URLS` (plural).

---

## 📈 Performance Impact

### With 3 sources (default):
- ✅ Minimal impact
- ✅ Scans complete in ~2-5 seconds
- ✅ No noticeable slowdown

### With 5+ sources:
- ⚠️ Longer scan times
- ⚠️ More API calls
- ✅ Still works fine
- 💡 Consider increasing `FETCH_INTERVAL_SECONDS`

### With 10+ sources:
- ⚠️ May hit rate limits
- ⚠️ Requires `SCRAPE_DO_TOKEN`
- 💡 Increase `FETCH_INTERVAL_SECONDS` to 10+

---

## 🎉 Success!

Your app now scans multiple sources automatically!

**Next steps:**
1. Deploy with default settings (works out of the box)
2. Monitor logs to see sources being scanned
3. Add more sources as needed
4. Get ScraperAPI token for better reliability (optional)

**Questions?**
- Check logs for detailed scan information
- Use `/api/health` endpoint to verify status
- Test sources in browser before adding them

---

**Happy scanning! 🚀**
