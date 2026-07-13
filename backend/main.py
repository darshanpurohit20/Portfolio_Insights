"""
Portfolio API — robust version
────────────────────────────────
Same endpoints / same response shape as before (frontend needs zero changes):
  GET  /
  GET  /api/stocks/quote
  POST /api/stocks/portfolio
  POST /api/portfolio/extract

What changed and why:
  1. fast_info and info are fetched independently — one failing doesn't kill the whole stock.
  2. "info" (sector/marketCap/capType) is cached separately with a MUCH longer TTL
     (it barely changes), so we stop re-hitting Yahoo for it on every request.
  3. A semaphore caps concurrent Yahoo calls (default 3) instead of firing 10-18 at once,
     which is what was tripping the rate limiter on HF's shared IP.
  4. @retry with exponential backoff + jitter, specifically for rate-limit / transient errors.
  5. @timed on every endpoint + the yfinance call, logged and returned in a "debug" block.
  6. A global exception handler + per-request logging middleware so the process
     can never crash from an unhandled error — it always returns JSON.
"""

import asyncio
import functools
import json
import logging
import os
import random
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Semaphore
from typing import Any, Dict, List, Optional, Tuple

import yfinance as yf
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from groq import Groq

load_dotenv()

# ─────────────────────────────────────────
# Logging
# ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("portfolio_api")


# ─────────────────────────────────────────
# Decorators
# ─────────────────────────────────────────
def timed(label: Optional[str] = None):
    """Logs how long a sync or async function took. Never swallows exceptions —
    logs the failure + duration, then re-raises so callers still handle it."""

    def decorator(func):
        name = label or func.__name__

        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    duration = time.perf_counter() - start
                    logger.info(f"[TIMING] {name} took {duration:.3f}s")
                    if isinstance(result, dict):
                        result.setdefault("_duration_sec", round(duration, 3))
                    return result
                except Exception:
                    duration = time.perf_counter() - start
                    logger.error(f"[TIMING] {name} FAILED after {duration:.3f}s")
                    raise
            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start
                logger.info(f"[TIMING] {name} took {duration:.3f}s")
                return result
            except Exception:
                duration = time.perf_counter() - start
                logger.error(f"[TIMING] {name} FAILED after {duration:.3f}s")
                raise
        return sync_wrapper
    return decorator


