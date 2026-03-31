import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Any, Optional, Tuple, cast
from datetime import datetime, timedelta
import pandas as pd
import logging
import time
from nsepython import nse_quote, nsefetch
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# ─────────────────────────────────────────
# SIMPLE ROUNDING (INLINE - NO IMPORTS)
# ─────────────────────────────────────────
def round_money(x):
    try:
        return round(float(x), 2)
    except (TypeError, ValueError):
        return 0.0

def round_percent(x):
    try:
        return round(float(x), 2)
    except (TypeError, ValueError):
        return 0.0

def round_price(x):
    try:
        return round(float(x), 2)
    except (TypeError, ValueError):
        return 0.0

def safe_divide(a, b):
    return (a / b) if b and b != 0 else 0.0

load_dotenv()

# ─────────────────────────────────────────
# App setup
# ─────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Portfolio API", version="6.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────
# Cache & Configuration
# ─────────────────────────────────────────
price_cache: Dict[str, Any] = {}
index_cache: Dict[str, Any] = {"data": {}, "updated_at": None}

CACHE_TTL = 60          # Fresh data
STALE_TTL = 300         # Stale fallback
INDEX_TTL = 300         # Nifty 500 cache TTL
executor = ThreadPoolExecutor(max_workers=50) # INCREASED WORKERS For parallelism

def get_from_cache(symbol: str) -> Tuple[Optional[Dict[str, Any]], bool]:
    """Returns (data, is_fresh)"""
    # 1. Check direct price cache
    if symbol in price_cache:
        cached_item = price_cache[symbol]
        age = (datetime.now() - cached_item["cached_at"]).total_seconds()
        if age < CACHE_TTL:
            return cached_item["data"], True
        elif age < STALE_TTL:
            return cached_item["data"], False

    # 2. Check Index Cache (Nifty 500)
    if symbol in index_cache["data"]:
        return index_cache["data"][symbol], True
        
    return None, False

def _nse_symbol(symbol: str) -> str:
    return symbol.upper().replace(".NS", "").replace(".BO", "").strip()

# ─────────────────────────────────────────
# BULK INDEX FETCHER (NEXT LEVEL SPEED)
# ─────────────────────────────────────────
def _refresh_index_cache(*args):
    """Fetches Nifty 500 data in ONE request"""
    try:
        url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500"
        payload = nsefetch(url)
        data = payload.get("data", [])
        if not data:
            return
            
        new_cache = {}
        for row in data:
            sym = row.get("symbol", "")
            if not sym: continue
            
            # Map from index fields to our standard format
            mapped = {
                "symbol": sym,
                "currentPrice": round_price(row.get("lastPrice", 0)),
                "dayHigh": round_price(row.get("dayHigh", 0)),
                "dayLow": round_price(row.get("dayLow", 0)),
                "high52w": round_price(row.get("yearHigh", 0)),
                "low52w": round_price(row.get("yearLow", 0)),
                "previousClose": round_price(row.get("previousClose", 0)),
                "change": round_percent(row.get("change", 0)),
                "changePercent": round_percent(row.get("pChange", 0)),
                "volume": row.get("totalTradedVolume", 0),
                "openPrice": round_price(row.get("open", 0)),
                "history": [], # Bulk doesn't have history
                "source": "NSE Nifty 500 Index",
                "error": False,
                "cachedAt": datetime.now().isoformat(),
            }
            new_cache[sym] = mapped
            # Also update main price cache for direct lookups
            if sym not in price_cache or (datetime.now() - price_cache[sym]["cached_at"]).total_seconds() > CACHE_TTL:
                price_cache[sym] = {"data": mapped, "cached_at": datetime.now()}
            
        index_cache["data"] = new_cache
        index_cache["updated_at"] = datetime.now()
        logger.info(f"Refreshed Nifty 500 Index Cache with {len(new_cache)} symbols")
    except Exception as e:
        logger.error(f"Failed to refresh index cache: {e}")

