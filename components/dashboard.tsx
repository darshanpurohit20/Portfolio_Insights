"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import useSWR from "swr"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { PortfolioSummary } from "@/components/portfolio-summary"
import { PortfolioTable } from "@/components/portfolio-table"
import { StockCards } from "@/components/stock-cards"
import { PortfolioOCR } from "@/components/portfolio-ocr"
import { AddStockDialog } from "@/components/add-stock-dialog"
import { PriceAlerts } from "@/components/price-alerts"
import { TrendingUp, Plus, LogOut, RefreshCw, LayoutGrid, TableIcon, FileSearch } from "lucide-react"
import type { PortfolioStock, PortfolioItem, PriceAlert } from "@/lib/types"

const STORAGE_KEY = "stockfolio-portfolio"
const ALERTS_KEY = "stockfolio-alerts"

function loadPortfolio(): PortfolioStock[] {
  if (typeof window === "undefined") return []
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function savePortfolio(stocks: PortfolioStock[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(stocks))
}

function loadAlerts(): PriceAlert[] {
  if (typeof window === "undefined") return []
  try {
    const raw = localStorage.getItem(ALERTS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveAlerts(alerts: PriceAlert[]) {
  localStorage.setItem(ALERTS_KEY, JSON.stringify(alerts))
}

const fetcher = (url: string) => fetch(url).then((r) => r.json())

export function Dashboard({ username }: { username: string }) {
  const router = useRouter()
  const [portfolio, setPortfolio] = useState<PortfolioStock[]>([])
  const [alerts, setAlerts] = useState<PriceAlert[]>([])
  const [addOpen, setAddOpen] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setPortfolio(loadPortfolio())
    setAlerts(loadAlerts())
    setMounted(true)
  }, [])

  const symbols = portfolio.map((s) => s.yfinSymbol).join(",")

  const { data: quotes, isLoading, mutate } = useSWR(
    symbols ? `/api/stocks/quote?symbols=${symbols}` : null,
    fetcher,
    { refreshInterval: 60000, revalidateOnFocus: true }
  )

  const portfolioItems: PortfolioItem[] = portfolio.map((stock) => {
    const q = quotes?.[stock.yfinSymbol] || {}
    const currentPrice = q.currentPrice || 0
    const invested = stock.qty * stock.buyPrice
    const currentValue = stock.qty * currentPrice
    const pnl = currentValue - invested

    return {
      ...stock,
      currentPrice,
      dayHigh: q.dayHigh || 0,
      dayLow: q.dayLow || 0,
      high52w: q.high52w || 0,
      low52w: q.low52w || 0,
      invested,
      currentValue,
      pnl,
      pnlPercent: invested ? (pnl / invested) * 100 : 0,
      dayHighValue: stock.qty * (q.dayHigh || 0),
      dayLowValue: stock.qty * (q.dayLow || 0),
      high52wValue: stock.qty * (q.high52w || 0),
      low52wValue: stock.qty * (q.low52w || 0),
      change: q.change || 0,
      changePercent: q.changePercent || 0,
      history: q.history || [],
    }
  })

  const checkAlerts = useCallback(() => {
    if (!quotes) return

    setAlerts((prev) => {
      let updated = false
      const newAlerts = prev.map((alert) => {
        if (!alert.active || alert.triggered) return alert
        const q = quotes[alert.symbol]
        if (!q) return alert

        const price = q.currentPrice
        const hit =
          (alert.condition === "above" && price >= alert.targetPrice) ||
          (alert.condition === "below" && price <= alert.targetPrice)

        if (hit) {
          updated = true
          toast.warning(`Alert: ${alert.name} is ${alert.condition} ${alert.targetPrice.toLocaleString("en-IN")}`, {
            description: `Current price: ${price.toLocaleString("en-IN")}`,
          })
          return { ...alert, triggered: true }
        }
        return alert
      })

      if (updated) saveAlerts(newAlerts)
      return updated ? newAlerts : prev
    })
  }, [quotes])

  useEffect(() => {
    checkAlerts()
  }, [checkAlerts])

  function addMultipleStocks(stocks: PortfolioStock[]) {
    const updated = [...portfolio, ...stocks]
    setPortfolio(updated)
    savePortfolio(updated)
  }

  function removeStock(id: string) {
    const stock = portfolio.find((s) => s.id === id)
    const updated = portfolio.filter((s) => s.id !== id)
    setPortfolio(updated)
    savePortfolio(updated)
    if (stock) toast.info(`Removed ${stock.name} from portfolio`)
  }

  function addAlert(alert: PriceAlert) {
    const updated = [...alerts, alert]
    setAlerts(updated)
    saveAlerts(updated)
    toast.success(`Alert set for ${alert.name}`)
  }

  function removeAlert(id: string) {
    const updated = alerts.filter((a) => a.id !== id)
    setAlerts(updated)
    saveAlerts(updated)
  }

  function toggleAlert(id: string) {
    const updated = alerts.map((a) =>
      a.id === id ? { ...a, active: !a.active, triggered: false } : a
    )
    setAlerts(updated)
    saveAlerts(updated)
  }

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" })
    router.push("/")
    router.refresh()
  }

  if (!mounted) return null

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <TrendingUp className="h-4 w-4 text-primary" />
            </div>
            <span className="text-lg font-bold text-foreground tracking-tight">StockFolio</span>
          </div>

          <div className="flex items-center gap-2">
            <PriceAlerts
              alerts={alerts}
              items={portfolioItems}
              onAddAlert={addAlert}
              onRemoveAlert={removeAlert}
              onToggleAlert={toggleAlert}
            />
            <Button
              variant="outline"
              size="icon"
              onClick={() => mutate()}
              disabled={isLoading}
              className="border-border text-foreground hover:bg-secondary"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
              <span className="sr-only">Refresh data</span>
            </Button>
            <span className="hidden text-sm text-muted-foreground sm:inline">{username}</span>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              className="text-muted-foreground hover:text-loss"
            >
              <LogOut className="h-4 w-4" />
              <span className="sr-only">Log out</span>
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6">
        <div className="flex flex-col gap-6">
          <PortfolioSummary items={portfolioItems} loading={isLoading && !quotes} />

          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-foreground">Holdings</h2>
            <Button
              onClick={() => setAddOpen(true)}
              className="bg-primary text-primary-foreground hover:bg-primary/90"
            >
              <Plus className="h-4 w-4 mr-1" />
              Add Stock
            </Button>
          </div>

          <Tabs defaultValue="table">
            <TabsList className="bg-secondary border border-border">
              <TabsTrigger value="table" className="data-[state=active]:bg-card data-[state=active]:text-foreground">
                <TableIcon className="h-3.5 w-3.5 mr-1" />
                Table
              </TabsTrigger>
              <TabsTrigger value="cards" className="data-[state=active]:bg-card data-[state=active]:text-foreground">
                <LayoutGrid className="h-3.5 w-3.5 mr-1" />
                Cards
              </TabsTrigger>
              <TabsTrigger value="ocr" className="data-[state=active]:bg-card data-[state=active]:text-foreground">
                <FileSearch className="h-3.5 w-3.5 mr-1" />
                AI Import
              </TabsTrigger>
            </TabsList>

            <TabsContent value="table" className="mt-4">
              <PortfolioTable
                items={portfolioItems}
                onRemove={removeStock}
                loading={isLoading && !quotes}
              />
            </TabsContent>

            <TabsContent value="cards" className="mt-4">
              <StockCards items={portfolioItems} onRemove={removeStock} />
            </TabsContent>

            <TabsContent value="ocr" className="mt-4">
              <PortfolioOCR onAddStocks={addMultipleStocks} />
            </TabsContent>
          </Tabs>
        </div>
      </main>

      <AddStockDialog open={addOpen} onOpenChange={setAddOpen} onAdd={addStock} />
    </div>
  )
}
