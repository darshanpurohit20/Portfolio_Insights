from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Portfolio API", version="1.0.0")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for stock prices (TTL: 15 minutes)
price_cache: Dict = {}
CACHE_TTL = 15 * 60  # 15 minutes in seconds


def is_cache_valid(symbol: str) -> bool:
    """Check if cached data is still valid"""
    if symbol not in price_cache:
        return False
    cached_at = price_cache[symbol].get("cached_at")
    if cached_at is None:
        return False
    elapsed = (datetime.now() - cached_at).total_seconds()
    return elapsed < CACHE_TTL


def get_stock_data(symbol: str) -> Dict:
    """
    Fetch stock data from yfinance
    Returns: {
        currentPrice, dayHigh, dayLow, previousClose, change, changePercent,
        high52w, low52w, volume, openPrice, history
    }
    """
    try:
        logger.info(f"Fetching data for {symbol}...")
        
        # Check cache first
        if is_cache_valid(symbol):
            logger.info(f"[{symbol}] Using cached data")
            return price_cache[symbol]["data"]
        
        # Fetch current quote and 1 year history
        ticker = yf.Ticker(symbol)
        
        # Get current data
        info = ticker.info
        hist = ticker.history(period="1y")
        
        if hist.empty:
            raise ValueError(f"No historical data found for {symbol}")
        
        # Get latest day data
        latest = hist.iloc[-1]
        previous = hist.iloc[-2] if len(hist) > 1 else latest
        
        current_price = float(latest["Close"])
        day_high = float(latest["High"])
        day_low = float(latest["Low"])
        previous_close = float(previous["Close"])
        
        change = current_price - previous_close
        change_percent = (change / previous_close * 100) if previous_close > 0 else 0
        
        # 52-week high/low
        high_52w = float(hist["High"].max())
        low_52w = float(hist["Low"].min())
        
        # Prepare history data for charts
        history_data = []
        for date, row in hist.tail(30).iterrows():  # Last 30 days
            history_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "close": float(row["Close"])
            })
        
        result = {
            "symbol": symbol,
            "currentPrice": current_price,
            "dayHigh": day_high,
            "dayLow": day_low,
            "high52w": high_52w,
            "low52w": low_52w,
            "previousClose": previous_close,
            "change": change,
            "changePercent": change_percent,
            "volume": int(latest.get("Volume", 0)),
            "openPrice": float(latest.get("Open", 0)),
            "history": history_data,
            "source": "Yahoo Finance",
            "error": False,
        }
        
        # Cache the result
        price_cache[symbol] = {
            "data": result,
            "cached_at": datetime.now()
        }
        
        logger.info(f"[{symbol}] ✓ Success: ₹{current_price:.2f} ({change_percent:+.2f}%)")
        return result
        
    except Exception as e:
        logger.error(f"[{symbol}] Error: {str(e)}")
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
            "errorMsg": str(e),
        }


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Portfolio API is running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Try a quick yfinance fetch to verify connectivity
        test = yf.Ticker("INFY.NS")
        test.info
        return {"status": "healthy", "backend": "ready"}
    except Exception as e:
        return {"status": "degraded", "error": str(e)}, 503


@app.get("/api/stocks/quote")
async def get_quotes(symbols: str):
    """
    Fetch stock quotes for given symbols
    Query params: symbols=SYMBOL1,SYMBOL2,SYMBOL3
    
    Example: /api/stocks/quote?symbols=HDFCBANK.NS,ITC.NS,ADANIGREEN.NS
    """
    try:
        if not symbols:
            raise HTTPException(status_code=400, detail="No symbols provided")
        
        symbol_list = [s.strip() for s in symbols.split(",")]
        logger.info(f"\n📊 Fetching {len(symbol_list)} symbols...")
        
        results = {}
        for symbol in symbol_list:
            results[symbol] = get_stock_data(symbol)
        
        logger.info(f"✅ All {len(symbol_list)} symbols processed\n")
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stocks/portfolio")
async def get_portfolio(data: Dict):
    """
    Get complete portfolio data with all calculations
    Body: {
        "portfolio": [
            {"symbol": "HDFCBANK.NS", "qty": 75, "buyPrice": 746.41},
            ...
        ]
    }
    """
    try:
        portfolio = data.get("portfolio", [])
        if not portfolio:
            raise HTTPException(status_code=400, detail="No portfolio data provided")
        
        results = []
        total_invested = 0
        total_value = 0
        
        for holding in portfolio:
            symbol = holding.get("symbol")
            qty = holding.get("qty", 0)
            buy_price = holding.get("buyPrice", 0)
            
            stock_data = get_stock_data(symbol)
            current_price = stock_data.get("currentPrice", 0)
            
            invested = qty * buy_price
            current_value = qty * current_price
            pnl = current_value - invested
            pnl_percent = (pnl / invested * 100) if invested > 0 else 0
            
            total_invested += invested
            total_value += current_value
            
            results.append({
                **stock_data,
                "qty": qty,
                "buyPrice": buy_price,
                "invested": invested,
                "currentValue": current_value,
                "pnl": pnl,
                "pnlPercent": pnl_percent,
            })
        
        total_pnl = total_value - total_invested
        total_pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        return {
            "holdings": results,
            "summary": {
                "totalInvested": total_invested,
                "totalValue": total_value,
                "totalPnl": total_pnl,
                "totalPnlPercent": total_pnl_percent,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Portfolio API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks/cache/clear")
async def clear_cache():
    """Clear the price cache"""
    global price_cache
    cache_size = len(price_cache)
    price_cache = {}
    return {"message": f"Cache cleared, removed {cache_size} entries"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
