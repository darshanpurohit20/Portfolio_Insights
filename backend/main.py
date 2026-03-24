# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from typing import Dict, List, Optional
# import yfinance as yf
# import pandas as pd
# from datetime import datetime, timedelta
# import logging
# import asyncio
# from functools import lru_cache

# # ─────────────────────────────────────────
# # Logging
# # ─────────────────────────────────────────
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# app = FastAPI(title="Portfolio API", version="2.0.0")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ─────────────────────────────────────────
# # In-Memory Cache (TTL: 15 minutes)
# # Keyed by frozenset of symbols so bulk
# # requests share cached results.
# # ─────────────────────────────────────────
# price_cache: Dict[str, Dict] = {}   # symbol → {data, cached_at}
# CACHE_TTL = 15 * 60  # seconds


# def is_cache_valid(symbol: str) -> bool:
#     if symbol not in price_cache:
#         return False
#     elapsed = (datetime.now() - price_cache[symbol]["cached_at"]).total_seconds()
#     return elapsed < CACHE_TTL


# def get_cached_symbols(symbols: List[str]) -> tuple[Dict, List[str]]:
#     """
#     Split symbols into (already_cached_results, symbols_that_need_fetching).
#     """
#     cached = {}
#     missing = []
#     for s in symbols:
#         if is_cache_valid(s):
#             logger.info(f"[{s}] Cache HIT")
#             cached[s] = price_cache[s]["data"]
#         else:
#             missing.append(s)
#     return cached, missing


# # ─────────────────────────────────────────
# # Core: Single Bulk Fetch via yf.download()
# #
# # WHY yf.download() instead of ticker.info:
# #   • ticker.info  → hits /v10/finance/quoteSummary/ (rate-limited heavily)
# #   • yf.download() → hits /v8/finance/chart/ once for ALL symbols (bulk, tolerant)
# #   • We derive everything we need from OHLCV data — no metadata endpoint needed
# # ─────────────────────────────────────────
# def bulk_fetch(symbols: List[str]) -> Dict[str, Dict]:
#     """
#     Fetch OHLCV data for all symbols in ONE yf.download() call.
#     Derives: currentPrice, dayHigh, dayLow, previousClose, change,
#              changePercent, high52w, low52w, volume, openPrice, history.

#     Returns a dict: { symbol → stock_data_dict }
#     """
#     if not symbols:
#         return {}

#     logger.info(f"📡 Bulk fetching {len(symbols)} symbols: {symbols}")

#     try:
#         # Single network call for all symbols
#         # auto_adjust=True: adjusts for splits/dividends automatically
#         raw = yf.download(
#             tickers=symbols,
#             period="1y",
#             interval="1d",
#             group_by="ticker",
#             auto_adjust=True,
#             threads=True,       # parallel downloads internally
#             progress=False,
#         )
#     except Exception as e:
#         logger.error(f"yf.download() failed: {e}")
#         return {s: _error_result(s, str(e)) for s in symbols}

#     results = {}

#     for symbol in symbols:
#         try:
#             # ── Extract per-symbol DataFrame ──────────────────────────────
#             if len(symbols) == 1:
#                 # yf.download with a single ticker returns flat columns
#                 df = raw.copy()
#             else:
#                 # Multi-ticker returns MultiIndex columns: (Field, Symbol)
#                 if symbol not in raw.columns.get_level_values(1):
#                     raise ValueError(f"Symbol {symbol} not found in downloaded data")
#                 df = raw.xs(symbol, axis=1, level=1).copy()

#             df.dropna(how="all", inplace=True)

#             if df.empty or len(df) < 2:
#                 raise ValueError("Insufficient data returned")

#             # ── Derive price metrics ───────────────────────────────────────
#             latest   = df.iloc[-1]
#             previous = df.iloc[-2]

#             current_price    = float(latest["Close"])
#             day_high         = float(latest["High"])
#             day_low          = float(latest["Low"])
#             previous_close   = float(previous["Close"])
#             open_price       = float(latest["Open"])
#             volume           = int(latest.get("Volume", 0))

#             change           = current_price - previous_close
#             change_percent   = (change / previous_close * 100) if previous_close else 0

#             # 52-week high/low from the full year of data
#             high_52w = float(df["High"].max())
#             low_52w  = float(df["Low"].min())

