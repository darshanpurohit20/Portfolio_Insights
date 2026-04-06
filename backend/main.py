import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Any, Optional, Tuple, cast
from datetime import datetime, timedelta
import pandas as pd
import logging
import time
import os
from groq import Groq
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

app = FastAPI(title="Portfolio API", version="7.0.0")

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
sector_cache: Dict[str, str] = {} # symbol -> industry

CACHE_TTL = 60          # Fresh data
STALE_TTL = 300         # Stale fallback
INDEX_TTL = 3600        # Nifty 500 cache TTL (1 hour)
executor = ThreadPoolExecutor(max_workers=50)

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
    """Fetches Nifty 500 data and ranks by Market Cap"""
    try:
        url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500"
        payload = nsefetch(url)
        data = payload.get("data", [])
        if not data:
            return
            
        # Sort by Free Float Market Cap to determine Cap Type
        sorted_data = sorted(data, key=lambda x: x.get("ffmc", 0), reverse=True)
        
        new_cache = {}
        for i, row in enumerate(sorted_data):
            sym = row.get("symbol", "")
            if not sym: continue
            
            # Classification based on rank
            rank = i + 1
            if rank <= 100:
                cap_type = "Large Cap"
            elif rank <= 250:
                cap_type = "Mid Cap"
            else:
                cap_type = "Small Cap"

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
                "history": [],
                "source": "NSE Nifty 500 Index",
                "sector": "Other", # Will be patched if known
                "capType": cap_type,
                "error": False,
                "cachedAt": datetime.now().isoformat(),
            }
            new_cache[sym] = mapped
            
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
        # 1. Quote
        url = f"https://www.nseindia.com/api/quote-equity?symbol={nse_sym}"
        data = nsefetch(url)
        price_info = data.get("priceInfo", {})
        if not price_info:
            return None

        # 2. Industry Metadata (Cached for 1 day)
        sector = sector_cache.get(nse_sym, "Other")
        if sector == "Other":
            try:
                meta_url = f"https://www.nseindia.com/api/equity-meta-info?symbol={nse_sym}"
                meta = nsefetch(meta_url)
                industry = meta.get("industry", "Other")
                is_etf = meta.get("isETFSec", False)
                
                if is_etf or industry == "Mutual Fund Scheme":
                    sector = "ETFs & Mutual Funds"
                else:
                    sector = industry
                    
                sector_cache[nse_sym] = sector
            except: pass

        intra = price_info.get("intraDayHighLow", {})
        week = price_info.get("weekHighLow", {})
        current = float(price_info.get("lastPrice", 0))
        prev_close = float(price_info.get("previousClose", 0))
        
        change = current - prev_close
        change_pct = safe_divide(change, prev_close) * 100.0

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
            "history": [],
            "source": "NSE India (Direct Fallback)",
            "sector": sector,
            "capType": "Small Cap", # Fallback for non-index stocks
            "error": False,
            "cachedAt": datetime.now().isoformat(),
        }
        
        price_cache[symbol] = {"data": result, "cached_at": datetime.now()}
        return result
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
        return None

async def get_stock_data_bulk(symbols: List[str]) -> Dict[str, Any]:
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
            # Patch sector if missing from index cache (initially "Other")
            if data.get("sector") == "Other" and nse_s in sector_cache:
                data["sector"] = sector_cache[nse_s]
            results[s] = data
            if not is_fresh:
                to_fetch.append(s)
        else:
            to_fetch.append(s)

    if not to_fetch:
        return results

    # Parallel fetch missing/stale items
    loop = asyncio.get_event_loop()
    tasks = []
    for s in to_fetch:
        tasks.append(loop.run_in_executor(executor, _get_single_stock_data, s))
    
    # Also fetch industry for items in results that have "Other" sector (e.g. from index cache)
    for s, data in results.items():
        if data.get("sector") == "Other" and s not in [t for t in to_fetch]:
             tasks.append(loop.run_in_executor(executor, _get_single_stock_data, s))
    
    if tasks:
        fetched_results = await asyncio.gather(*tasks)
        for i, s in enumerate(to_fetch):
            if fetched_results[i]:
                results[s] = fetched_results[i]
            elif s not in results:
                results[s] = _error_result(s, "Fetch failed")

    return results

def _error_result(symbol: str, msg: str) -> Dict:
    return {
        "symbol": symbol, "currentPrice": 0,
        "dayHigh": 0, "dayLow": 0, "high52w": 0, "low52w": 0,
        "previousClose": 0, "change": 0, "changePercent": 0, "volume": 0,
        "openPrice": 0, "history": [], "source": "ERROR", "error": True, "errorMsg": msg,
        "sector": "Other", "capType": "Unknown"
    }

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "version": "7.0.0", "index_size": len(index_cache["data"])}

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
        s_data = stock_data.get(symbol, {})
        current = float(s_data.get("currentPrice", 0))

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

