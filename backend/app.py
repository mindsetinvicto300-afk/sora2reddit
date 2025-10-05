from __future__ import annotations

import asyncio
import contextlib
import logging
import os
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

THREAD_URL = os.getenv(
    "THREAD_URL",
    "https://www.reddit.com/r/OpenAI/comments/1nukmm2/open_ai_sora_2_invite_codes_megathread",
)
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


async def fetch_thread_json(client: httpx.AsyncClient) -> Dict[str, Any]:
    url = ensure_json_url(THREAD_URL)
    if SCRAPE_DO_TOKEN:
        proxy_url = f"https://api.scrape.do?token={SCRAPE_DO_TOKEN}&url={quote_plus(url)}"
        target_url = proxy_url
    else:
        target_url = url

    response = await client.get(target_url)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, list) and payload:
        return payload[1] if len(payload) > 1 else payload[0]
    if isinstance(payload, dict):
        return payload
    raise HTTPException(status_code=502, detail="Unexpected payload structure from Reddit")


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
    async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
        payload = await fetch_thread_json(client)

    listing = payload.get("data", {}).get("children", [])
    new_codes: list[CodeEntry] = []
    now = time.time()

    for comment in iter_comments(listing):
        body = comment.get("body")
        if not body:
            continue
        codes = extract_codes_from_body(body)
        if not codes:
            continue

        created_utc = float(comment.get("created_utc" or now))
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

    if new_codes:
        _ordered_codes.extend(new_codes)
        _ordered_codes.sort(key=lambda item: item.first_seen, reverse=True)
        if len(_ordered_codes) > MAX_CODES:
            for entry in _ordered_codes[MAX_CODES:]:
                _codes.pop(entry.code, None)
            del _ordered_codes[MAX_CODES:]

    _last_fetch = time.time()
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
        await asyncio.sleep(FETCH_INTERVAL_SECONDS)


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
