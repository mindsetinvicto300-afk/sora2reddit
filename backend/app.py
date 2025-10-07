from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List
from urllib.parse import quote_plus

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .blacklist import DEFAULT_BLACKLIST
from .models import CodeEntry, CodesResponse


logger = logging.getLogger("sora2_scanner")
logging.basicConfig(level=logging.INFO)

ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"

# Support multiple sources - can be comma-separated URLs
THREAD_URLS = os.getenv(
    "THREAD_URLS",
    "https://www.reddit.com/r/OpenAI/comments/1nukmm2/open_ai_sora_2_invite_codes_megathread,"
    "https://www.reddit.com/r/OpenAI/search.json?q=sora+invite+code&restrict_sr=1&sort=new&t=week,"
    "https://www.reddit.com/r/sora/search.json?q=invite+code&restrict_sr=1&sort=new&t=week"
).split(",")
TWITTER_SEARCH_URLS = os.getenv(
    "TWITTER_SEARCH_URLS",
    ""  # Twitter requires auth, so disabled by default
).split(",") if os.getenv("TWITTER_SEARCH_URLS") else []
FETCH_INTERVAL_SECONDS = float(os.getenv("FETCH_INTERVAL_SECONDS", "5"))
SCRAPE_DO_TOKEN = os.getenv("SCRAPE_DO_TOKEN")
MAX_CODES = int(os.getenv("MAX_CODES", "200"))

CODE_PATTERN = re.compile(r"\b[0-9A-Za-z]{6}\b")
BLACKLIST = {word.upper() for word in DEFAULT_BLACKLIST}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