@app.post("/api/portfolio/extract")
async def extract_portfolio(payload: Dict):
    """
    Enhanced production endpoint for portfolio extraction.
    Includes comprehensive debugging for Hugging Face/Vercel environments.
    """
    import time
    import json
    import traceback
    from fastapi.responses import JSONResponse
    
    start_time = time.time()
    request_id = f"ocr_{int(start_time)}"
    
    # 1. Environment Debugging
    is_prod = os.environ.get("SPACE_ID") is not None
    api_key = os.environ.get("GROQ_API_KEY")
    has_key = api_key is not None and api_key != "your_groq_api_key_here"
    key_len = len(api_key) if api_key else 0
    
    logger.info(f"[{request_id}] >>> Extraction request received.")
    logger.info(f"[{request_id}] Context: env={'prod' if is_prod else 'local'}, has_api_key={has_key}, key_len={key_len}")

    # 2. Validate Input & Payload Size
    image_data = payload.get("image")
    if not image_data:
        logger.error(f"[{request_id}] FAILED: No image provided in request body")
        return JSONResponse(
            status_code=400,
            content={"error": True, "stage": "validation", "message": "Missing image data", "details": "Payload did not contain 'image' key."}
        )

    payload_size_kb = len(image_data) / 1024
    logger.info(f"[{request_id}] Payload size: {payload_size_kb:.2f} KB")

    if payload_size_kb > 8192: # 8MB limit
        logger.warning(f"[{request_id}] LARGE PAYLOAD: {payload_size_kb:.2f} KB detected.")

    # 3. Detect MIME Type accurately
    mime_type = "image/jpeg" 
    base64_image = image_data
    
    if "," in image_data:
        try:
            header, base64_image = image_data.split(",", 1)
            if "image/" in header:
                mime_type = header.split(":")[1].split(";")[0]
            logger.info(f"[{request_id}] Extracted MIME type: {mime_type}")
        except Exception as e:
            logger.warning(f"[{request_id}] MIME parse failed: {e}. Using fallback image/jpeg")

    # 4. API Key Verification
    if not has_key:
        logger.error(f"[{request_id}] CRITICAL: GROQ_API_KEY is missing or unconfigured.")
        return JSONResponse(
            status_code=401,
            content={
                "error": True,
                "stage": "auth_check",
                "message": "Groq API key not configured in environment",
                "details": "Ensure GROQ_API_KEY is set in Hugging Face Space secrets.",
                "is_production": is_prod
            }
        )

    # 5. Groq API Call with Timing & Safety
    try:
        client = Groq(api_key=api_key)
        
        prompt = """
        Analyze this stock portfolio screenshot and extract the holdings into a JSON array.
        For each holding, extract:
        - "symbol": The likely NSE stock symbol (e.g., RELIANCE, ITC, SBIN).
        - "qty": The number of shares owned as a number.
        - "buyPrice": The average buy price per share.
        
        IMPORTANT: Look for stock names like "ITC", "HDFC Bank", "Adani Green".
        Extract the quantity which is usually below or beside the name (e.g. "70 shares").
        
        CALCULATION RULE for buyPrice:
        If "Average Price" or "Avg Cost" is visible, use it.
        If NOT visible, look for "Last Price" and "P&L %" or "Returns %".
        Calculate: buyPrice = Last Price / (1 + (Returns % / 100)).
        
        Return ONLY a JSON object with the key "data" which is an array of these objects.
        Example: {"data": [{"symbol": "ITC", "qty": 100, "buyPrice": 450.50}]}
        """
        
        api_start_time = time.time()
        logger.info(f"[{request_id}] Calling Groq API (meta-llama/llama-4-scout)...")
        
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            response_format={"type": "json_object"},
            timeout=45.0 # Increased timeout for production stability
        )
        
        api_end_time = time.time()
        api_duration = api_end_time - api_start_time
        total_duration = api_end_time - start_time
        
        logger.info(f"[{request_id}] API SUCCESS: Response received in {api_duration:.2f}s")
        
        content = completion.choices[0].message.content
        result = json.loads(content)
        
        # Log summary of found stocks
        stocks_found = len(result.get("data", []))
        logger.info(f"[{request_id}] Done. Found {stocks_found} stocks. Total time: {total_duration:.2f}s")
        
        return {
            "success": True, 
            "data": result.get("data", []),
            "debug": {
                "api_time_sec": round(api_duration, 2),
                "total_time_sec": round(total_duration, 2),
                "payload_size_kb": round(payload_size_kb, 2),
                "mime": mime_type
            }
        }
        
    except Exception as e:
        total_duration = time.time() - start_time
        error_msg = str(e)
        logger.error(f"[{request_id}] API FAILURE after {total_duration:.2f}s: {error_msg}")
        logger.error(f"[{request_id}] Stacktrace: {traceback.format_exc()}")
        
        # Classify Error for easier debugging
        stage = "api_call"
        if "timeout" in error_msg.lower():
            stage = "api_timeout"
        elif "authentication" in error_msg.lower() or "401" in error_msg.lower():
            stage = "api_auth"
        elif "connection" in error_msg.lower() or "fetch" in error_msg.lower() or "httpx" in error_msg.lower():
            stage = "network_issue"

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "stage": stage,
                "message": f"Extraction failed: {error_msg}",
                "details": {
                    "request_id": request_id,
                    "payload_size_kb": round(payload_size_kb, 2),
                    "total_time_sec": round(total_duration, 2),
                    "is_production": is_prod,
                    "has_api_key": has_key
                }
            }
        )

