from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
from datetime import datetime, timedelta
import pandas as pd
import logging
import time

from nsepython import nse_quote, nsefetch
from dotenv import load_dotenv

# ─────────────────────────────────────────
# SIMPLE ROUNDING (INLINE - NO IMPORTS)
# ─────────────────────────────────────────
def round_money(x):
    return round(float(x), 2)

def round_percent(x):
    return round(float(x), 2)

def round_price(x):
    return round(float(x), 2)

def safe_divide(a, b):
    return (a / b) if b else 0.0

def calculate_scenario_value(qty, price, invested_per_unit=0):
    value = qty * price
    invested = qty * invested_per_unit
    pnl = value - invested
    pnl_pct = (pnl / invested * 100) if invested else 0.0

    return {
        "value": round_money(value),
        "pnl": round_money(pnl),
        "pnlPercent": round_percent(pnl_pct),
    }

load_dotenv()

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
# Cache
# ─────────────────────────────────────────
price_cache: Dict[str, Dict] = {}
CACHE_TTL = 60


def is_cache_valid(symbol: str) -> bool:
    if symbol not in price_cache:
        return False
    return (datetime.now() - price_cache[symbol]["cached_at"]).total_seconds() < CACHE_TTL


def _nse_symbol(symbol: str) -> str:
    return symbol.upper().replace(".NS", "").replace(".BO", "")

# ─────────────────────────────────────────
# FETCH QUOTE
# ─────────────────────────────────────────
def _fetch_quote(nse_sym: str) -> Dict:
    url = f"https://www.nseindia.com/api/quote-equity?symbol={nse_sym}"
    data = nsefetch(url)

    price_info = data.get("priceInfo", {})
    if not price_info:
        raise ValueError("No priceInfo returned")

    intra = price_info.get("intraDayHighLow", {})
    week = price_info.get("weekHighLow", {})

    current = float(price_info.get("lastPrice", 0))
    open_price = float(price_info.get("open", 0))
    prev_close = float(price_info.get("previousClose", 0))

    day_high = float(intra.get("max", 0))
    day_low = float(intra.get("min", 0))

    high_52w = float(week.get("max", 0))
    low_52w = float(week.get("min", 0))

    change = current - prev_close
    change_pct = safe_divide(change, prev_close) * 100.0

    return {
        "current": round_price(current),
        "open": round_price(open_price),
        "prevClose": round_price(prev_close),
        "dayHigh": round_price(day_high),
        "dayLow": round_price(day_low),
        "high52w": round_price(high_52w),
        "low52w": round_price(low_52w),
        "change": round_percent(change),
        "changePct": round_percent(change_pct),
    }

# ─────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────
def _fetch_history(nse_sym: str) -> List[Dict]:
    to_date = datetime.now()
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

        return [
            {
                "date": row.get("CH_TIMESTAMP", ""),
                "close": float(row.get("CH_CLOSING_PRICE", 0)),
            }
            for row in rows[-30:]
        ]
    except Exception:
        return []

# ─────────────────────────────────────────
# FETCH SINGLE
# ─────────────────────────────────────────
def fetch_single(symbol: str) -> Dict:
    nse_sym = _nse_symbol(symbol)

    try:
        quote = _fetch_quote(nse_sym)
        history = _fetch_history(nse_sym)

        result = {
            "symbol": symbol,
            "currentPrice": quote["current"],
            "dayHigh": quote["dayHigh"],
            "dayLow": quote["dayLow"],
            "high52w": quote["high52w"],
            "low52w": quote["low52w"],
            "previousClose": quote["prevClose"],
            "change": quote["change"],
            "changePercent": quote["changePct"],
            "volume": 0,
            "openPrice": quote["open"],
            "history": history,
            "source": "NSE India",
            "error": False,
            "cachedAt": datetime.now().isoformat(),
        }

        price_cache[symbol] = {"data": result, "cached_at": datetime.now()}
        return result

    except Exception as e:
        return _error_result(symbol, str(e))


def _error_result(symbol: str, msg: str) -> Dict:
    return {
        "symbol": symbol,
        "currentPrice": 0,
        "dayHigh": 0,
        "dayLow": 0,
        "high52w": 0,
        "low52w": 0,
        "previousClose": 0,
        "change": 0,
        "changePercent": 0,
        "volume": 0,
        "openPrice": 0,
        "history": [],
        "source": "ERROR",
        "error": True,
        "errorMsg": msg,
    }

# ─────────────────────────────────────────
# BULK FETCH
# ─────────────────────────────────────────
def get_stock_data_bulk(symbols: List[str]) -> Dict[str, Dict]:
    results = {}
    to_fetch = []

    for s in symbols:
        if is_cache_valid(s):
            results[s] = price_cache[s]["data"]
        else:
            to_fetch.append(s)

    for i, symbol in enumerate(to_fetch):
        results[symbol] = fetch_single(symbol)
        if i < len(to_fetch) - 1:
            time.sleep(0.3)

    return results

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok"}

@app.get("/api/stocks/quote")
async def get_quotes(symbols: str):
    if not symbols:
        raise HTTPException(status_code=400, detail="No symbols")

    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    return get_stock_data_bulk(symbol_list)

@app.post("/api/stocks/portfolio")
async def get_portfolio(data: Dict):
    portfolio = data.get("portfolio", [])
    if not portfolio:
        raise HTTPException(status_code=400, detail="No data")

    symbol_map = {h["symbol"]: h for h in portfolio}
    stock_data = get_stock_data_bulk(list(symbol_map.keys()))

    results = []
    total_invested = 0
    total_value = 0

    for symbol, h in symbol_map.items():
        qty = float(h["qty"])
        buy = float(h["buyPrice"])
        current = float(stock_data[symbol]["currentPrice"])

        invested = qty * buy
        value = qty * current
        pnl = value - invested
        pnl_pct = safe_divide(pnl, invested) * 100

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
            "pnlPercent": round_percent(pnl_pct),
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

# ─────────────────────────────────────────
# RUN
# ─────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)