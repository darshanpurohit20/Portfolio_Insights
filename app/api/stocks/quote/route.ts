import { NextRequest, NextResponse } from "next/server"

let yahooFinance: any = null
const priceCache = new Map<string, { data: any; timestamp: number }>()
const CACHE_DURATION = 5 * 60000 // 5 minute cache

async function initYahooFinance() {
  if (yahooFinance) return yahooFinance
  try {
    const module = await import("yahoo-finance2")
    yahooFinance = module.default || module
    // Suppress the survey notice
    yahooFinance.suppressNotices(['yahooSurvey'])
    return yahooFinance
  } catch (error) {
    console.error("Failed to load yahoo-finance2:", error)
    throw error
  }
}

function delay(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// Generate mock historical data
function generateMockHistory(basePrice: number, volatility: number) {
  const history = []
  let price = basePrice
  for (let i = 30; i >= 0; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i)
    const change = (Math.random() - 0.5) * volatility
    price = price + change
    history.push({
      date: date.toISOString().split("T")[0],
      close: parseFloat(price.toFixed(2)),
    })
  }
  return history
}

// Fallback mock data for development when rate limited
const mockStockData: Record<string, any> = {
  "ITC.NS": {
    symbol: "ITC.NS",
    currentPrice: 290.50,
    dayHigh: 295.00,
    dayLow: 285.00,
    high52w: 450.00,
    low52w: 200.00,
    previousClose: 288.00,
    change: 2.50,
    changePercent: 0.87,
    history: generateMockHistory(290.50, 3)
  },
  "ADANIGREEN.NS": {
    symbol: "ADANIGREEN.NS",
    currentPrice: 815.00,
    dayHigh: 825.00,
    dayLow: 800.00,
    high52w: 1200.00,
    low52w: 600.00,
    previousClose: 810.00,
    change: 5.00,
    changePercent: 0.62,
    history: generateMockHistory(815.00, 20)
  },
  "HDFCBANK.NS": {
    symbol: "HDFCBANK.NS",
    currentPrice: 1700.00,
    dayHigh: 1720.00,
    dayLow: 1680.00,
    high52w: 2100.00,
    low52w: 1200.00,
    previousClose: 1690.00,
    change: 10.00,
    changePercent: 0.59,
    history: generateMockHistory(1700.00, 15)
  },
  "BANKBETA.NS": {
    symbol: "BANKBETA.NS",
    currentPrice: 53.00,
    dayHigh: 54.00,
    dayLow: 52.00,
    high52w: 70.00,
    low52w: 40.00,
    previousClose: 52.50,
    change: 0.50,
    changePercent: 0.95,
    history: generateMockHistory(53.00, 1.5)
  },
  "MAZDOCK.NS": {
    symbol: "MAZDOCK.NS",
    currentPrice: 2200.00,
    dayHigh: 2250.00,
    dayLow: 2150.00,
    high52w: 3000.00,
    low52w: 1500.00,
    previousClose: 2180.00,
    change: 20.00,
    changePercent: 0.92,
    history: generateMockHistory(2200.00, 30)
  },
  "GROWWNIFTY.NS": {
    symbol: "GROWWNIFTY.NS",
    currentPrice: 9.00,
    dayHigh: 9.20,
    dayLow: 8.80,
    high52w: 12.00,
    low52w: 6.00,
    previousClose: 8.95,
    change: 0.05,
    changePercent: 0.56,
    history: generateMockHistory(9.00, 0.3)
  },
  "EXCELSOFT.NS": {
    symbol: "EXCELSOFT.NS",
    currentPrice: 72.00,
    dayHigh: 74.00,
    dayLow: 70.00,
    high52w: 120.00,
    low52w: 40.00,
    previousClose: 71.00,
    change: 1.00,
    changePercent: 1.41,
    history: generateMockHistory(72.00, 2)
  },
  "BANDHANBNK.NS": {
    symbol: "BANDHANBNK.NS",
    currentPrice: 148.00,
    dayHigh: 152.00,
    dayLow: 145.00,
    high52w: 250.00,
    low52w: 80.00,
    previousClose: 147.00,
    change: 1.00,
    changePercent: 0.68,
    history: generateMockHistory(148.00, 4)
  }
}