# ─────────────────────────────────────────
# FETCH LOGIC (PARALLEL)
# ─────────────────────────────────────────
def _get_single_stock_data(symbol: str) -> Optional[Dict]:
    """Fallback fetch for a single stock using nsepython"""
    nse_sym = _nse_symbol(symbol)
    try:
        # Quote
        url = f"https://www.nseindia.com/api/quote-equity?symbol={nse_sym}"
        data = nsefetch(url)
        
        price_info = data.get("priceInfo", {})
        if not price_info:
            return None

        intra = price_info.get("intraDayHighLow", {})
        week = price_info.get("weekHighLow", {})
        current = float(price_info.get("lastPrice", 0))
        prev_close = float(price_info.get("previousClose", 0))
        
        change = current - prev_close
        change_pct = safe_divide(change, prev_close) * 100.0

        # History (Limited to 30 days)
        history = []
        try:
            to_date = datetime.now()
            from_date = to_date - timedelta(days=40)
            hist_url = (
                f"https://www.nseindia.com/api/historical/cm/equity"
                f'?symbol={nse_sym}&series=["EQ","BE","ETF"]'
                f'&from={from_date.strftime("%d-%m-%Y")}'
                f'&to={to_date.strftime("%d-%m-%Y")}'
                f'&csv=false'
            )
            hist_data = nsefetch(hist_url)
            rows = hist_data.get("data", [])
            history = [
                {"date": row.get("CH_TIMESTAMP", ""), "close": float(row.get("CH_CLOSING_PRICE", 0))}
                for row in rows[-30:]
            ]
        except: pass

        result = {
            "symbol": symbol,
            "currentPrice": round_price(current),
            "dayHigh": round_price(intra.get("max", 0)),
            "dayLow": round_price(intra.get("min", 0)),
            "high52w": round_price(week.get("max", 0)),
            "low52w": round_price(week.get("min", 0)),
            "previousClose": round_price(prev_close),
            "change": round_percent(change),
            "changePercent": round_percent(change_pct),
            "volume": 0,
            "openPrice": round_price(price_info.get("open", 0)),
            "history": history,
            "source": "NSE India (Direct Fallback)",
            "error": False,
            "cachedAt": datetime.now().isoformat(),
        }
        
        price_cache[symbol] = {"data": result, "cached_at": datetime.now()}
        return result
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
        return None

async def get_stock_data_bulk(symbols: List[str]) -> Dict[str, Dict]:
    results = {}
    to_fetch = []
    
    # 1. Update Index Cache if empty or stale
    if not index_cache["updated_at"] or (datetime.now() - index_cache["updated_at"]).total_seconds() > INDEX_TTL:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, _refresh_index_cache)

    # 2. Check cache (Index + Price)
    for s in symbols:
        nse_s = _nse_symbol(s)
        data, is_fresh = get_from_cache(nse_s)
        if data:
            results[s] = data
            if not is_fresh:
                to_fetch.append(s)
        else:
            to_fetch.append(s)

    if not to_fetch:
        return results

    # 3. Parallel fetch missing/stale items (Fallback to 50 workers)
    loop = asyncio.get_event_loop()
    tasks = [loop.run_in_executor(executor, _get_single_stock_data, s) for s in to_fetch]
    
    if tasks:
        fetched_results = await asyncio.gather(*tasks)
        for i, s in enumerate(to_fetch):
            if fetched_results[i]:
                results[s] = fetched_results[i]
            elif s not in results:
                results[s] = _error_result(s, "Fetch failed after fallback")

    return results

def _error_result(symbol: str, msg: str) -> Dict:
    return {
        "symbol": symbol, "currentPrice": 0,
        "dayHigh": 0, "dayLow": 0, "high52w": 0, "low52w": 0,
        "previousClose": 0, "change": 0, "changePercent": 0, "volume": 0,
        "openPrice": 0, "history": [], "source": "ERROR", "error": True, "errorMsg": msg,
    }

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "version": "6.0.0", "index_size": len(index_cache["data"])}

@app.get("/api/stocks/quote")
async def get_quotes(symbols: str):
    if not symbols: raise HTTPException(status_code=400, detail="No symbols")
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    return await get_stock_data_bulk(symbol_list)

@app.post("/api/stocks/portfolio")
async def get_portfolio(data: Dict):
    portfolio = data.get("portfolio", [])
    if not portfolio: raise HTTPException(status_code=400, detail="No data")

    symbol_map = {h["symbol"]: h for h in portfolio}
    stock_data = await get_stock_data_bulk(list(symbol_map.keys()))

    results = []
    total_invested = 0
    total_value = 0

    for symbol, h in symbol_map.items():
        qty = float(h["qty"])
        buy = float(h["buyPrice"])
        current = float(stock_data.get(symbol, {}).get("currentPrice", 0))

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
        })

    total_pnl = total_value - total_invested
    return {
        "holdings": results,
        "summary": {
            "totalInvested": round_money(total_invested),
            "totalValue": round_money(total_value),
            "totalPnl": round_money(total_pnl),
            "totalPnlPercent": round_percent(safe_divide(total_pnl, total_invested) * 100),
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)