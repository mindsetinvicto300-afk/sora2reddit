from __future__ import annotations

import asyncio
import contextlib
import gzip
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

THREAD_URLS = os.getenv(
    "THREAD_URLS",
    "https://www.reddit.com/r/OpenAI/comments/1o8kmg9/sora_2_megathread_part_3/,"
    "https://www.reddit.com/r/OpenAI/search.json?q=sora+invite+code&restrict_sr=1&sort=new&t=week,"
    "https://www.reddit.com/r/sora/search.json?q=invite+code&restrict_sr=1&sort=new&t=week"
).split(",")
TWITTER_SEARCH_URLS = os.getenv("TWITTER_SEARCH_URLS", "").split(",") if os.getenv("TWITTER_SEARCH_URLS") else []
FETCH_INTERVAL_SECONDS = float(os.getenv("FETCH_INTERVAL_SECONDS", "5"))
SCRAPE_DO_TOKEN = os.getenv("SCRAPE_DO_TOKEN")
MAX_CODES = int(os.getenv("MAX_CODES", "200"))

CODE_PATTERN = re.compile(r"\b[0-9A-Za-z]{6}\b")
BLACKLIST = {word.upper() for word in DEFAULT_BLACKLIST}

# User agents rotativos para evitar detecção
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

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
    """Garante que a URL termina com .json"""
    url = url.strip()
    if url.endswith(".json") or ".json?" in url:
        return url
    # Remove trailing slash antes de adicionar .json
    url = url.rstrip("/")
    return f"{url}.json"


def normalize_reddit_url(url: str) -> str:
    """Converte para old.reddit.com que é menos restritivo"""
    url = url.replace("www.reddit.com", "old.reddit.com")
    url = url.replace("reddit.com", "old.reddit.com")
    return ensure_json_url(url)


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
    """Busca JSON do Reddit com múltiplos fallbacks"""
    url = normalize_reddit_url(url)
    
    # Lista de métodos de proxy em ordem de preferência
    proxy_methods = []
    
    # ScraperAPI é a melhor opção se disponível
    if SCRAPE_DO_TOKEN:
        proxy_methods.append(
            ("ScraperAPI", f"http://api.scraperapi.com?api_key={SCRAPE_DO_TOKEN}&url={quote_plus(url)}")
        )
    
    # Proxies CORS como fallback
    proxy_methods.extend([
        ("AllOrigins", f"https://api.allorigins.win/raw?url={quote_plus(url)}"),
        ("ThingProxy", f"https://thingproxy.freeboard.io/fetch/{url}"),
        ("CORS-Anywhere", f"https://corsproxy.io/?{quote_plus(url)}"),
    ])
    
    # Tentar direto como último recurso
    proxy_methods.append(("Direct", url))
    
    last_error = None
    
    for proxy_name, target_url in proxy_methods:
        try:
            # User agent aleatório
            user_agent = random.choice(USER_AGENTS)
            headers = {
                "User-Agent": user_agent,
                "Accept": "application/json, text/html, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
            }
            
            logger.info(f"Tentando {proxy_name} para {url[:80]}...")
            
            response = await client.get(
                target_url,
                headers=headers,
                timeout=20,
                follow_redirects=True
            )
            response.raise_for_status()
            
            # Processar resposta
            content = response.content
            text = None
            
            # Descomprimir se for gzip
            if content and content[:2] == b'\x1f\x8b':
                try:
                    text = gzip.decompress(content).decode('utf-8')
                except Exception:
                    text = response.text
            else:
                text = response.text
            
            if not text or not text.strip():
                logger.warning(f"{proxy_name} retornou resposta vazia")
                continue
            
            # Parse JSON
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as je:
                preview = text[:200].encode('unicode_escape').decode('ascii')
                logger.warning(f"{proxy_name} retornou JSON inválido: {preview}")
                continue
            
            # Validar estrutura
            if isinstance(payload, list) and payload:
                logger.info(f"✓ {proxy_name} funcionou!")
                return payload[1] if len(payload) > 1 else payload[0]
            elif isinstance(payload, dict):
                logger.info(f"✓ {proxy_name} funcionou!")
                return payload
            else:
                logger.warning(f"{proxy_name} retornou estrutura inesperada")
                continue
                
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            logger.warning(f"{proxy_name} falhou com {status}")
            last_error = e
            
            # Se for 429 (rate limit), esperar um pouco
            if status == 429:
                await asyncio.sleep(2)
            continue
            
        except Exception as e:
            logger.warning(f"{proxy_name} falhou: {type(e).__name__}: {str(e)[:100]}")
            last_error = e
            continue
    
    # Todos os métodos falharam
    error_msg = f"Todos os proxies falharam para {url[:80]}"
    if last_error:
        error_msg += f" - Último erro: {last_error}"
    logger.error(error_msg)
    raise HTTPException(status_code=502, detail="Todos os métodos de proxy falharam")


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
    """Escaneia uma fonte do Reddit"""
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
                
        if new_codes:
            logger.info(f"Encontrados {len(new_codes)} códigos novos em {url[:80]}")
            
    except Exception as exc:
        logger.warning(f"Falha ao escanear {url[:80]}: {exc}")
    
    return new_codes