async function fetchStockDataWithRetry(yf: any, symbol: string, retries = 2): Promise<any> {
  // Check cache first
  const cached = priceCache.get(symbol)
  if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
    console.log(`[${symbol}] Returning cached data`)
    return cached.data
  }

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      // Exponential backoff: 2s, 4s, 6s
      if (attempt > 0) {
        const backoffTime = 2000 * (attempt + 1)
        console.log(`[${symbol}] Retry attempt ${attempt}, waiting ${backoffTime}ms...`)
        await delay(backoffTime)
      } else {
        // Initial 2-second delay between requests
        await delay(2000)
      }

      const [quote, history] = await Promise.all([
        yf.quote(symbol),
        yf.chart(symbol, {
          period1: new Date(
            Date.now() - 365 * 24 * 60 * 60 * 1000
          ).toISOString().split("T")[0],
          interval: "1d",
        }),
      ])

      const historyData = (history?.quotes || [])
        .filter((q: { close?: number | null }) => q.close != null)
        .map((q: { date: Date; close?: number | null }) => ({
          date: q.date.toISOString().split("T")[0],
          close: q.close,
        }))

      const result = {
        symbol,
        currentPrice: quote?.regularMarketPrice || 0,
        dayHigh: quote?.regularMarketDayHigh || 0,
        dayLow: quote?.regularMarketDayLow || 0,
        high52w: quote?.fiftyTwoWeekHigh || 0,
        low52w: quote?.fiftyTwoWeekLow || 0,
        previousClose: quote?.regularMarketPreviousClose || 0,
        change: quote?.regularMarketChange || 0,
        changePercent: quote?.regularMarketChangePercent || 0,
        history: historyData,
      }

      // Cache successful result
      priceCache.set(symbol, { data: result, timestamp: Date.now() })
      console.log(`[${symbol}] Success: ₹${result.currentPrice}`)
      return result
    } catch (err: any) {
      const errorMsg = (err as any)?.message || String(err)
      
      // Check if it's a rate limit error
      if (errorMsg.includes("Too Many Requests") && attempt < retries) {
        console.log(`[${symbol}] Rate limited, retrying...`)
        continue
      }
      
      // If all retries failed, use mock data as fallback
      if (attempt === retries) {
        console.warn(`[${symbol}] All retries failed, using mock data. Error: ${errorMsg}`)
        const mockData = mockStockData[symbol] || {
          symbol,
          currentPrice: 0,
          dayHigh: 0,
          dayLow: 0,
          high52w: 0,
          low52w: 0,
          previousClose: 0,
          change: 0,
          changePercent: 0,
          history: [],
          error: true,
          errorMsg: errorMsg,
          mock: true
        }
        
        // Cache mock data too
        priceCache.set(symbol, { data: mockData, timestamp: Date.now() })
        return mockData
      }
    }
  }

  // Fallback (shouldn't reach here)
  return mockStockData[symbol] || { symbol, currentPrice: 0, error: true }
}

export async function GET(req: NextRequest) {
  try {
    const symbols = req.nextUrl.searchParams.get("symbols")
    if (!symbols) {
      return NextResponse.json({ error: "No symbols provided" }, { status: 400 })
    }

    const yf = await initYahooFinance()
    const symbolList = symbols.split(",").map((s) => s.trim())
    const results: Record<string, unknown> = {}

    // Process requests sequentially with longer delays and retries
    for (const symbol of symbolList) {
      results[symbol] = await fetchStockDataWithRetry(yf, symbol)
    }

    return NextResponse.json(results)
  } catch (error: any) {
    console.error("API Error:", error)
    return NextResponse.json(
      { error: "Failed to fetch stock data", message: error?.message },
      { status: 500 }
    )
  }
}
