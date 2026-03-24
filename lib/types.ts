export interface PortfolioStock {
  id: string
  symbol: string
  yfinSymbol: string
  name: string
  qty: number
  buyPrice: number
}

export interface StockQuote {
  symbol: string
  name: string
  currentPrice: number
  dayHigh: number
  dayLow: number
  high52w: number
  low52w: number
  previousClose: number
  change: number
  changePercent: number
  history: { date: string; close: number }[]
}

export interface PortfolioItem extends PortfolioStock {
  currentPrice: number
  dayHigh: number
  dayLow: number
  high52w: number
  low52w: number
  invested: number
  currentValue: number
  pnl: number
  pnlPercent: number
  dayHighValue: number
  dayLowValue: number
  high52wValue: number
  low52wValue: number
  change: number
  changePercent: number
  history: { date: string; close: number }[]
}

export interface PriceAlert {
  id: string
  symbol: string
  name: string
  targetPrice: number
  condition: "above" | "below"
  active: boolean
  triggered: boolean
}