#             # Last 30 days history for sparkline/chart
#             history = [
#                 {"date": d.strftime("%Y-%m-%d"), "close": float(r["Close"])}
#                 for d, r in df.tail(30).iterrows()
#             ]

#             result = {
#                 "symbol":        symbol,
#                 "currentPrice":  current_price,
#                 "dayHigh":       day_high,
#                 "dayLow":        day_low,
#                 "high52w":       high_52w,
#                 "low52w":        low_52w,
#                 "previousClose": previous_close,
#                 "change":        round(change, 4),
#                 "changePercent": round(change_percent, 4),
#                 "volume":        volume,
#                 "openPrice":     open_price,
#                 "history":       history,
#                 "source":        "Yahoo Finance (bulk)",
#                 "error":         False,
#                 "cachedAt":      datetime.now().isoformat(),
#             }

#             # Store in cache
#             price_cache[symbol] = {"data": result, "cached_at": datetime.now()}
#             logger.info(f"[{symbol}] ✓ ₹{current_price:.2f} ({change_percent:+.2f}%)")
#             results[symbol] = result

#         except Exception as e:
#             logger.error(f"[{symbol}] Parse error: {e}")
#             results[symbol] = _error_result(symbol, str(e))

#     return results


# def _error_result(symbol: str, msg: str) -> Dict:
#     return {
#         "symbol":        symbol,
#         "currentPrice":  0,
#         "dayHigh":       0,
#         "dayLow":        0,
#         "high52w":       0,
#         "low52w":        0,
#         "previousClose": 0,
#         "change":        0,
#         "changePercent": 0,
#         "volume":        0,
#         "openPrice":     0,
#         "history":       [],
#         "source":        "ERROR",
#         "error":         True,
#         "errorMsg":      msg,
#     }


# # ─────────────────────────────────────────
# # Unified data-getter used by all endpoints
# # ─────────────────────────────────────────
# def get_stock_data_bulk(symbols: List[str]) -> Dict[str, Dict]:
#     """
#     Returns data for all requested symbols.
#     Serves cached symbols immediately; fetches only uncached ones.
#     """
#     cached_results, missing = get_cached_symbols(symbols)

#     if missing:
#         fresh = bulk_fetch(missing)
#         cached_results.update(fresh)

#     return cached_results


# # ─────────────────────────────────────────
# # Routes
# # ─────────────────────────────────────────

# @app.get("/")
# async def root():
#     return {
#         "status": "ok",
#         "message": "Portfolio API v2 — uses yf.download() to avoid rate limits",
#         "version": "2.0.0",
#     }


# @app.get("/health")
# async def health():
#     """
#     Lightweight health check — avoids calling ticker.info (rate-limited).
#     Uses a tiny yf.download() call instead.
#     """
#     try:
#         test = yf.download("INFY.NS", period="5d", progress=False, threads=False)
#         if test.empty:
#             raise ValueError("Empty response from Yahoo Finance")
#         return {"status": "healthy", "backend": "ready"}
#     except Exception as e:
#         return {"status": "degraded", "error": str(e)}


# @app.get("/api/stocks/quote")
# async def get_quotes(symbols: str):
#     """
#     Fetch quotes for one or more symbols.
#     Query param: symbols=HDFCBANK.NS,ITC.NS,ADANIGREEN.NS

#     All symbols are fetched in a SINGLE yf.download() call.
#     Cache is checked first — uncached symbols are bulk-fetched together.
#     """
#     if not symbols:
#         raise HTTPException(status_code=400, detail="No symbols provided")

#     symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
#     logger.info(f"\n📊 Quote request for: {symbol_list}")

#     try:
#         results = get_stock_data_bulk(symbol_list)
#         logger.info(f"✅ Returned {len(results)} symbols\n")
#         return results
#     except Exception as e:
#         logger.error(f"Quote API error: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @app.post("/api/stocks/portfolio")
# async def get_portfolio(data: Dict):
#     """
#     Full portfolio endpoint.
#     Body: {
#         "portfolio": [
#             {"symbol": "HDFCBANK.NS", "qty": 75, "buyPrice": 746.41},
#             ...
#         ]
#     }

#     All symbols are fetched in a single bulk request.
#     """
#     portfolio = data.get("portfolio", [])
#     if not portfolio:
#         raise HTTPException(status_code=400, detail="No portfolio data provided")

