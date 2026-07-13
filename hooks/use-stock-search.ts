import { useEffect, useRef, useState } from "react"
import { NseStock, searchStocks as searchStaticStocks } from "@/lib/nse-stocks"

const DEBOUNCE_MS = 250
const MIN_QUERY_LENGTH = 1

interface LiveSearchResult {
  symbol: string
  name: string
  exchange: string
  quoteType: string
}

function toNseStock(r: LiveSearchResult): NseStock {
  return {
    symbol: r.symbol.replace(/\.(NS|BO)$/i, ""),
    name: r.name,
    yfinSymbol: r.symbol,
  }
}

/** Merge live results in front of static ones, de-duped by symbol. */
function mergeResults(live: NseStock[], fallback: NseStock[]): NseStock[] {
  const seen = new Set(live.map((s) => s.symbol.toUpperCase()))
  const rest = fallback.filter((s) => !seen.has(s.symbol.toUpperCase()))
  return [...live, ...rest].slice(0, 15)
}

/**
 * Stock search with instant first-paint from the static NSE_STOCKS list,
 * upgraded to live Yahoo Finance results once the debounced network call resolves.
 * Any backend/network failure silently keeps the static results — search never breaks.
 */
export function useStockSearch(query: string) {
  const [results, setResults] = useState<NseStock[]>(() => searchStaticStocks(query))
  const [isLive, setIsLive] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const requestIdRef = useRef(0)

  useEffect(() => {
    const staticResults = searchStaticStocks(query)

    // Instant paint from the static list, every keystroke
    setResults(staticResults)
    setIsLive(false)

    if (query.trim().length < MIN_QUERY_LENGTH) {
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    const currentRequestId = ++requestIdRef.current

    const timer = setTimeout(async () => {
      try {
        const res = await fetch(
          `/api/stocks/search?q=${encodeURIComponent(query)}`,
          { signal: AbortSignal.timeout(6000) }
        )
        if (!res.ok) throw new Error(`search failed: ${res.status}`)
        const data: { results?: LiveSearchResult[] } = await res.json()

        // Ignore stale responses if the user kept typing
        if (currentRequestId !== requestIdRef.current) return

        const live = (data.results ?? []).map(toNseStock)
        if (live.length > 0) {
          setResults(mergeResults(live, staticResults))
          setIsLive(true)
        }
        // If live search came back empty, just keep showing static results
      } catch {
        // Network error / timeout / backend down — static results stay on screen
        if (currentRequestId === requestIdRef.current) setIsLive(false)
      } finally {
        if (currentRequestId === requestIdRef.current) setIsLoading(false)
      }
    }, DEBOUNCE_MS)

    return () => clearTimeout(timer)
  }, [query])

  return { results, isLive, isLoading }
}