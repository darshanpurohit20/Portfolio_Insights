---
title: Portfolio Insights Backend
emoji: 🚀
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
pinned: true
---

# 📊 Portfolio Insights Backend

A fast and reliable Python backend for fetching real NSE stock prices using yfinance. Built with FastAPI, fully containerized, and deployed on Hugging Face Spaces.

**[Visit Live Backend →](https://huggingface.co/spaces/Darshanpurohit/Portfolio_Insight_backend/)**

---

## ✨ Features

- ✅ **Real-time NSE stock quotes** using yfinance
- 📈 **Historical price data** (1 year of daily prices)
- 💰 **Portfolio calculations** with P&L analysis
- 🚀 **FastAPI** with async support for high performance
- 🐳 **Docker-based deployment** on Hugging Face Spaces (serverless)
- 🔄 **15-minute intelligent caching** to reduce API calls
- 📊 **Complete stock analytics** (52W high/low, day range, volume)
- 🤗 **Zero infrastructure** management needed
- 🔀 **CORS enabled** for frontend integration

---

## 📋 API Endpoints

### Base URL
```
https://darshanpurohit-portfolio-insight-backend.hf.space
```

### 1. Get Stock Quotes
**`GET /api/stocks/quote`**

Fetch live stock quotes for NSE symbols.

**Query Parameters:**
- `symbols` (required): Comma-separated symbols (e.g., `HDFCBANK.NS,ITC.NS`)

**Example Request:**
```bash
curl "https://darshanpurohit-portfolio-insight-backend.hf.space/api/stocks/quote?symbols=HDFCBANK.NS,ITC.NS"
```

**Response:**
```json
{
  "HDFCBANK.NS": {
    "symbol": "HDFCBANK.NS",
    "currentPrice": 1700.5,
    "dayHigh": 1720.0,
    "dayLow": 1680.0,
    "high52w": 2100.0,
    "low52w": 1200.0,
    "previousClose": 1690.0,
    "change": 10.5,
    "changePercent": 0.62,
    "volume": 5250000,
    "openPrice": 1695.0,
    "history": [
      {"date": "2024-03-20", "close": 1700.5}
    ],
    "source": "Yahoo Finance",
    "error": false
  }
}
```

### 2. Health Check
**`GET /health`**

Check if the backend is running.

**Response:**
```json
{
  "status": "healthy",
  "backend": "ready"
}
```

### 3. Clear Cache
**`GET /api/stocks/cache/clear`**

Clear the in-memory price cache.

---

## 📁 Project Structure

```
backend/
├── main.py                 # FastAPI app with all endpoints
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker configuration
├── space.yaml             # Hugging Face Spaces config
├── .dockerignore           # Files to exclude from Docker
└── README.md              # This file
```

### Key Components

- **main.py**: FastAPI application with:
  - `get_stock_data()` - Fetches quotes from yfinance with retry logic
  - `/api/stocks/quote` - REST endpoint for stock quotes
  - `/health` - Health check endpoint
  - In-memory caching with 15-minute TTL

---

## 🚀 How to Run Locally

### 1. Clone the Repository
```bash
git clone https://github.com/darshanpurohit20/Portfolio_Insights.git
cd Portfolio_Insights/backend
```

### 2. Set Up Python Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run the Server
```bash
python main.py
```

Server will start at: `http://localhost:8000`

Test it:
```bash
curl "http://localhost:8000/api/stocks/quote?symbols=INFY.NS"
```

---

## ⚙️ Configuration

### For Frontend Integration

Update your Next.js frontend `.env` file:

```bash
# Use the live Hugging Face Spaces backend
NEXT_PUBLIC_BACKEND_URL=https://darshanpurohit-portfolio-insight-backend.hf.space

# OR for local development
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

### Backend Configuration

No environment variables required. The backend is fully self-contained.

---

## 🐳 Docker Deployment

### Build Locally
```bash
docker build -t portfolio-backend ./backend
docker run -p 8000:8000 portfolio-backend
```

### Using Docker Compose
```bash
docker-compose up backend
```

### Deploy to Hugging Face Spaces

1. Go to [Hugging Face Spaces](https://huggingface.co/spaces)
2. Create a new Space and select **Docker** SDK
3. Upload these files from `/backend`:
   - `Dockerfile`
   - `requirements.txt`
   - `main.py`
   - `space.yaml`
4. Hugging Face will auto-build and deploy!

---

## 📊 Performance Metrics

| Metric | Value |
|--------|-------|
| **First Request** | ~2-3 seconds (yfinance fetch) |
| **Cached Requests** | <50ms |
| **Cache TTL** | 15 minutes |
| **Max Concurrent Symbols** | 10+ per request |
| **Memory Baseline** | ~50MB |

---

## 🔧 Development

### Adding New Endpoints

1. Open `main.py`
2. Add your route using FastAPI decorators:
```python
@app.get("/api/new-endpoint")
async def new_endpoint():
    return {"message": "Hello"}
```
3. Reload the server (uvicorn auto-reloads in development)

### Monitoring

View server logs to see:
- Request timings
- Cache hits/misses
- Error details

---

## 🚨 Troubleshooting

| Problem | Solution |
|---------|----------|
| **"Connection refused"** | Check `NEXT_PUBLIC_BACKEND_URL` in frontend `.env` |
| **Slow first request** | Normal - yfinance is fetching. Subsequent requests cached. |
| **Symbol not found** | Ensure uppercase with `.NS` suffix (e.g., `HDFCBANK.NS`) |
| **Stale data** | Call `/api/stocks/cache/clear` to refresh |

---

## 📚 Example Valid Symbols

```
HDFCBANK.NS    - HDFC Bank
ITC.NS         - ITC Limited
INFY.NS        - Infosys
TCS.NS         - Tata Consultancy Services
RELIANCE.NS    - Reliance Industries
ADANIGREEN.NS  - Adani Green Energy
```

---

## 💡 Credits

Created with 💙 by **[Darshan Purohit](https://github.com/darshanpurohit20)**

[![GitHub - Darshan Purohit](https://img.shields.io/badge/GitHub-darshanpurohit20-blue?style=flat&logo=github)](https://github.com/darshanpurohit20)
[![Twitter - @darshanpurohit](https://img.shields.io/badge/Twitter-@darshanpurohit-blue?style=flat&logo=twitter)](https://twitter.com/darshanpurohit)

### Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Data**: yfinance (Yahoo Finance)
- **Deployment**: Docker + Hugging Face Spaces
- **Frontend**: Next.js + TypeScript

---

## 📄 License

MIT License - Feel free to use this backend in your projects!

---

**Made with ❤️ for the Indian stock market community**