#     # Deduplicate symbols (in case user sent the same stock twice)
#     symbol_map = {h["symbol"].strip().upper(): h for h in portfolio}
#     symbols = list(symbol_map.keys())

#     logger.info(f"\n💼 Portfolio request for {len(symbols)} holdings")

#     try:
#         stock_data = get_stock_data_bulk(symbols)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

#     results = []
#     total_invested = 0.0
#     total_value = 0.0

#     for symbol, holding in symbol_map.items():
#         qty       = float(holding.get("qty", 0))
#         buy_price = float(holding.get("buyPrice", 0))
#         sd        = stock_data.get(symbol, _error_result(symbol, "Not fetched"))

#         current_price = sd.get("currentPrice", 0)
#         invested      = qty * buy_price
#         current_value = qty * current_price
#         pnl           = current_value - invested
#         pnl_percent   = (pnl / invested * 100) if invested else 0

#         total_invested += invested
#         total_value    += current_value

#         results.append({
#             **sd,
#             "qty":          qty,
#             "buyPrice":     buy_price,
#             "invested":     round(invested, 2),
#             "currentValue": round(current_value, 2),
#             "pnl":          round(pnl, 2),
#             "pnlPercent":   round(pnl_percent, 4),
#         })

#     total_pnl = total_value - total_invested
#     total_pnl_pct = (total_pnl / total_invested * 100) if total_invested else 0

#     return {
#         "holdings": results,
#         "summary": {
#             "totalInvested":  round(total_invested, 2),
#             "totalValue":     round(total_value, 2),
#             "totalPnl":       round(total_pnl, 2),
#             "totalPnlPercent": round(total_pnl_pct, 4),
#         },
#     }


# @app.get("/api/stocks/cache/status")
# async def cache_status():
#     """Show what's currently in cache and when it expires."""
#     now = datetime.now()
#     entries = []
#     for symbol, entry in price_cache.items():
#         age = (now - entry["cached_at"]).total_seconds()
#         entries.append({
#             "symbol":     symbol,
#             "ageSeconds": int(age),
#             "expiresIn":  max(0, int(CACHE_TTL - age)),
#             "valid":      age < CACHE_TTL,
#         })
#     return {"cacheSize": len(price_cache), "entries": entries}


# @app.get("/api/stocks/cache/clear")
# async def clear_cache():
#     global price_cache
#     size = len(price_cache)
#     price_cache = {}
#     return {"message": f"Cache cleared — removed {size} entries"}


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=7860)

"""
Portfolio API v3 — NSEPython backend
--------------------------------------
Switched from yfinance → nsepython because:
  • Yahoo Finance actively blocks HuggingFace's shared cloud IPs
  • yf.download() returns empty body (char 0 error) — not rate-limited, IP-banned
  • nsepython hits NSE's own servers directly, which do NOT block cloud IPs
  • NSE data is also more accurate for Indian stocks (no currency conversion quirks)

Install: pip install nsepython fastapi uvicorn pandas
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
from datetime import datetime, timedelta
import pandas as pd
import logging
import time

# nsepython wraps NSE's official API with proper headers/cookies
from nsepython import nse_quote, nsefetch
from dotenv import load_dotenv
load_dotenv()
# Import rounding utilities for financial accuracy
from rounding import (
    round_money, round_percent, round_price,
    safe_divide, format_holding, calculate_portfolio_summary,
    calculate_scenario_value, apply_rounding_to_stock_quote
)

# ─────────────────────────────────────────
# App setup
# ─────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Portfolio API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────
# Cache  (symbol → {data, cached_at})
# ─────────────────────────────────────────
price_cache: Dict[str, Dict] = {}
CACHE_TTL = 15 * 60  # 15 minutes


def is_cache_valid(symbol: str) -> bool:
    if symbol not in price_cache:
        return False
    return (datetime.now() - price_cache[symbol]["cached_at"]).total_seconds() < CACHE_TTL


def _nse_symbol(symbol: str) -> str:
    """Strip exchange suffix: 'HDFCBANK.NS' → 'HDFCBANK'"""
    return symbol.upper().replace(".NS", "").replace(".BO", "")


# ─────────────────────────────────────────
# NSE: fetch quote (current price + day stats)
# ─────────────────────────────────────────
# def _fetch_quote(nse_sym: str) -> Dict:
#     """
#     nse_quote() returns a dict with keys:
#       priceInfo.lastPrice, priceInfo.open, priceInfo.intraDayHighLow,
#       priceInfo.weekHighLow, info.symbol, etc.
#     """
#     data = nse_quote(nse_sym)

