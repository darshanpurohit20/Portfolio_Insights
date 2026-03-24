# Portfolio Insights - Backend (Python/FastAPI)

A fast and reliable Python backend for fetching real NSE stock prices using yfinance.

## Live Demo

🚀 **[Try on Hugging Face Spaces](https://huggingface.co/spaces/Darshanpurohit/Portfolio_Insight_backend/)**

## Features

- ✅ Real-time NSE stock quotes using yfinance
- 📈 Historical price data (1 year)
- 💰 Portfolio calculations with P&L
- 🚀 FastAPI with async support
- 🐳 Docker & Docker Compose ready
- 🔄 15-minute price caching
- 📊 Complete stock analytics
- 🤗 Deployed on Hugging Face Spaces

## Quick Start

### Option 1: Local Development

1. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

2. **Run the server:**
```bash
python main.py
```

The API will be available at `http://localhost:8000`

3. **Check health:**
```bash
curl http://localhost:8000/health
```

### Option 2: Docker

1. **Build and run:**
```bash
docker build -t portfolio-backend ./backend
docker run -p 8000:8000 portfolio-backend
```

2. **Or use Docker Compose (from project root):**
```bash
docker-compose up backend
```

## API Endpoints

### GET `/api/stocks/quote`
Fetch stock quotes for given symbols

**Query Parameters:**
- `symbols`: Comma-separated list of symbols (e.g., `HDFCBANK.NS,ITC.NS,ADANIGREEN.NS`)

**Example:**
```bash
curl "http://localhost:8000/api/stocks/quote?symbols=HDFCBANK.NS,ITC.NS"
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
      {"date": "2024-03-20", "close": 1700.5},
      ...
    ],
    "source": "Yahoo Finance",
    "error": false
  }
}
```

### GET `/health`
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "backend": "ready"
}
```

### GET `/api/stocks/cache/clear`
Clear the price cache

## Environment Variables

Create a `.env` file (optional for local development):
```bash
# No environment variables required for basic operation
# Backend runs on port 8000 by default
```

## Requirements

- Python 3.11+
- See `requirements.txt` for dependencies

## Development

### Adding new endpoints

1. Edit `main.py`
2. Use the `get_stock_data()` function for fetching prices
3. Reload the server (uvicorn will auto-reload in development)

### Monitoring

Server logs will show:
- Request processing time
- Cache hits/misses
- Data fetch success/failures
- Detailed error messages

## Deployment

### Hugging Face Spaces

The backend is live on Hugging Face Spaces! Access it here:
**https://huggingface.co/spaces/Darshanpurohit/Portfolio_Insight_backend/**

**Space Configuration (space.yaml):**
```yaml
---
title: Portfolio Insights Backend
emoji: 🚀
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
pinned: true
---
```

To deploy your own instance on Hugging Face Spaces:
1. Create a new Space on [Hugging Face](https://huggingface.co/spaces)
2. Select "Docker" as SDK
3. Upload the `Dockerfile` and `requirements.txt`
4. Space will automatically build and deploy

### Heroku
```bash
git push heroku main
```

### AWS (Docker):
```bash
aws ecr get-login-password | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
docker tag portfolio-backend:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/portfolio-backend:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/portfolio-backend:latest
```

### Google Cloud Run
```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/portfolio-backend
gcloud run deploy portfolio-backend --image gcr.io/$PROJECT_ID/portfolio-backend --platform managed
```

## Frontend Integration

The Next.js frontend calls this backend via:
```
GET /api/stocks/quote?symbols=...
```

Configure the backend URL in `.env`:
```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

## Performance

- **First request:** ~2-3 seconds (fetches from yfinance)
- **Cached requests:** <50ms (from in-memory cache, TTL: 15 minutes)
- **Concurrent symbols:** Handles up to 10+ symbols per request efficiently
- **Memory usage:** ~50MB baseline, grows with cache size

## Troubleshooting

### "Connection refused" from frontend
- Ensure backend is running on port 8000
- Check `NEXT_PUBLIC_BACKEND_URL` in frontend `.env`
- Verify CORS is enabled (it is by default)

### "No historical data found for symbol"
- Symbol may not exist or be delisted
- Check spelling (should be uppercase with `.NS` suffix for NSE)
- Example valid symbols: `HDFCBANK.NS`, `ITC.NS`, `ADANIGREEN.NS`

### Slow responses on first request
- yfinance needs to fetch data from Yahoo Finance
- This is normal, subsequent requests use cache
- Cache TTL is 15 minutes by default

### Data not updating
- Clear cache: `GET /api/stocks/cache/clear`
- Or wait for 15-minute cache expiration

## License

MIT