app = FastAPI(title="Sora2 Invite Code Scanner", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_results_lock = asyncio.Lock()
_codes: Dict[str, CodeEntry] = {}
_ordered_codes: List[CodeEntry] = []
_last_fetch: float = 0.0
_scanner_task: asyncio.Task | None = None


def ensure_json_url(url: str) -> str:
    if url.endswith(".json"):
        return url
    return f"{url}.json"


def is_valid_candidate(candidate: str) -> bool:
    candidate = candidate.upper()
    if candidate in BLACKLIST:
        return False
    letters = sum(ch.isalpha() for ch in candidate)
    digits = sum(ch.isdigit() for ch in candidate)
    if letters < 2 or digits < 2:
        return False
    return True


async def fetch_thread_json(client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
    url = ensure_json_url(url)

    # Try old.reddit.com first (less restrictive)
    if "www.reddit.com" in url:
        url = url.replace("www.reddit.com", "old.reddit.com")

    # Try multiple proxy methods in order of preference
    proxy_methods = []

    if SCRAPE_DO_TOKEN:
        # Try ScraperAPI first if token is provided
        proxy_methods.append(("ScraperAPI", f"http://api.scraperapi.com?api_key={SCRAPE_DO_TOKEN}&url={quote_plus(url)}"))

    # Always have CORS proxy as fallback
    proxy_methods.extend([
        ("AllOrigins", f"https://api.allorigins.win/raw?url={quote_plus(url)}"),
        ("Direct", url),  # Try direct access as last resort
    ])

    last_error = None
    for proxy_name, target_url in proxy_methods:
        try:
            logger.info(f"Trying {proxy_name} proxy for {url[:80]}...")
            response = await client.get(target_url, timeout=20)
            response.raise_for_status()

            # Parse JSON response (use .text to handle encoding properly)
            payload = json.loads(response.text)

            if isinstance(payload, list) and payload:
                logger.info(f"✓ {proxy_name} proxy succeeded")
                return payload[1] if len(payload) > 1 else payload[0]
            if isinstance(payload, dict):
                logger.info(f"✓ {proxy_name} proxy succeeded")
                return payload
            logger.warning(f"{proxy_name} returned unexpected structure, trying next proxy...")
            continue
        except httpx.HTTPStatusError as e:
            logger.warning(f"{proxy_name} failed with {e.response.status_code}, trying next proxy...")
            last_error = e
            continue
        except Exception as e:
            logger.warning(f"{proxy_name} failed with {type(e).__name__}: {e}, trying next proxy...")
            last_error = e
            continue

    # All proxy methods failed
    if last_error:
        raise last_error
    raise HTTPException(status_code=502, detail="All proxy methods failed")


def iter_comments(children: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for child in children:
        data = child.get("data") or {}
        yield data
        replies = data.get("replies")
        if isinstance(replies, dict):
            yield from iter_comments(replies.get("data", {}).get("children", []))


def extract_codes_from_body(body: str) -> List[str]:
    matches = []
    for candidate in CODE_PATTERN.findall(body.upper()):
        if not is_valid_candidate(candidate):
            continue
        matches.append(candidate)
    return matches


async def scan_reddit_source(client: httpx.AsyncClient, url: str, now: float) -> List[CodeEntry]:
    """Scan a single Reddit source for codes."""
    new_codes: list[CodeEntry] = []

    try:
        payload = await fetch_thread_json(client, url)
        listing = payload.get("data", {}).get("children", [])

        for comment in iter_comments(listing):
            body = comment.get("body")
            if not body:
                continue
            codes = extract_codes_from_body(body)
            if not codes:
                continue

            created_utc = float(comment.get("created_utc") or now)
            permalink = comment.get("permalink")
            if permalink and permalink.startswith("/"):
                permalink = f"https://www.reddit.com{permalink}"

            for code in codes:
                if code in _codes:
                    continue
                entry = CodeEntry(
                    code=code,
                    comment_id=comment.get("id", ""),
                    author=comment.get("author"),
                    permalink=permalink or "",
                    created_utc=created_utc,
                    first_seen=now,
                )
                _codes[code] = entry
                new_codes.append(entry)
    except Exception as exc:
        logger.warning(f"Failed to scan Reddit source {url}: {exc}")

    return new_codes


async def scan_twitter_source(client: httpx.AsyncClient, url: str, now: float) -> List[CodeEntry]:
    """Scan Twitter/X for codes (requires ScraperAPI or similar)."""
    new_codes: list[CodeEntry] = []

    if not SCRAPE_DO_TOKEN:
        logger.warning("Twitter scanning requires SCRAPE_DO_TOKEN")
        return new_codes

    try:
        # Twitter requires more sophisticated scraping
        target_url = f"http://api.scraperapi.com?api_key={SCRAPE_DO_TOKEN}&url={quote_plus(url)}"
        response = await client.get(target_url)
        response.raise_for_status()

        # Extract codes from Twitter HTML/JSON
        text = response.text
        codes = extract_codes_from_body(text)

        for code in codes:
            if code in _codes:
                continue
            entry = CodeEntry(
                code=code,
                comment_id="",
                author="twitter",
                permalink=url,
                created_utc=now,
                first_seen=now,
            )
            _codes[code] = entry
            new_codes.append(entry)
    except Exception as exc:
        logger.warning(f"Failed to scan Twitter source {url}: {exc}")

    return new_codes


async def scan_once() -> List[CodeEntry]:
    global _last_fetch
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    new_codes: list[CodeEntry] = []
    now = time.time()

    async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
        # Scan all Reddit sources
        for thread_url in THREAD_URLS:
            thread_url = thread_url.strip()
            if not thread_url:
                continue
            logger.info(f"Scanning Reddit source: {thread_url}")
            codes = await scan_reddit_source(client, thread_url, now)
            new_codes.extend(codes)

        # Scan Twitter sources if configured
        for twitter_url in TWITTER_SEARCH_URLS:
            twitter_url = twitter_url.strip()
            if not twitter_url:
                continue
            logger.info(f"Scanning Twitter source: {twitter_url}")
            codes = await scan_twitter_source(client, twitter_url, now)
            new_codes.extend(codes)

    if new_codes:
        _ordered_codes.extend(new_codes)
        _ordered_codes.sort(key=lambda item: item.first_seen, reverse=True)
        if len(_ordered_codes) > MAX_CODES:
            for entry in _ordered_codes[MAX_CODES:]:
                _codes.pop(entry.code, None)
            del _ordered_codes[MAX_CODES:]

    _last_fetch = time.time()
    logger.info(f"Scan complete. Found {len(new_codes)} new codes from {len(THREAD_URLS)} sources")
    return new_codes


def _prune_invalid_entries() -> None:
    if not _ordered_codes:
        return
    invalid_codes = {entry.code for entry in _ordered_codes if not is_valid_candidate(entry.code)}
    if not invalid_codes:
        return
    _ordered_codes[:] = [entry for entry in _ordered_codes if entry.code not in invalid_codes]
    for code in invalid_codes:
        _codes.pop(code, None)


async def scanner_loop() -> None:
    while True:
        try:
            async with _results_lock:
                await scan_once()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Scanner iteration failed: %s", exc)

        # Add random jitter to avoid pattern detection
        jitter = random.uniform(0, 10)
        sleep_time = FETCH_INTERVAL_SECONDS + jitter
        logger.info(f"Next scan in {sleep_time:.1f}s")
        await asyncio.sleep(sleep_time)


@app.on_event("startup")
async def startup_event() -> None:
    global _scanner_task
    if _scanner_task is None:
        _scanner_task = asyncio.create_task(scanner_loop())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    global _scanner_task
    if _scanner_task:
        _scanner_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _scanner_task
        _scanner_task = None


@app.get("/api/codes", response_model=CodesResponse)
async def get_codes() -> CodesResponse:
    async with _results_lock:
        _prune_invalid_entries()
        return CodesResponse(codes=list(_ordered_codes), fetched_at=_last_fetch)


@app.post("/api/scan", response_model=CodesResponse)
async def manual_scan() -> CodesResponse:
    async with _results_lock:
        await scan_once()
        _prune_invalid_entries()
        return CodesResponse(codes=list(_ordered_codes), fetched_at=_last_fetch)


@app.get("/api/health")
async def healthcheck() -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "codes_cached": len(_ordered_codes),
            "last_fetch": _last_fetch,
            "interval_seconds": FETCH_INTERVAL_SECONDS,
        }
    )


@app.get("/")
async def serve_index() -> FileResponse:
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend build not found")
    return FileResponse(index_file)