#     price_info = data.get("priceInfo", {})
#     intra      = price_info.get("intraDayHighLow", {})
#     week       = price_info.get("weekHighLow", {})

#     current    = float(price_info.get("lastPrice", 0))
#     open_price = float(price_info.get("open", 0))
#     prev_close = float(price_info.get("previousClose", 0))
#     day_high   = float(intra.get("max", 0))
#     day_low    = float(intra.get("min", 0))
#     high_52w   = float(week.get("max", 0))
#     low_52w    = float(week.get("min", 0))

#     change     = current - prev_close
#     change_pct = (change / prev_close * 100) if prev_close else 0

#     return {
#         "current":   current,
#         "open":      open_price,
#         "prevClose": prev_close,
#         "dayHigh":   day_high,
#         "dayLow":    day_low,
#         "high52w":   high_52w,
#         "low52w":    low_52w,
#         "change":    round(change, 4),
#         "changePct": round(change_pct, 4),
#     }
# def _fetch_quote(nse_sym: str) -> Dict:
#     data = nse_quote(nse_sym)

#     # Try primary source
#     price_info = data.get("priceInfo", {})

#     # 🔥 FALLBACK (important)
#     if not price_info:
#         price_info = data.get("metadata", {})

#     intra = price_info.get("intraDayHighLow", {})
#     week  = price_info.get("weekHighLow", {})

#     current = float(price_info.get("lastPrice", 0))
#     open_price = float(price_info.get("open", 0))
#     prev_close = float(price_info.get("previousClose", 0))

#     # 🔥 fallback for day high/low
#     day_high = float(intra.get("max", price_info.get("dayHigh", 0)))
#     day_low  = float(intra.get("min", price_info.get("dayLow", 0)))

#     high_52w = float(week.get("max", 0))
#     low_52w  = float(week.get("min", 0))
#     logger.info(f"[DEBUG {nse_sym}] {data}")
#     change = current - prev_close
#     change_pct = (change / prev_close * 100) if prev_close else 0

#     return {
#         "current":   current,
#         "open":      open_price,
#         "prevClose": prev_close,
#         "dayHigh":   day_high,
#         "dayLow":    day_low,
#         "high52w":   high_52w,
#         "low52w":    low_52w,
#         "change":    round(change, 4),
#         "changePct": round(change_pct, 4),
#     }
def _fetch_quote(nse_sym: str) -> Dict:
    """
    Fetch stock quote from NSE.
    
    All values are kept in full precision during calculation,
    then rounded at output stage.
    """
    url = f"https://www.nseindia.com/api/quote-equity?symbol={nse_sym}"

    data = nsefetch(url)

    price_info = data.get("priceInfo", {})

    if not price_info:
        raise ValueError("No priceInfo returned")

    intra = price_info.get("intraDayHighLow", {})
    week  = price_info.get("weekHighLow", {})

    # Step 1: Extract with full precision (no rounding yet)
    current = float(price_info.get("lastPrice", 0))
    open_price = float(price_info.get("open", 0))
    prev_close = float(price_info.get("previousClose", 0))

    day_high = float(intra.get("max", 0))
    day_low  = float(intra.get("min", 0))

    high_52w = float(week.get("max", 0))
    low_52w  = float(week.get("min", 0))

    # Step 2: Calculate change with full precision
    change = current - prev_close
    change_pct = safe_divide(change, prev_close) * 100.0

    # Step 3: Round only at output stage
    return {
        "current":   round_price(current),
        "open":      round_price(open_price),
        "prevClose": round_price(prev_close),
        "dayHigh":   round_price(day_high),
        "dayLow":    round_price(day_low),
        "high52w":   round_price(high_52w),
        "low52w":    round_price(low_52w),
        "change":    round_percent(change),
        "changePct": round_percent(change_pct),
    }