async def scan_twitter_source(client: httpx.AsyncClient, url: str, now: float) -> List[CodeEntry]:
    """Escaneia Twitter/X (requer ScraperAPI)"""
    new_codes: list[CodeEntry] = []
    
    if not SCRAPE_DO_TOKEN:
        logger.warning("Twitter requer SCRAPE_DO_TOKEN")
        return new_codes
    
    try:
        target_url = f"http://api.scraperapi.com?api_key={SCRAPE_DO_TOKEN}&url={quote_plus(url)}"
        response = await client.get(target_url, timeout=20)
        response.raise_for_status()
        
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
        logger.warning(f"Falha ao escanear Twitter {url}: {exc}")
    
    return new_codes


async def scan_once() -> List[CodeEntry]:
    global _last_fetch
    
    new_codes: list[CodeEntry] = []
    now = time.time()
    
    # Headers base
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
    }
    
    async with httpx.AsyncClient(timeout=20, headers=headers, follow_redirects=True) as client:
        # Escanear fontes do Reddit
        for thread_url in THREAD_URLS:
            thread_url = thread_url.strip()
            if not thread_url:
                continue
                
            logger.info(f"Escaneando Reddit: {thread_url[:80]}...")
            codes = await scan_reddit_source(client, thread_url, now)
            new_codes.extend(codes)
            
            # Pequeno delay entre requisições
            await asyncio.sleep(0.5)
        
        # Escanear Twitter se configurado
        for twitter_url in TWITTER_SEARCH_URLS:
            twitter_url = twitter_url.strip()
            if not twitter_url:
                continue
                
            logger.info(f"Escaneando Twitter: {twitter_url}")
            codes = await scan_twitter_source(client, twitter_url, now)
            new_codes.extend(codes)
    
    # Atualizar lista ordenada
    if new_codes:
        _ordered_codes.extend(new_codes)
        _ordered_codes.sort(key=lambda item: item.first_seen, reverse=True)
        
        if len(_ordered_codes) > MAX_CODES:
            for entry in _ordered_codes[MAX_CODES:]:
                _codes.pop(entry.code, None)
            del _ordered_codes[MAX_CODES:]
    
    _last_fetch = time.time()
    logger.info(f"Scan completo: {len(new_codes)} códigos novos de {len(THREAD_URLS)} fontes")
    
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
        except Exception as exc:
            logger.exception("Erro no scanner: %s", exc)
        
        # Jitter aleatório para evitar padrões
        jitter = random.uniform(0, 5)
        sleep_time = FETCH_INTERVAL_SECONDS + jitter
        logger.info(f"Próximo scan em {sleep_time:.1f}s")
        await asyncio.sleep(sleep_time)


@app.on_event("startup")
async def startup_event() -> None:
    global _scanner_task
    if _scanner_task is None:
        _scanner_task = asyncio.create_task(scanner_loop())
        logger.info("Scanner iniciado!")


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
    return JSONResponse({
        "status": "ok",
        "codes_cached": len(_ordered_codes),
        "last_fetch": _last_fetch,
        "interval_seconds": FETCH_INTERVAL_SECONDS,
        "scraper_enabled": bool(SCRAPE_DO_TOKEN),
    })


@app.get("/")
async def serve_index() -> FileResponse:
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend não encontrado")
    return FileResponse(index_file)
