import { NextRequest, NextResponse } from "next/server"

let yahooFinance: any = null
const priceCache = new Map<string, { data: any; timestamp: number }>()
const CACHE_DURATION = 60000 // 1 minute cache

async function initYahooFinance() {
  if (yahooFinance) return yahooFinance
  try {
    const module = await import("yahoo-finance2")
    yahooFinance = module.default || module
    return yahooFinance
  } catch (error) {
    console.error("Failed to load yahoo-finance2:", error)
    throw error
  }
}

// Add delay between requests to avoid rate limiting
function delay(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function fetchStockData(yf: any, symbol: string) {
  // Check cache first
  const cached = priceCache.get(symbol)
  if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
    console.log(`[${symbol}] Returning cached data`)
    return cached.data
  }

  try {
    // Add 1-second delay between requests to avoid rate limiting
    await delay(1000)

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
    console.log(`[${symbol}] Price: ${result.currentPrice}`)
    return result
  } catch (err) {
    console.error(`Error fetching ${symbol}:`, err)
    return {
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
      errorMsg: (err as any)?.message,
    }
  }
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

    // Process requests sequentially with delays to avoid rate limiting
    for (const symbol of symbolList) {
      results[symbol] = await fetchStockData(yf, symbol)
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