# ─────────────────────────────────────────
# NSE: fetch 1-year history for sparkline
# ─────────────────────────────────────────
def _fetch_history(nse_sym: str) -> List[Dict]:
    """
    NSE historical endpoint returns daily OHLCV.
    We fetch last 365 days and keep the last 30 for the chart.
    """
    to_date   = datetime.now()
    from_date = to_date - timedelta(days=365)

    url = (
        f"https://www.nseindia.com/api/historical/cm/equity"
        f'?symbol={nse_sym}&series=["EQ","BE","ETF"]'
        f'&from={from_date.strftime("%d-%m-%Y")}'
        f'&to={to_date.strftime("%d-%m-%Y")}'
        f'&csv=false'
    )

    try:
        response = nsefetch(url)
        rows = response.get("data", [])

        history = []
        for row in rows[-30:]:   # last 30 trading days
            history.append({
                "date":  row.get("CH_TIMESTAMP", ""),
                "close": float(row.get("CH_CLOSING_PRICE", 0)),
            })
        return history
    except Exception as e:
        logger.warning(f"[{nse_sym}] History fetch failed: {e}")
        return []


# ─────────────────────────────────────────
# Core: fetch one symbol from NSE
# ─────────────────────────────────────────
def fetch_single(symbol: str) -> Dict:
    """Fetch quote + history for one symbol from NSE."""
    nse_sym = _nse_symbol(symbol)
    logger.info(f"[{symbol}] → NSE fetch for '{nse_sym}'")

    try:
        quote   = _fetch_quote(nse_sym)
        history = _fetch_history(nse_sym)

        result = {
            "symbol":        symbol,
            "currentPrice":  quote["current"],
            "dayHigh":       quote["dayHigh"],
            "dayLow":        quote["dayLow"],
            "high52w":       quote["high52w"],
            "low52w":        quote["low52w"],
            "previousClose": quote["prevClose"],
            "change":        quote["change"],
            "changePercent": quote["changePct"],
            "volume":        0,
            "openPrice":     quote["open"],
            "history":       history,
            "source":        "NSE India",
            "error":         False,
            "cachedAt":      datetime.now().isoformat(),
        }

        price_cache[symbol] = {"data": result, "cached_at": datetime.now()}
        logger.info(f"[{symbol}] ✓ ₹{quote['current']:.2f} ({quote['changePct']:+.2f}%)")
        return result

    except Exception as e:
        logger.error(f"[{symbol}] NSE fetch failed: {e}")
        return _error_result(symbol, str(e))


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
# Batch fetcher with cache + small delay
# ─────────────────────────────────────────
def get_stock_data_bulk(symbols: List[str]) -> Dict[str, Dict]:
    results  = {}
    to_fetch = []

    for s in symbols:
        if is_cache_valid(s):
            logger.info(f"[{s}] Cache HIT")
            results[s] = price_cache[s]["data"]
        else:
            to_fetch.append(s)

    for i, symbol in enumerate(to_fetch):
        results[symbol] = fetch_single(symbol)
        if i < len(to_fetch) - 1:
            time.sleep(0.3)   # courtesy delay between NSE calls

    return results


# ─────────────────────────────────────────
# Routes
# ─────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "status":  "ok",
        "message": "Portfolio API v3 — powered by NSE India (no Yahoo Finance)",
        "version": "3.0.0",
    }


@app.get("/health")
async def health():
    try:
        data = nse_quote("INFY")
        if not data or "priceInfo" not in data:
            raise ValueError("Unexpected NSE response")
        price = data["priceInfo"]["lastPrice"]
        return {"status": "healthy", "testSymbol": "INFY", "price": price}
    except Exception as e:
        return {"status": "degraded", "error": str(e)}


