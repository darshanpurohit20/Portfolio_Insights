from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging
import asyncio
from functools import lru_cache

# ─────────────────────────────────────────
# Logging
# ─────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Portfolio API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────
# In-Memory Cache (TTL: 15 minutes)
# Keyed by frozenset of symbols so bulk
# requests share cached results.
# ─────────────────────────────────────────
price_cache: Dict[str, Dict] = {}   # symbol → {data, cached_at}
CACHE_TTL = 15 * 60  # seconds


def is_cache_valid(symbol: str) -> bool:
    if symbol not in price_cache:
        return False
    elapsed = (datetime.now() - price_cache[symbol]["cached_at"]).total_seconds()
    return elapsed < CACHE_TTL


def get_cached_symbols(symbols: List[str]) -> tuple[Dict, List[str]]:
    """
    Split symbols into (already_cached_results, symbols_that_need_fetching).
    """
    cached = {}
    missing = []
    for s in symbols:
        if is_cache_valid(s):
            logger.info(f"[{s}] Cache HIT")
            cached[s] = price_cache[s]["data"]
        else:
            missing.append(s)
    return cached, missing


# ─────────────────────────────────────────
# Core: Single Bulk Fetch via yf.download()
#
# WHY yf.download() instead of ticker.info:
#   • ticker.info  → hits /v10/finance/quoteSummary/ (rate-limited heavily)
#   • yf.download() → hits /v8/finance/chart/ once for ALL symbols (bulk, tolerant)
#   • We derive everything we need from OHLCV data — no metadata endpoint needed
# ─────────────────────────────────────────
def bulk_fetch(symbols: List[str]) -> Dict[str, Dict]:
    """
    Fetch OHLCV data for all symbols in ONE yf.download() call.
    Derives: currentPrice, dayHigh, dayLow, previousClose, change,
             changePercent, high52w, low52w, volume, openPrice, history.

    Returns a dict: { symbol → stock_data_dict }
    """
    if not symbols:
        return {}

    logger.info(f"📡 Bulk fetching {len(symbols)} symbols: {symbols}")

    try:
        # Single network call for all symbols
        # auto_adjust=True: adjusts for splits/dividends automatically
        raw = yf.download(
            tickers=symbols,
            period="1y",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,       # parallel downloads internally
            progress=False,
        )
    except Exception as e:
        logger.error(f"yf.download() failed: {e}")
        return {s: _error_result(s, str(e)) for s in symbols}

    results = {}

    for symbol in symbols:
        try:
            # ── Extract per-symbol DataFrame ──────────────────────────────
            if len(symbols) == 1:
                # yf.download with a single ticker returns flat columns
                df = raw.copy()
            else:
                # Multi-ticker returns MultiIndex columns: (Field, Symbol)
                if symbol not in raw.columns.get_level_values(1):
                    raise ValueError(f"Symbol {symbol} not found in downloaded data")
                df = raw.xs(symbol, axis=1, level=1).copy()

            df.dropna(how="all", inplace=True)

            if df.empty or len(df) < 2:
                raise ValueError("Insufficient data returned")

            # ── Derive price metrics ───────────────────────────────────────
            latest   = df.iloc[-1]
            previous = df.iloc[-2]

            current_price    = float(latest["Close"])
            day_high         = float(latest["High"])
            day_low          = float(latest["Low"])
            previous_close   = float(previous["Close"])
            open_price       = float(latest["Open"])
            volume           = int(latest.get("Volume", 0))

            change           = current_price - previous_close
            change_percent   = (change / previous_close * 100) if previous_close else 0

            # 52-week high/low from the full year of data
            high_52w = float(df["High"].max())
            low_52w  = float(df["Low"].min())

            # Last 30 days history for sparkline/chart
            history = [
                {"date": d.strftime("%Y-%m-%d"), "close": float(r["Close"])}
                for d, r in df.tail(30).iterrows()
            ]

            result = {
                "symbol":        symbol,
                "currentPrice":  current_price,
                "dayHigh":       day_high,
                "dayLow":        day_low,
                "high52w":       high_52w,
                "low52w":        low_52w,
                "previousClose": previous_close,
                "change":        round(change, 4),
                "changePercent": round(change_percent, 4),
                "volume":        volume,
                "openPrice":     open_price,
                "history":       history,
                "source":        "Yahoo Finance (bulk)",
                "error":         False,
                "cachedAt":      datetime.now().isoformat(),
            }

            # Store in cache
            price_cache[symbol] = {"data": result, "cached_at": datetime.now()}
            logger.info(f"[{symbol}] ✓ ₹{current_price:.2f} ({change_percent:+.2f}%)")
            results[symbol] = result

        except Exception as e:
            logger.error(f"[{symbol}] Parse error: {e}")
            results[symbol] = _error_result(symbol, str(e))

    return results


