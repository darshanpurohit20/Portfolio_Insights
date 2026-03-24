"use client"

import { useState, useEffect, useCallback } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Search, Plus } from "lucide-react"
import type { NseStock } from "@/lib/nse-stocks"
import type { PortfolioStock } from "@/lib/types"

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAdd: (stock: PortfolioStock) => void
}

export function AddStockDialog({ open, onOpenChange, onAdd }: Props) {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<NseStock[]>([])
  const [selected, setSelected] = useState<NseStock | null>(null)
  const [qty, setQty] = useState("")
  const [buyPrice, setBuyPrice] = useState("")
  const [searching, setSearching] = useState(false)

  const searchStocks = useCallback(async (q: string) => {
    if (q.length < 1) {
      setResults([])
      return
    }
    setSearching(true)
    try {
      const res = await fetch(`/api/stocks/search?q=${encodeURIComponent(q)}`)
      const data = await res.json()
      setResults(data)
    } catch {
      setResults([])
    } finally {
      setSearching(false)
    }
  }, [])

  useEffect(() => {
    const timer = setTimeout(() => searchStocks(query), 300)
    return () => clearTimeout(timer)
  }, [query, searchStocks])

  function handleSelect(stock: NseStock) {
    setSelected(stock)
    setQuery(stock.name)
    setResults([])
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!selected || !qty || !buyPrice) return

    onAdd({
      id: `${selected.yfinSymbol}-${Date.now()}`,
      symbol: selected.symbol,
      yfinSymbol: selected.yfinSymbol,
      name: selected.name,
      qty: parseInt(qty),
      buyPrice: parseFloat(buyPrice),
    })

    setQuery("")
    setSelected(null)
    setQty("")
    setBuyPrice("")
    onOpenChange(false)
  }

  function reset() {
    setQuery("")
    setSelected(null)
    setQty("")
    setBuyPrice("")
    setResults([])
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) reset()
        onOpenChange(v)
      }}
    >
      <DialogContent className="bg-card border-border">
        <DialogHeader>
          <DialogTitle className="text-foreground">Add Stock</DialogTitle>
          <DialogDescription>
            Search by stock name or NSE symbol. Auto-maps to Yahoo Finance format.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label className="text-foreground">Search Stock</Label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value)
                  setSelected(null)
                }}
                placeholder="e.g., TCS, Reliance, HDFC..."
                className="pl-10 bg-secondary text-foreground border-border"
              />
            </div>

            {results.length > 0 && !selected && (
              <div className="max-h-48 overflow-y-auto rounded-lg border border-border bg-secondary">
                {results.map((stock) => (
                  <button
                    key={stock.yfinSymbol}
                    type="button"
                    onClick={() => handleSelect(stock)}
                    className="flex w-full items-center justify-between px-3 py-2 text-left hover:bg-accent/10 transition-colors"
                  >
                    <div>
                      <span className="text-sm font-medium text-foreground">{stock.name}</span>
                      <span className="ml-2 text-xs text-muted-foreground">{stock.symbol}</span>
                    </div>
                    <span className="text-xs text-primary font-mono">{stock.yfinSymbol}</span>
                  </button>
                ))}
              </div>
            )}

            {searching && (
              <p className="text-xs text-muted-foreground">Searching...</p>
            )}

            {selected && (
              <div className="flex items-center gap-2 rounded-md bg-primary/10 px-3 py-2">
                <span className="text-sm font-medium text-primary">{selected.name}</span>
                <span className="text-xs text-muted-foreground">({selected.yfinSymbol})</span>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="ml-auto h-5 w-5 text-muted-foreground"
                  onClick={() => {
                    setSelected(null)
                    setQuery("")
                  }}
                >
                  x
                </Button>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-2">
              <Label className="text-foreground">Quantity</Label>
              <Input
                type="number"
                min="1"
                value={qty}
                onChange={(e) => setQty(e.target.value)}
                placeholder="e.g., 10"
                className="bg-secondary text-foreground border-border"
                required
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label className="text-foreground">Buy Price</Label>
              <Input
                type="number"
                min="0.01"
                step="0.01"
                value={buyPrice}
                onChange={(e) => setBuyPrice(e.target.value)}
                placeholder="e.g., 3500"
                className="bg-secondary text-foreground border-border"
                required
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              type="submit"
              disabled={!selected || !qty || !buyPrice}
              className="bg-primary text-primary-foreground hover:bg-primary/90"
            >
              <Plus className="h-4 w-4 mr-1" />
              Add to Portfolio
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