@app.get("/api/stocks/quote")
async def get_quotes(symbols: str):
    """
    Fetch quotes for one or more NSE symbols.
    Query param: symbols=HDFCBANK.NS,ITC.NS,ADANIGREEN.NS
    .NS suffix is accepted and stripped automatically.
    """
    if not symbols:
        raise HTTPException(status_code=400, detail="No symbols provided")

    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    logger.info(f"\n📊 Quote request: {symbol_list}")

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
    Full portfolio with P&L calculations.
    Body: {"portfolio": [{"symbol": "HDFCBANK.NS", "qty": 75, "buyPrice": 746.41}, ...]}
    
    ROUNDING STRATEGY:
    1. Calculate all values in full floating-point precision
    2. Accumulate totals from unrounded values
    3. Round ONLY when building the response
    4. This ensures: sum(rounded items) ≈ rounded(total)
    """
    portfolio = data.get("portfolio", [])
    if not portfolio:
        raise HTTPException(status_code=400, detail="No portfolio data provided")

    symbol_map = {h["symbol"].strip().upper(): h for h in portfolio}
    symbols    = list(symbol_map.keys())
    logger.info(f"\n💼 Portfolio request: {len(symbols)} holdings")

    try:
        stock_data = get_stock_data_bulk(symbols)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Step 1: Process each holding with FULL PRECISION
    # (Do NOT round at this stage — maintain precision for totals)
    results        = []
    total_invested = 0.0  # Accumulate unrounded values
    total_value    = 0.0  # Accumulate unrounded values

    for symbol, holding in symbol_map.items():
        qty       = float(holding.get("qty", 0))
        buy_price = float(holding.get("buyPrice", 0))
        sd        = stock_data.get(symbol, _error_result(symbol, "Not fetched"))

        current_price = float(sd.get("currentPrice", 0))
        
        # Calculate with full precision
        invested = qty * buy_price
        current_value = qty * current_price
        pnl = current_value - invested
        pnl_percent = safe_divide(pnl, invested) * 100.0

        # Accumulate for totals (keep precision)
        total_invested += invested
        total_value    += current_value

        # Step 2: Format holding with rounded values for output
        formatted_holding = {
            **sd,
            "qty":          qty,
            "buyPrice":     round_price(buy_price),
            "currentPrice": round_price(current_price),
            "invested":     round_money(invested),
            "currentValue": round_money(current_value),
            "pnl":          round_money(pnl),
            "pnlPercent":   round_percent(pnl_percent),
        }
        results.append(formatted_holding)

    # Step 3: Calculate portfolio totals from UNROUNDED values
    total_pnl     = total_value - total_invested
    total_pnl_pct = safe_divide(total_pnl, total_invested) * 100.0

    # Step 4: Round summary AFTER calculating from full-precision totals
    summary = {
        "totalInvested":   round_money(total_invested),
        "totalValue":      round_money(total_value),
        "totalPnl":        round_money(total_pnl),
        "totalPnlPercent": round_percent(total_pnl_pct),
    }

    return {
        "holdings": results,
        "summary": summary
    }


@app.post("/api/stocks/scenarios")
async def get_portfolio_scenarios(data: Dict):
    """
    Calculate portfolio value under different price scenarios.
    Useful for "What if?" analysis:
      - What if price touches day high/low?
      - What if price touches 52-week high/low?
    
    Body: {
        "portfolio": [
            {"symbol": "HDFCBANK.NS", "qty": 75, "buyPrice": 746.41},
            ...
        ]
    }
    
    Response includes current + scenario values for each holding.
    """
    portfolio = data.get("portfolio", [])
    if not portfolio:
        raise HTTPException(status_code=400, detail="No portfolio data provided")

    symbol_map = {h["symbol"].strip().upper(): h for h in portfolio}
    symbols    = list(symbol_map.keys())
    logger.info(f"\n📊 Scenario request: {len(symbols)} holdings")

    try:
        stock_data = get_stock_data_bulk(symbols)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    results = []
    totals_at_current = {"value": 0.0, "pnl": 0.0}
    totals_at_day_high = {"value": 0.0, "pnl": 0.0}
    totals_at_day_low = {"value": 0.0, "pnl": 0.0}
    totals_at_52w_high = {"value": 0.0, "pnl": 0.0}
    totals_at_52w_low = {"value": 0.0, "pnl": 0.0}

    for symbol, holding in symbol_map.items():
        qty = float(holding.get("qty", 0))
        buy_price = float(holding.get("buyPrice", 0))
        sd = stock_data.get(symbol, _error_result(symbol, "Not fetched"))

        current_price = float(sd.get("currentPrice", 0))
        day_high = float(sd.get("dayHigh", 0))
        day_low = float(sd.get("dayLow", 0))
        high_52w = float(sd.get("high52w", 0))
        low_52w = float(sd.get("low52w", 0))

        invested = qty * buy_price

        # Calculate at current price
        at_current = calculate_scenario_value(qty, current_price, invested_per_unit=buy_price)
        
        # Calculate at day high/low
        at_day_high = calculate_scenario_value(qty, day_high, invested_per_unit=buy_price)
        at_day_low = calculate_scenario_value(qty, day_low, invested_per_unit=buy_price)
        
        # Calculate at 52-week high/low
        at_52w_high = calculate_scenario_value(qty, high_52w, invested_per_unit=buy_price)
        at_52w_low = calculate_scenario_value(qty, low_52w, invested_per_unit=buy_price)

        # Accumulate for totals
        totals_at_current["value"] += qty * current_price
        totals_at_current["pnl"] += at_current["pnl"]
        
        totals_at_day_high["value"] += qty * day_high
        totals_at_day_high["pnl"] += at_day_high["pnl"]
        
        totals_at_day_low["value"] += qty * day_low
        totals_at_day_low["pnl"] += at_day_low["pnl"]
        
        totals_at_52w_high["value"] += qty * high_52w
        totals_at_52w_high["pnl"] += at_52w_high["pnl"]
        
        totals_at_52w_low["value"] += qty * low_52w
        totals_at_52w_low["pnl"] += at_52w_low["pnl"]

        results.append({
            "symbol": symbol,
            "qty": qty,
            "buyPrice": round_price(buy_price),
            "invested": round_money(invested),
            "scenarios": {
                "current": at_current,
                "dayHigh": {**at_day_high, "price": round_price(day_high)},
                "dayLow": {**at_day_low, "price": round_price(day_low)},
                "high52w": {**at_52w_high, "price": round_price(high_52w)},
                "low52w": {**at_52w_low, "price": round_price(low_52w)},
            }
        })

    # Calculate total invested
    total_invested = sum(float(h.get("qty", 0)) * float(h.get("buyPrice", 0)) for h in portfolio)

    return {
        "holdings": results,
        "scenarioSummary": {
            "totalInvested": round_money(total_invested),
            "atCurrent": {
                "value": round_money(totals_at_current["value"]),
                "pnl": round_money(totals_at_current["pnl"]),
                "pnlPercent": round_percent(safe_divide(totals_at_current["pnl"], total_invested) * 100.0),
            },
            "atDayHigh": {
                "value": round_money(totals_at_day_high["value"]),
                "pnl": round_money(totals_at_day_high["pnl"]),
                "pnlPercent": round_percent(safe_divide(totals_at_day_high["pnl"], total_invested) * 100.0),
            },
            "atDayLow": {
                "value": round_money(totals_at_day_low["value"]),
                "pnl": round_money(totals_at_day_low["pnl"]),
                "pnlPercent": round_percent(safe_divide(totals_at_day_low["pnl"], total_invested) * 100.0),
            },
            "at52wHigh": {
                "value": round_money(totals_at_52w_high["value"]),
                "pnl": round_money(totals_at_52w_high["pnl"]),
                "pnlPercent": round_percent(safe_divide(totals_at_52w_high["pnl"], total_invested) * 100.0),
            },
            "at52wLow": {
                "value": round_money(totals_at_52w_low["value"]),
                "pnl": round_money(totals_at_52w_low["pnl"]),
                "pnlPercent": round_percent(safe_divide(totals_at_52w_low["pnl"], total_invested) * 100.0),
            },
        }
    }


@app.post("/api/portfolio/extract")
async def extract_portfolio_from_image(data: Dict):
    """
    Extract portfolio holdings from an image using OCR.
    
    Flow:
    1. Receive base64 image
    2. Use pytesseract to extract text from image
    3. Send extracted text to Groq's text model with detailed prompt
    4. Parse LLM response to extract symbol, qty, buyPrice
    5. Return structured portfolio data
    
    Body: {"image": "data:image/png;base64,iVBOR..."}
    """
    import base64
    import io
    import json
    import os
    from PIL import Image
    import pytesseract
    from groq import Groq

    try:
        image_data = data.get("image")
        if not image_data:
            raise ValueError("No image provided")

        # Extract base64 data
        if "base64," in image_data:
            image_data = image_data.split("base64,")[1]

        # Decode base64 to image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if necessary (handles PNG with transparency, etc.)
        if image.mode != "RGB":
            image = image.convert("RGB")

        logger.info("🖼️ Image received, extracting text via OCR...")

        # Step 1: Extract text using Tesseract OCR
        extracted_text = pytesseract.image_to_string(image)
        logger.info(f"📄 OCR extracted text:\n{extracted_text[:500]}...")

        if not extracted_text.strip():
            return {
                "success": True,
                "data": [],
                "message": "No text detected in image. Please upload a clearer screenshot."
            }

        # Step 2: Send extracted text to Groq for LLM processing
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise ValueError("GROQ_API_KEY not configured")

        client = Groq(api_key=groq_key)

        prompt = f"""You are a financial portfolio extraction expert. Analyze the provided text extracted from a portfolio screenshot and extract ALL stock holdings.

