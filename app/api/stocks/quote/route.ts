import { NextRequest, NextResponse } from "next/server"
const yahooFinance = require("yahoo-finance2").default

export async function GET(req: NextRequest) {
  const symbols = req.nextUrl.searchParams.get("symbols")
  if (!symbols) {
    return NextResponse.json({ error: "No symbols provided" }, { status: 400 })
  }

  const symbolList = symbols.split(",").map((s) => s.trim())
  const results: Record<string, unknown> = {}

  await Promise.all(
    symbolList.map(async (symbol) => {
      try {
        const [quote, history] = await Promise.all([
          yahooFinance.quote(symbol),
          yahooFinance.chart(symbol, {
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

        results[symbol] = {
          symbol,
          currentPrice: quote.regularMarketPrice || 0,
          dayHigh: quote.regularMarketDayHigh || 0,
          dayLow: quote.regularMarketDayLow || 0,
          high52w: quote.fiftyTwoWeekHigh || 0,
          low52w: quote.fiftyTwoWeekLow || 0,
          previousClose: quote.regularMarketPreviousClose || 0,
          change: quote.regularMarketChange || 0,
          changePercent: quote.regularMarketChangePercent || 0,
          history: historyData,
        }
      } catch (err) {
        console.error(`Error fetching ${symbol}:`, err)
        results[symbol] = {
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
        }
      }
    })
  )

  return NextResponse.json(results)
}