def _error_result(symbol: str, msg: str) -> Dict:
    return {
        "symbol":        symbol,
        "currentPrice":  0,
        "dayHigh":       0,
        "dayLow":        0,
        "high52w":       0,
        "low52w":        0,
        "previousClose": 0,
        "change":        0,
        "changePercent": 0,
        "volume":        0,
        "openPrice":     0,
        "history":       [],
        "source":        "ERROR",
        "error":         True,
        "errorMsg":      msg,
    }


# ─────────────────────────────────────────
# Unified data-getter used by all endpoints
# ─────────────────────────────────────────
def get_stock_data_bulk(symbols: List[str]) -> Dict[str, Dict]:
    """
    Returns data for all requested symbols.
    Serves cached symbols immediately; fetches only uncached ones.
    """
    cached_results, missing = get_cached_symbols(symbols)

    if missing:
        fresh = bulk_fetch(missing)
        cached_results.update(fresh)

    return cached_results


# ─────────────────────────────────────────
# Routes
# ─────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Portfolio API v2 — uses yf.download() to avoid rate limits",
        "version": "2.0.0",
    }


@app.get("/health")
async def health():
    """
    Lightweight health check — avoids calling ticker.info (rate-limited).
    Uses a tiny yf.download() call instead.
    """
    try:
        test = yf.download("INFY.NS", period="5d", progress=False, threads=False)
        if test.empty:
            raise ValueError("Empty response from Yahoo Finance")
        return {"status": "healthy", "backend": "ready"}
    except Exception as e:
        return {"status": "degraded", "error": str(e)}


@app.get("/api/stocks/quote")
async def get_quotes(symbols: str):
    """
    Fetch quotes for one or more symbols.
    Query param: symbols=HDFCBANK.NS,ITC.NS,ADANIGREEN.NS

    All symbols are fetched in a SINGLE yf.download() call.
    Cache is checked first — uncached symbols are bulk-fetched together.
    """
    if not symbols:
        raise HTTPException(status_code=400, detail="No symbols provided")

    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    logger.info(f"\n📊 Quote request for: {symbol_list}")

    try:
        results = get_stock_data_bulk(symbol_list)
        logger.info(f"✅ Returned {len(results)} symbols\n")
        return results
    except Exception as e:
        logger.error(f"Quote API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stocks/portfolio")
async def get_portfolio(data: Dict):
    """
    Full portfolio endpoint.
    Body: {
        "portfolio": [
            {"symbol": "HDFCBANK.NS", "qty": 75, "buyPrice": 746.41},
            ...
        ]
    }

    All symbols are fetched in a single bulk request.
    """
    portfolio = data.get("portfolio", [])
    if not portfolio:
        raise HTTPException(status_code=400, detail="No portfolio data provided")

    # Deduplicate symbols (in case user sent the same stock twice)
    symbol_map = {h["symbol"].strip().upper(): h for h in portfolio}
    symbols = list(symbol_map.keys())

    logger.info(f"\n💼 Portfolio request for {len(symbols)} holdings")

    try:
        stock_data = get_stock_data_bulk(symbols)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    results = []
    total_invested = 0.0
    total_value = 0.0

    for symbol, holding in symbol_map.items():
        qty       = float(holding.get("qty", 0))
        buy_price = float(holding.get("buyPrice", 0))
        sd        = stock_data.get(symbol, _error_result(symbol, "Not fetched"))

        current_price = sd.get("currentPrice", 0)
        invested      = qty * buy_price
        current_value = qty * current_price
        pnl           = current_value - invested
        pnl_percent   = (pnl / invested * 100) if invested else 0

        total_invested += invested
        total_value    += current_value

        results.append({
            **sd,
            "qty":          qty,
            "buyPrice":     buy_price,
            "invested":     round(invested, 2),
            "currentValue": round(current_value, 2),
            "pnl":          round(pnl, 2),
            "pnlPercent":   round(pnl_percent, 4),
        })

    total_pnl = total_value - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested else 0

    return {
        "holdings": results,
        "summary": {
            "totalInvested":  round(total_invested, 2),
            "totalValue":     round(total_value, 2),
            "totalPnl":       round(total_pnl, 2),
            "totalPnlPercent": round(total_pnl_pct, 4),
        },
    }


@app.get("/api/stocks/cache/status")
async def cache_status():
    """Show what's currently in cache and when it expires."""
    now = datetime.now()
    entries = []
    for symbol, entry in price_cache.items():
        age = (now - entry["cached_at"]).total_seconds()
        entries.append({
            "symbol":     symbol,
            "ageSeconds": int(age),
            "expiresIn":  max(0, int(CACHE_TTL - age)),
            "valid":      age < CACHE_TTL,
        })
    return {"cacheSize": len(price_cache), "entries": entries}


@app.get("/api/stocks/cache/clear")
async def clear_cache():
    global price_cache
    size = len(price_cache)
    price_cache = {}
    return {"message": f"Cache cleared — removed {size} entries"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)