def retry(max_attempts: int = 3, base_delay: float = 0.75, backoff: float = 2.0,
          jitter: float = 0.4, exceptions: Tuple[type, ...] = (Exception,)):
    """Retries a sync function on the given exceptions with exponential backoff + jitter.
    Logs every attempt. Raises the last exception if all attempts are exhausted."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_attempts:
                        logger.error(
                            f"[RETRY] {func.__name__} failed after {attempt}/{max_attempts} "
                            f"attempts: {e}"
                        )
                        raise
                    sleep_for = delay + random.uniform(0, jitter)
                    logger.warning(
                        f"[RETRY] {func.__name__} attempt {attempt}/{max_attempts} "
                        f"failed ({e}); retrying in {sleep_for:.2f}s"
                    )
                    time.sleep(sleep_for)
                    delay *= backoff
            raise last_exc  # pragma: no cover
        return wrapper
    return decorator


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "too many requests" in msg or "rate limit" in msg or "429" in msg


# ─────────────────────────────────────────
# Rounding / math helpers
# ─────────────────────────────────────────
def round_money(x) -> float:
    try:
        return round(float(x), 2)
    except (TypeError, ValueError):
        return 0.0


round_percent = round_money
round_price = round_money


def safe_divide(a, b) -> float:
    return (a / b) if b else 0.0


# ─────────────────────────────────────────
# App setup
# ─────────────────────────────────────────
app = FastAPI(title="Portfolio API", version="8.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
        duration = time.perf_counter() - start
        logger.info(
            f"[REQUEST] {request.method} {request.url.path} -> "
            f"{response.status_code} in {duration:.3f}s"
        )
        return response
    except Exception:
        duration = time.perf_counter() - start
        logger.error(
            f"[REQUEST] {request.method} {request.url.path} -> UNHANDLED "
            f"EXCEPTION after {duration:.3f}s\n{traceback.format_exc()}"
        )
        return JSONResponse(
            status_code=500,
            content={"error": True, "stage": "unhandled", "message": "Internal server error"},
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"[UNCAUGHT] {request.method} {request.url.path}: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"error": True, "stage": "unhandled", "message": str(exc)},
    )


# ─────────────────────────────────────────
# Cache & concurrency configuration
# ─────────────────────────────────────────
price_cache: Dict[str, Any] = {}      # fast-moving: price, OHLC, volume
meta_cache: Dict[str, Any] = {}       # slow-moving: sector, marketCap, capType

PRICE_TTL = 90          # seconds — fresh
PRICE_STALE_TTL = 300   # seconds — usable-but-stale fallback
META_TTL = timedelta(hours=6)  # sector/marketCap barely change

MAX_CONCURRENT_YF_CALLS = 3   # actual cap on simultaneous Yahoo hits
executor = ThreadPoolExecutor(max_workers=10)
yf_semaphore = Semaphore(MAX_CONCURRENT_YF_CALLS)


def _normalize_symbol(symbol: str) -> str:
    return symbol.upper().replace(".NS", "").replace(".BO", "").strip()


def _market_cap_to_crore_rupees(market_cap: Optional[float]) -> float:
    try:
        return float(market_cap) / 1e7 if market_cap else 0.0
    except (TypeError, ValueError):
        return 0.0


def _classify_market_cap(market_cap_crore: float) -> str:
    if market_cap_crore >= 20000:
        return "Large Cap"
    if market_cap_crore >= 5000:
        return "Mid Cap"
    if market_cap_crore > 0:
        return "Small Cap"
    return "Unknown"


def _get_price_cache(symbol: str) -> Tuple[Optional[Dict[str, Any]], bool]:
    item = price_cache.get(symbol)
    if not item:
        return None, False
    age = (datetime.now() - item["cached_at"]).total_seconds()
    if age < PRICE_TTL:
        return item["data"], True
    if age < PRICE_STALE_TTL:
        return item["data"], False
    return None, False


def _get_meta_cache(symbol: str) -> Optional[Dict[str, Any]]:
    item = meta_cache.get(symbol)
    if not item:
        return None
    if datetime.now() - item["cached_at"] < META_TTL:
        return item["data"]
    return None


# ─────────────────────────────────────────
# yfinance fetch — fast_info and info are independent,
# each retried on rate-limit errors, each fails without
# taking the other down.
# ─────────────────────────────────────────
@retry(max_attempts=3, base_delay=0.75, backoff=2.0, exceptions=(Exception,))
def _fetch_fast_info(ticker: yf.Ticker) -> Dict[str, Any]:
    data = ticker.fast_info
    if data is None:
        raise ValueError("fast_info returned None")
    return dict(data)


@retry(max_attempts=2, base_delay=1.0, backoff=2.0, exceptions=(Exception,))
def _fetch_info(ticker: yf.Ticker) -> Dict[str, Any]:
    data = ticker.info
    if data is None:
        raise ValueError("info returned None")
    return dict(data)


def _get_meta(symbol: str, yf_symbol: str, ticker: yf.Ticker) -> Dict[str, Any]:
    """Sector / marketCap / capType, cached for hours since it rarely changes."""
    cached = _get_meta_cache(symbol)
    if cached is not None:
        return cached

    try:
        info = _fetch_info(ticker)
        market_cap = info.get("marketCap")
        market_cap_crore = _market_cap_to_crore_rupees(market_cap)
        meta = {
            "sector": info.get("sector", "Other") or "Other",
            "marketCap": market_cap or 0,
            "capType": _classify_market_cap(market_cap_crore),
        }
        meta_cache[symbol] = {"data": meta, "cached_at": datetime.now()}
        return meta
    except Exception as e:
        logger.warning(f"[META] {yf_symbol}: info fetch failed ({e}); using defaults")
        # Serve stale meta cache if we have *any*, even expired, rather than "Unknown"
        stale = meta_cache.get(symbol)
        if stale:
            return stale["data"]
        return {"sector": "Other", "marketCap": 0, "capType": "Unknown"}


@timed("_get_single_stock_data")
def _get_single_stock_data(symbol: str) -> Dict:
    base_symbol = _normalize_symbol(symbol)
    yf_symbol = base_symbol if base_symbol.endswith(".NS") else f"{base_symbol}.NS"

    with yf_semaphore:  # cap concurrent Yahoo hits regardless of thread pool size
        try:
            ticker = yf.Ticker(yf_symbol)

            try:
                fast = _fetch_fast_info(ticker)
            except Exception as e:
                logger.error(f"[PRICE] {yf_symbol}: fast_info failed after retries: {e}")
                return _error_result(symbol, f"price fetch failed: {e}")

            current = float(fast.get("lastPrice") or 0)
            prev_close = float(fast.get("previousClose") or 0)
            change = current - prev_close
            change_pct = safe_divide(change, prev_close) * 100

            meta = _get_meta(base_symbol, yf_symbol, ticker)

            result = {
                "symbol": base_symbol,
                "currentPrice": round_price(current),
                "dayHigh": round_price(fast.get("dayHigh", 0)),
                "dayLow": round_price(fast.get("dayLow", 0)),
                "high52w": round_price(fast.get("yearHigh", 0)),
                "low52w": round_price(fast.get("yearLow", 0)),
                "previousClose": round_price(prev_close),
                "change": round_percent(change),
                "changePercent": round_percent(change_pct),
                "volume": fast.get("volume", 0) or 0,
                "openPrice": round_price(fast.get("open", 0)),
                "history": [],
                "source": "Yahoo Finance",
                "sector": meta["sector"],
                "marketCap": meta["marketCap"],
                "capType": meta["capType"],
                "error": False,
                "cachedAt": datetime.now().isoformat(),
            }
            price_cache[base_symbol] = {"data": result, "cached_at": datetime.now()}
            return result

        except Exception as e:
            stage = "rate_limit" if _is_rate_limit_error(e) else "fetch_failed"
            logger.exception(f"[PRICE] {yf_symbol}: unexpected failure ({stage})")
            return _error_result(symbol, str(e))


def _error_result(symbol: str, msg: str) -> Dict:
    return {
        "symbol": symbol, "currentPrice": 0,
        "dayHigh": 0, "dayLow": 0, "high52w": 0, "low52w": 0,
        "previousClose": 0, "change": 0, "changePercent": 0, "volume": 0,
        "openPrice": 0, "history": [], "source": "ERROR", "error": True, "errorMsg": msg,
        "sector": "Other", "marketCap": 0, "capType": "Unknown",
        "cachedAt": datetime.now().isoformat(),
    }


@timed("get_stock_data_bulk")
async def get_stock_data_bulk(symbols: List[str]) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    to_fetch: List[str] = []

    for s in symbols:
        base_symbol = _normalize_symbol(s)
        data, is_fresh = _get_price_cache(base_symbol)
        if data:
            results[s] = data
            if not is_fresh:
                to_fetch.append(s)
        else:
            to_fetch.append(s)

    if not to_fetch:
        return results

    loop = asyncio.get_event_loop()
    tasks = [loop.run_in_executor(executor, _get_single_stock_data, s) for s in to_fetch]
    fetched_results = await asyncio.gather(*tasks, return_exceptions=True)

    for s, res in zip(to_fetch, fetched_results):
        if isinstance(res, Exception):
            logger.exception(f"[BULK] unhandled exception fetching {s}")
            results[s] = _error_result(s, f"unexpected error: {res}")
        elif res:
            results[s] = res
        elif s not in results:
            results[s] = _error_result(s, "fetch returned no data")

    return results


# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "status": "ok",
        "version": "8.0.0",
        "price_cache_size": len(price_cache),
        "meta_cache_size": len(meta_cache),
    }


@app.get("/api/stocks/quote")
@timed("GET /api/stocks/quote")
async def get_quotes(symbols: str):
    if not symbols:
        raise HTTPException(status_code=400, detail="No symbols provided")
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            raise HTTPException(status_code=400, detail="No valid symbols provided")
        return await get_stock_data_bulk(symbol_list)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[ENDPOINT] /api/stocks/quote failed")
        raise HTTPException(status_code=500, detail=f"Quote fetch failed: {e}")


@app.post("/api/stocks/portfolio")
@timed("POST /api/stocks/portfolio")
async def get_portfolio(data: Dict):
    try:
        portfolio = data.get("portfolio", [])
        if not portfolio:
            raise HTTPException(status_code=400, detail="No portfolio data provided")

        # Validate holdings up front instead of letting a bad row crash the loop
        symbol_map = {}
        for h in portfolio:
            try:
                symbol_map[h["symbol"]] = {"qty": float(h["qty"]), "buyPrice": float(h["buyPrice"])}
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"[PORTFOLIO] skipping malformed holding {h}: {e}")

        if not symbol_map:
            raise HTTPException(status_code=400, detail="No valid holdings in portfolio")

        stock_data = await get_stock_data_bulk(list(symbol_map.keys()))

        results = []
        total_invested = 0.0
        total_value = 0.0

        for symbol, h in symbol_map.items():
            qty, buy = h["qty"], h["buyPrice"]
            s_data = stock_data.get(symbol, {})
            current = float(s_data.get("currentPrice", 0) or 0)

            invested = qty * buy
            value = qty * current
            pnl = value - invested
            total_invested += invested
            total_value += value

            results.append({
                "symbol": symbol,
                "qty": qty,
                "buyPrice": round_price(buy),
                "currentPrice": round_price(current),
                "invested": round_money(invested),
                "currentValue": round_money(value),
                "pnl": round_money(pnl),
                "pnlPercent": round_percent(safe_divide(pnl, invested) * 100),
                "sector": s_data.get("sector", "Other"),
                "capType": s_data.get("capType", "Small Cap"),
                "priceError": s_data.get("error", False),
            })

        total_pnl = total_value - total_invested
        return {
            "holdings": results,
            "summary": {
                "totalInvested": round_money(total_invested),
                "totalValue": round_money(total_value),
                "totalPnl": round_money(total_pnl),
                "totalPnlPercent": round_percent(safe_divide(total_pnl, total_invested) * 100),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[ENDPOINT] /api/stocks/portfolio failed")
        raise HTTPException(status_code=500, detail=f"Portfolio calculation failed: {e}")


@app.post("/api/portfolio/extract")
async def extract_portfolio(payload: Dict):
    """Extracts holdings from a portfolio screenshot via Groq vision."""
    start_time = time.perf_counter()
    request_id = f"ocr_{int(time.time())}"

    is_prod = os.environ.get("SPACE_ID") is not None
    api_key = os.environ.get("GROQ_API_KEY")
    has_key = bool(api_key) and api_key != "your_groq_api_key_here"

    logger.info(f"[{request_id}] extraction request received (prod={is_prod}, has_key={has_key})")

    image_data = payload.get("image")
    if not image_data:
        logger.error(f"[{request_id}] missing image data")
        return JSONResponse(
            status_code=400,
            content={"error": True, "stage": "validation", "message": "Missing image data"},
        )

    payload_size_kb = len(image_data) / 1024
    logger.info(f"[{request_id}] payload size: {payload_size_kb:.2f} KB")

    mime_type = "image/jpeg"
    base64_image = image_data
    if "," in image_data:
        try:
            header, base64_image = image_data.split(",", 1)
            if "image/" in header:
                mime_type = header.split(":")[1].split(";")[0]
        except Exception as e:
            logger.warning(f"[{request_id}] MIME parse failed ({e}); defaulting to image/jpeg")

    if not has_key:
        logger.error(f"[{request_id}] GROQ_API_KEY not configured")
        return JSONResponse(
            status_code=401,
            content={
                "error": True, "stage": "auth_check",
                "message": "Groq API key not configured",
                "details": "Set GROQ_API_KEY in the environment / HF Space secrets.",
            },
        )

    prompt = """
    Analyze this stock portfolio screenshot and extract the holdings into a JSON array.
    For each holding, extract:
    - "symbol": The likely NSE stock symbol (e.g., RELIANCE, ITC, SBIN).
    - "qty": The number of shares owned as a number.
    - "buyPrice": The average buy price per share.

    If "Average Price" or "Avg Cost" is visible, use it.
    If NOT visible, use Last Price and Returns %:
    buyPrice = Last Price / (1 + (Returns % / 100)).

    Return ONLY a JSON object: {"data": [{"symbol": "ITC", "qty": 100, "buyPrice": 450.50}]}
    """

    try:
        client = Groq(api_key=api_key)
        api_start = time.perf_counter()

        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}},
                ],
            }],
            response_format={"type": "json_object"},
            timeout=45.0,
        )

        api_duration = time.perf_counter() - api_start
        total_duration = time.perf_counter() - start_time

        content = completion.choices[0].message.content
        result = json.loads(content)
        stocks_found = len(result.get("data", []))
        logger.info(f"[{request_id}] success: {stocks_found} stocks in {total_duration:.2f}s")

        return {
            "success": True,
            "data": result.get("data", []),
            "debug": {
                "api_time_sec": round(api_duration, 2),
                "total_time_sec": round(total_duration, 2),
                "payload_size_kb": round(payload_size_kb, 2),
                "mime": mime_type,
            },
        }

    except json.JSONDecodeError as e:
        logger.error(f"[{request_id}] Groq returned non-JSON: {e}")
        return JSONResponse(
            status_code=502,
            content={"error": True, "stage": "parse_error", "message": "Model returned invalid JSON"},
        )
    except Exception as e:
        total_duration = time.perf_counter() - start_time
        error_msg = str(e)
        logger.error(f"[{request_id}] extraction failed after {total_duration:.2f}s: {error_msg}")
        logger.error(f"[{request_id}] {traceback.format_exc()}")

        stage = "api_call"
        low = error_msg.lower()
        if "timeout" in low:
            stage = "api_timeout"
        elif "authentication" in low or "401" in low:
            stage = "api_auth"
        elif "connection" in low or "fetch" in low or "httpx" in low:
            stage = "network_issue"
        elif "429" in low or "rate" in low:
            stage = "rate_limit"

        return JSONResponse(
            status_code=500,
            content={
                "error": True, "stage": stage,
                "message": f"Extraction failed: {error_msg}",
                "details": {
                    "request_id": request_id,
                    "payload_size_kb": round(payload_size_kb, 2),
                    "total_time_sec": round(total_duration, 2),
                    "is_production": is_prod,
                },
            },
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)