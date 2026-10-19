from fastapi import FastAPI, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import Optional

from app.models import InstagramScrapeRequest, InstagramScrapeResponse
from app.scraper import scrape_instagram_profile
from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "FastAPI service that takes an Instagram profile link/handle as input "
        "and scrapes profile name, bio, captions for all posts, dates, locations, "
        "and post comments, returning everything in clean JSON format."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse, tags=["Web UI"])
def web_ui():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Instagram Profile & Posts Scraper</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    pre { max-height: 550px; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen">
  <div class="max-w-5xl mx-auto px-4 py-8">
    <!-- Header -->
    <header class="text-center mb-8">
      <div class="inline-flex items-center gap-3 px-4 py-2 rounded-full bg-slate-900 border border-slate-800 text-emerald-400 text-sm font-medium mb-3">
        <i class="fa-solid fa-robot text-lg text-emerald-400"></i> Session-Free Playwright Engine Active
      </div>
      <h1 class="text-3xl sm:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500 bg-clip-text text-transparent">
        Instagram Data Scraper
      </h1>
      <p class="text-slate-400 mt-2 text-sm sm:text-base">
        Extract real profile info, bio, posts, captions, timestamps, locations & comments into JSON &mdash; <strong>No Session ID Needed</strong>
      </p>
      <div class="mt-2 flex justify-center gap-4 text-xs text-slate-500">
        <a href="/docs" target="_blank" class="hover:text-pink-400 transition underline"><i class="fa-solid fa-book"></i> Interactive Docs (/docs)</a>
        <a href="/api/info" class="hover:text-pink-400 transition underline"><i class="fa-solid fa-code"></i> API Metadata (/api/info)</a>
        <a href="https://github.com/shreyash321/instagram-scraper-fastapi" target="_blank" class="hover:text-pink-400 transition underline"><i class="fa-brands fa-github"></i> GitHub Repo</a>
      </div>
    </header>

    <!-- Scraper Form Card -->
    <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-sm mb-6">
      <form id="scrapeForm" class="space-y-4">
        <div>
          <label class="block text-sm font-semibold text-slate-300 mb-1">
            Instagram Profile URL or Handle
          </label>
          <div class="relative">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
              <i class="fa-solid fa-link"></i>
            </div>
            <input
              type="text"
              id="profileUrl"
              required
              value="https://www.instagram.com/virat.kohli/"
              placeholder="e.g. https://www.instagram.com/virat.kohli/ or virat.kohli"
              class="w-full pl-10 pr-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-pink-500 text-sm transition"
            />
          </div>
        </div>

        <!-- Options Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1">Max Posts to Fetch</label>
            <input
              type="number"
              id="maxPosts"
              value="5"
              min="1"
              max="100"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:ring-2 focus:ring-pink-500 focus:outline-none"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1">Max Comments / Post</label>
            <input
              type="number"
              id="maxComments"
              value="3"
              min="0"
              max="50"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:ring-2 focus:ring-pink-500 focus:outline-none"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1">
              Instagram Session ID <span class="text-emerald-400 font-normal">(Optional)</span>
            </label>
            <input
              type="text"
              id="sessionId"
              placeholder="Optional - Playwright runs automatically"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:ring-2 focus:ring-pink-500 focus:outline-none"
            />
          </div>
        </div>

        <!-- Session ID Helper & Demo Toggle -->
        <div class="bg-slate-950/70 border border-slate-800/80 rounded-xl p-3 text-xs text-slate-400 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div class="flex items-center gap-2">
            <i class="fa-solid fa-circle-check text-emerald-400"></i>
            <span><strong>Session-Free Mode Active:</strong> Powered by Playwright headless browser engine. Real profile info, posts, captions, and comments are scraped live without requiring login cookies.</span>
          </div>
          <label class="flex items-center gap-2 text-slate-400 cursor-pointer flex-shrink-0">
            <input type="checkbox" id="demoFallback" class="rounded bg-slate-900 border-slate-700 text-pink-600 focus:ring-pink-500" />
            <span class="text-xs">Offline Demo Fallback Mode</span>
          </label>
        </div>

        <div class="pt-2 flex flex-wrap gap-3">
          <button
            type="submit"
            id="submitBtn"
            class="flex-1 bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-500 hover:to-purple-500 text-white font-medium py-3 px-6 rounded-xl shadow-lg shadow-pink-600/20 transition flex items-center justify-center gap-2 cursor-pointer"
          >
            <i class="fa-solid fa-bolt"></i>
            <span>Fetch Profile & Posts Data</span>
          </button>
          <button
            type="button"
            id="testBtn"
            class="px-4 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-xl text-sm transition"
          >
            Reset to @virat.kohli
          </button>
        </div>
      </form>
    </div>

    <!-- Status / Loading Indicator -->
    <div id="loader" class="hidden text-center py-12">
      <div class="inline-block animate-spin rounded-full h-10 w-10 border-4 border-pink-500 border-t-transparent"></div>
      <p class="mt-3 text-sm text-slate-400">Scraping Instagram profile, posts, captions, and comments...</p>
    </div>

    <!-- Error Banner -->
    <div id="errorBanner" class="hidden bg-red-950/60 border border-red-800 rounded-xl p-4 mb-6 text-red-300 text-sm">
      <div class="flex items-center gap-2 font-semibold">
        <i class="fa-solid fa-triangle-exclamation"></i>
        <span id="errorTitle">Scraping Failed</span>
      </div>
      <p id="errorMessage" class="mt-1 text-xs text-red-400"></p>
    </div>

    <!-- Auth Notice Banner -->
    <div id="authNoticeBanner" class="hidden bg-amber-950/50 border border-amber-700/60 rounded-xl p-4 mb-6 text-amber-200 text-sm">
      <div class="flex items-center gap-2 font-semibold text-amber-300">
        <i class="fa-solid fa-key"></i>
        <span>Instagram Session Cookie Required for Posts Timeline</span>
      </div>
      <p id="authNoticeMessage" class="mt-1 text-xs text-amber-300/80 leading-relaxed"></p>
      <div class="mt-3 bg-slate-950/80 p-3 rounded-lg border border-amber-900/50 text-xs text-slate-300">
        <strong class="text-amber-400">How to get your sessionid in 15 seconds:</strong>
        <ol class="list-decimal list-inside mt-1 space-y-1 text-slate-400">
          <li>Open <a href="https://www.instagram.com" target="_blank" class="text-pink-400 underline">instagram.com</a> in your browser and make sure you are logged in.</li>
          <li>Press <kbd class="px-1.5 py-0.5 bg-slate-800 border border-slate-700 rounded text-slate-200">F12</kbd> to open Developer Tools.</li>
          <li>Go to the <strong>Application</strong> tab (or <strong>Storage</strong> on Firefox) &rarr; expand <strong>Cookies</strong> &rarr; click <strong>https://www.instagram.com</strong>.</li>
          <li>Find the row named <code class="text-amber-400 font-mono font-bold">sessionid</code>, copy its value, and paste it into the <strong>Instagram Session ID</strong> field above!</li>
        </ol>
      </div>
    </div>

    <!-- Results Section -->
    <div id="resultsSection" class="hidden space-y-6">
      <!-- Profile Card -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-md">
        <div class="flex flex-col sm:flex-row items-center sm:items-start gap-5">
          <div class="w-20 h-20 rounded-full bg-gradient-to-tr from-yellow-500 via-pink-500 to-purple-600 p-0.5 flex-shrink-0">
            <div class="w-full h-full rounded-full bg-slate-950 flex items-center justify-center overflow-hidden">
              <i class="fa-solid fa-user text-3xl text-slate-500"></i>
            </div>
          </div>
          <div class="flex-1 text-center sm:text-left">
            <div class="flex flex-wrap items-center justify-center sm:justify-start gap-2">
              <h2 id="resFullName" class="text-xl font-bold text-white">Full Name</h2>
              <span id="resUsername" class="text-sm text-pink-400 font-mono">@username</span>
              <span id="resVerified" class="text-xs bg-blue-500/20 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded-full"><i class="fa-solid fa-circle-check"></i> Verified</span>
              <span id="resSourceBadge" class="text-xs bg-slate-800 text-slate-300 border border-slate-700 px-2 py-0.5 rounded-full">Source: live</span>
            </div>
            <p id="resBio" class="text-slate-300 text-sm mt-2 whitespace-pre-line"></p>
            <div class="mt-4 flex flex-wrap justify-center sm:justify-start gap-6 text-xs text-slate-400 border-t border-slate-800 pt-3">
              <div><strong id="resFollowers" class="text-white text-sm font-semibold">0</strong> Followers</div>
              <div><strong id="resFollowing" class="text-white text-sm font-semibold">0</strong> Following</div>
              <div><strong id="resPostsCount" class="text-white text-sm font-semibold">0</strong> Total Posts Published</div>
              <div><strong id="resScrapedCount" class="text-pink-400 text-sm font-semibold">0</strong> Posts Scraped</div>
            </div>
          </div>
        </div>
      </div>

      <!-- JSON Output Card -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-md">
        <div class="bg-slate-850 px-6 py-3 border-b border-slate-800 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <i class="fa-solid fa-code text-pink-400"></i>
            <span class="text-sm font-semibold text-slate-200">Scraped JSON Output</span>
          </div>
          <div class="flex gap-2">
            <button id="copyJsonBtn" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg transition flex items-center gap-1.5 cursor-pointer">
              <i class="fa-regular fa-copy"></i> Copy JSON
            </button>
            <button id="downloadJsonBtn" class="px-3 py-1.5 bg-pink-600/80 hover:bg-pink-600 text-white text-xs rounded-lg transition flex items-center gap-1.5 cursor-pointer">
              <i class="fa-solid fa-download"></i> Download .json
            </button>
          </div>
        </div>
        <div class="p-4 bg-slate-950 overflow-x-auto">
          <pre id="jsonOutput" class="text-xs text-green-400 font-mono overflow-y-auto"></pre>
        </div>
      </div>
    </div>
  </div>

  <script>
    let currentData = null;

    document.getElementById('testBtn').addEventListener('click', () => {
      document.getElementById('profileUrl').value = 'https://www.instagram.com/virat.kohli/';
      document.getElementById('maxPosts').value = '10';
      document.getElementById('maxComments').value = '5';
    });

    document.getElementById('scrapeForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const url = document.getElementById('profileUrl').value.trim();
      const maxPosts = parseInt(document.getElementById('maxPosts').value) || 10;
      const maxComments = parseInt(document.getElementById('maxComments').value) || 5;
      const sessionId = document.getElementById('sessionId').value.trim() || null;
      const demoFallback = document.getElementById('demoFallback').checked;

      const loader = document.getElementById('loader');
      const resultsSection = document.getElementById('resultsSection');
      const errorBanner = document.getElementById('errorBanner');
      const authNoticeBanner = document.getElementById('authNoticeBanner');
      const submitBtn = document.getElementById('submitBtn');

      loader.classList.remove('hidden');
      resultsSection.classList.add('hidden');
      errorBanner.classList.add('hidden');
      authNoticeBanner.classList.add('hidden');
      submitBtn.disabled = true;
      submitBtn.classList.add('opacity-50');

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 20000);

      try {
        const response = await fetch('/api/v1/scrape', {
          method: 'POST',
          signal: controller.signal,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url: url,
            max_posts: maxPosts,
            max_comments_per_post: maxComments,
            session_id: sessionId,
            fallback_sample_data: demoFallback
          })
        });

        clearTimeout(timeoutId);
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || 'Failed to fetch data');
        }

        currentData = data;
        renderResults(data);

        // Check if rate limited or authentication was required for posts
        if (data.status === 'rate_limited') {
          document.getElementById('authNoticeMessage').textContent = '⚠️ ' + data.message;
          authNoticeBanner.classList.remove('hidden');
        } else if (data.auth_required_for_posts && data.total_posts_scraped === 0) {
          document.getElementById('authNoticeMessage').textContent = data.message;
          authNoticeBanner.classList.remove('hidden');
        }
      } catch (err) {
        clearTimeout(timeoutId);
        document.getElementById('errorTitle').textContent = 'Error Scraping Profile';
        if (err.name === 'AbortError') {
          document.getElementById('errorMessage').textContent = 'Request timed out after 20 seconds. Instagram is responding slowly or throttling connections.';
        } else {
          document.getElementById('errorMessage').textContent = err.message;
        }
        errorBanner.classList.remove('hidden');
      } finally {
        loader.classList.add('hidden');
        submitBtn.disabled = false;
        submitBtn.classList.remove('opacity-50');
      }
    });

    function renderResults(data) {
      const p = data.profile || {};
      document.getElementById('resFullName').textContent = p.full_name || p.username || 'Unknown';
      document.getElementById('resUsername').textContent = '@' + (p.username || '');
      document.getElementById('resBio').textContent = p.biography || 'No bio available';
      document.getElementById('resFollowers').textContent = (p.followers || 0).toLocaleString();
      document.getElementById('resFollowing').textContent = (p.following || 0).toLocaleString();
      document.getElementById('resPostsCount').textContent = (p.posts_count || 0).toLocaleString();
      document.getElementById('resScrapedCount').textContent = data.total_posts_scraped || 0;
      document.getElementById('resSourceBadge').textContent = 'Source: ' + (data.source || 'live');

      const verifiedBadge = document.getElementById('resVerified');
      if (p.is_verified) {
        verifiedBadge.classList.remove('hidden');
      } else {
        verifiedBadge.classList.add('hidden');
      }

      document.getElementById('jsonOutput').textContent = JSON.stringify(data, null, 2);
      document.getElementById('resultsSection').classList.remove('hidden');
    }

    document.getElementById('copyJsonBtn').addEventListener('click', () => {
      if (!currentData) return;
      navigator.clipboard.writeText(JSON.stringify(currentData, null, 2)).then(() => {
        const btn = document.getElementById('copyJsonBtn');
        const orig = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-check text-green-400"></i> Copied!';
        setTimeout(() => { btn.innerHTML = orig; }, 2000);
      });
    });

    document.getElementById('downloadJsonBtn').addEventListener('click', () => {
      if (!currentData) return;
      const jsonStr = JSON.stringify(currentData, null, 2);
      const blob = new Blob([jsonStr], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      const username = (currentData.profile && currentData.profile.username) ? currentData.profile.username : 'instagram_data';
      a.href = url;
      a.download = `${username}_scraped_data.json`;
      a.click();
      URL.revokeObjectURL(url);
    });
  </script>
</body>
</html>
"""


@app.get("/api/info", tags=["General"])
def api_info():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs": "/docs",
        "endpoints": {
            "GET /": "Interactive Web UI for scraping",
            "POST /api/v1/scrape": "Scrapes profile & posts given a JSON request body with Instagram URL",
            "GET /api/v1/scrape": "Scrapes profile & posts via query parameters (?url=...)",
            "GET /api/v1/profile/{username}": "Direct scrape via username path parameter",
            "GET /health": "Health check endpoint"
        }
    }


@app.get("/health", tags=["General"])
def health_check():
    return {"status": "healthy"}


@app.post(
    "/api/v1/scrape",
    response_model=InstagramScrapeResponse,
    status_code=status.HTTP_200_OK,
    tags=["Scraper"],
    summary="Scrape Instagram profile by URL (JSON Body)"
)
def scrape_profile_post(request: InstagramScrapeRequest):
    """
    Scrapes an Instagram profile using a JSON request body:
    - **url**: Full profile link (e.g. `https://www.instagram.com/virat.kohli/`) or handle
    - **max_posts**: Maximum number of posts to scrape (e.g., 10, 50, 100)
    - **max_comments_per_post**: Maximum comments to fetch per post
    - **session_id**: Optional Instagram sessionid cookie value
    - **fallback_sample_data**: If True, generates demo sample posts matching requested count
    """
    try:
        response = scrape_instagram_profile(
            url_or_handle=request.url,
            max_posts=request.max_posts,
            max_comments_per_post=request.max_comments_per_post,
            session_id=request.session_id,
            fallback_sample_data=request.fallback_sample_data
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while scraping: {str(e)}"
        )


@app.get(
    "/api/v1/scrape",
    response_model=InstagramScrapeResponse,
    status_code=status.HTTP_200_OK,
    tags=["Scraper"],
    summary="Scrape Instagram profile by URL (Query Params)"
)
def scrape_profile_get(
    url: str = Query(..., description="Instagram profile URL (e.g. https://www.instagram.com/virat.kohli/)"),
    max_posts: Optional[int] = Query(10, description="Max posts to scrape"),
    max_comments: Optional[int] = Query(5, description="Max comments per post"),
    session_id: Optional[str] = Query(None, description="Optional sessionid cookie"),
    fallback_sample_data: bool = Query(False, description="Offline demo mock posts")
):
    """
    Convenient GET endpoint for quick browser or webhook testing.
    """
    return scrape_instagram_profile(
        url_or_handle=url,
        max_posts=max_posts,
        max_comments_per_post=max_comments,
        session_id=session_id,
        fallback_sample_data=fallback_sample_data
    )


@app.get(
    "/api/v1/profile/{username}",
    response_model=InstagramScrapeResponse,
    status_code=status.HTTP_200_OK,
    tags=["Scraper"],
    summary="Scrape Instagram profile by username"
)
def scrape_by_username(
    username: str,
    max_posts: Optional[int] = Query(10, description="Max posts to scrape"),
    max_comments: Optional[int] = Query(5, description="Max comments per post"),
    session_id: Optional[str] = Query(None, description="Optional sessionid cookie"),
    fallback_sample_data: bool = Query(False, description="Offline demo mock posts")
):
    """
    Convenient endpoint to fetch directly by username handle (e.g. /api/v1/profile/virat.kohli).
    """
    return scrape_instagram_profile(
        url_or_handle=username,
        max_posts=max_posts,
        max_comments_per_post=max_comments,
        session_id=session_id,
        fallback_sample_data=fallback_sample_data
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)