EXTRACTED TEXT:
{extracted_text}

TASK:
1. Identify all stock holdings (symbol, quantity, buy price)
2. Extract NSE stock symbols (e.g., HDFCBANK, INFY, RELIANCE)
3. Extract quantity and buy price for each holding

RULES:
- Use NSE stock symbols without .NS suffix
- Return ONLY a JSON array, no markdown, no extra text
- Symbol must be valid NSE symbol (uppercase)
- Qty must be a number (integer)
- buyPrice must be a number (can have decimals)
- If no portfolio data found, return: []

RESPONSE FORMAT:
[
  {{"symbol": "HDFCBANK", "qty": 100, "buyPrice": 1234.56}},
  {{"symbol": "ITC", "qty": 50, "buyPrice": 567.89}}
]

Extract all visible holdings. Be thorough - look for all occurrences of stock symbols, quantities, and prices."""

        logger.info("🤖 Sending extracted text to Groq LLM...")

        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",  # Robust text model (not vision)
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=2000
        )

        response_text = response.choices[0].message.content.strip()
        logger.info(f"🤖 LLM Response:\n{response_text}")

        # Step 3: Parse JSON response
        extracted_stocks = []
        try:
            # Try direct parsing
            extracted_stocks = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                try:
                    extracted_stocks = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse JSON from response: {response_text}")
                    extracted_stocks = []

        if not isinstance(extracted_stocks, list):
            extracted_stocks = []

        # Step 4: Validate and normalize
        validated_stocks = []
        for item in extracted_stocks:
            try:
                symbol = str(item.get("symbol", "")).upper().replace(".NS", "").replace(".BO", "").strip()
                qty_str = str(item.get("qty", 0)).replace(",", "").strip()
                price_str = str(item.get("buyPrice", 0)).replace(",", "").strip()

                qty = int(float(qty_str)) if qty_str else 0
                buy_price = float(price_str) if price_str else 0.0

                if symbol and qty > 0 and buy_price > 0:
                    validated_stocks.append({
                        "symbol": symbol,
                        "qty": qty,
                        "buyPrice": round(buy_price, 2)
                    })
                    logger.info(f"✓ Extracted: {symbol} x{qty} @ ₹{buy_price}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid item {item}: {e}")
                continue

        if not validated_stocks:
            return {
                "success": True,
                "data": [],
                "message": "No valid stock holdings found in the image. Please check if the screenshot clearly shows your portfolio with symbol, quantity, and price."
            }

        logger.info(f"✅ Successfully extracted {len(validated_stocks)} stocks")
        return {
            "success": True,
            "data": validated_stocks,
            "message": f"Successfully extracted {len(validated_stocks)} stocks from your portfolio image"
        }

    except Exception as e:
        logger.error(f"Portfolio extraction error: {e}", exc_info=True)
        error_msg = str(e)

        # More helpful error messages
        if "No such file or directory" in error_msg and "tesseract" in error_msg.lower():
            error_msg = "OCR library not installed. Please install tesseract-ocr on your system."
        elif "GROQ_API_KEY" in error_msg:
            error_msg = "Groq API key not configured on backend."

        return {
            "success": False,
            "error": error_msg,
            "message": "Failed to extract portfolio from image. " + error_msg
        }


@app.get("/api/stocks/cache/status")
async def cache_status():
    now = datetime.now()
    entries = []
    for symbol, entry in price_cache.items():
        age = (now - entry["cached_at"]).total_seconds()
        entries.append({
            "symbol":    symbol,
            "ageSecs":   int(age),
            "expiresIn": max(0, int(CACHE_TTL - age)),
            "valid":     age < CACHE_TTL,
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