# ─────────────────────────────────────────
# SCHEDULED REPORTS (APScheduler)
# ─────────────────────────────────────────
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import json
import report_generator
from fastapi import Response

REPORTS_FILE = os.path.join(os.path.dirname(__file__), "reports.json")

def load_reports():
    if os.path.exists(REPORTS_FILE):
        with open(REPORTS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_reports(data):
    with open(REPORTS_FILE, "w") as f:
        json.dump(data, f)

async def _job_send_scheduled_reports(frequency):
    logger.info(f"Running scheduled report job for frequency: {frequency}")
    reports = load_reports()
    for email, prefs in reports.items():
        if prefs.get("enabled") and prefs.get("frequency") == frequency:
            portfolio = prefs.get("portfolio", [])
            if not portfolio: continue
            
            # Fetch Live Prices
            symbols = [h["symbol"] for h in portfolio]
            stock_data = await get_stock_data_bulk(symbols)
            
            # Calculate summary
            portfolio_items = []
            total_invested = 0
            total_value = 0
            
            for h in portfolio:
                sym = h["symbol"]
                qty = float(h["qty"])
                buy = float(h["buyPrice"])
                s_data = stock_data.get(sym, {})
                current = float(s_data.get("currentPrice", 0))
                
                inv = qty * buy
                val = qty * current
                pnl = val - inv
                total_invested += inv
                total_value += val
                
                portfolio_items.append({
                    "symbol": sym, "qty": qty, "buyPrice": buy,
                    "currentPrice": current, "invested": inv,
                    "currentValue": val, "pnl": pnl,
                    "pnlPercent": (pnl / inv * 100) if inv else 0
                })
                
            total_pnl = total_value - total_invested
            summary_stats = {
                "totalInvested": total_invested,
                "totalValue": total_value,
                "totalPnl": total_pnl,
                "totalPnlPercent": (total_pnl / total_invested * 100) if total_invested else 0
            }
            
            # Generate and Send
            buffer = report_generator.generate_pdf_buffer(portfolio_items, summary_stats)
            report_generator.send_portfolio_email(email, buffer)

scheduler = AsyncIOScheduler()
scheduler.add_job(_job_send_scheduled_reports, 'cron', hour=18, minute=0, args=["Daily"], id="daily_reports", replace_existing=True)
scheduler.add_job(_job_send_scheduled_reports, 'cron', day_of_week='fri', hour=18, minute=0, args=["Weekly"], id="weekly_reports", replace_existing=True)
scheduler.add_job(_job_send_scheduled_reports, 'cron', day='last', hour=18, minute=0, args=["Monthly"], id="monthly_reports", replace_existing=True)

@app.on_event("startup")
async def start_scheduler():
    scheduler.start()
    logger.info("APScheduler started")

@app.on_event("shutdown")
async def shutdown_scheduler():
    scheduler.shutdown()

@app.post("/api/report/schedule")
async def schedule_report(data: Dict):
    email = data.get("email")
    if not email: raise HTTPException(status_code=400, detail="Missing email")
    
    reports = load_reports()
    reports[email] = {
        "enabled": data.get("enabled", False),
        "frequency": data.get("frequency", "Weekly"),
        "portfolio": data.get("portfolio", [])
    }
    save_reports(reports)
    return {"status": "success"}

@app.post("/api/report/generate")
async def generate_report(data: Dict):
    email = data.get("email")
    portfolio = data.get("portfolio", [])
    if not email or not portfolio:
        raise HTTPException(status_code=400, detail="Missing email or portfolio")
        
    total_invested = sum(item.get("invested", 0) for item in portfolio)
    total_value = sum(item.get("currentValue", 0) for item in portfolio)
    total_pnl = total_value - total_invested
    
    summary_stats = {
        "totalInvested": total_invested,
        "totalValue": total_value,
        "totalPnl": total_pnl,
        "totalPnlPercent": (total_pnl / total_invested * 100) if total_invested else 0
    }
    
    buffer = report_generator.generate_pdf_buffer(portfolio, summary_stats)
    return Response(content=buffer.read(), media_type="application/pdf")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)