"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Sparkline } from "@/components/sparkline"
import { Trash2 } from "lucide-react"
import type { PortfolioItem } from "@/lib/types"

function formatINR(value: number): string {
  return value.toLocaleString("en-IN", { maximumFractionDigits: 2 })
}

interface Props {
  items: PortfolioItem[]
  onRemove: (id: string) => void
}

export function StockCards({ items, onRemove }: Props) {
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-border bg-card p-12">
        <p className="text-lg font-medium text-muted-foreground">No stocks in your portfolio</p>
        <p className="text-sm text-muted-foreground mt-1">
          Add stocks using the button above to get started.
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => {
        const dayRange =
          item.dayHigh !== item.dayLow
            ? ((item.currentPrice - item.dayLow) / (item.dayHigh - item.dayLow)) * 100
            : 50
        const range52w =
          item.high52w !== item.low52w
            ? ((item.currentPrice - item.low52w) / (item.high52w - item.low52w)) * 100
            : 50

        return (
          <Card key={item.id} className="border-border bg-card overflow-hidden">
            <CardContent className="p-0">
              <div className="flex items-start justify-between p-4 pb-2">
                <div>
                  <h3 className="font-semibold text-foreground text-sm">{item.name}</h3>
                  <p className="text-xs text-muted-foreground">{item.symbol} &middot; Qty: {item.qty}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge
                    className={
                      item.pnl >= 0
                        ? "bg-profit/15 text-profit border-profit/20"
                        : "bg-loss/15 text-loss border-loss/20"
                    }
                  >
                    {item.pnlPercent >= 0 ? "+" : ""}{item.pnlPercent.toFixed(2)}%
                  </Badge>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-muted-foreground hover:text-loss"
                    onClick={() => onRemove(item.id)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>

              <div className="px-4 h-16">
                <Sparkline data={item.history} profit={item.pnl >= 0} height={64} />
              </div>

              <div className="grid grid-cols-3 gap-0 border-t border-border mt-2">
                <div className="flex flex-col items-center border-r border-border px-3 py-2.5">
                  <span className="text-[10px] text-muted-foreground uppercase">CMP</span>
                  <span className="text-sm font-semibold tabular-nums text-foreground">
                    {formatINR(item.currentPrice)}
                  </span>
                </div>
                <div className="flex flex-col items-center border-r border-border px-3 py-2.5">
                  <span className="text-[10px] text-muted-foreground uppercase">Value</span>
                  <span className="text-sm font-semibold tabular-nums text-foreground">
                    {formatINR(item.currentValue)}
                  </span>
                </div>
                <div className="flex flex-col items-center px-3 py-2.5">
                  <span className="text-[10px] text-muted-foreground uppercase">{"P&L"}</span>
                  <span className={`text-sm font-semibold tabular-nums ${item.pnl >= 0 ? "text-profit" : "text-loss"}`}>
                    {item.pnl >= 0 ? "+" : ""}{formatINR(item.pnl)}
                  </span>
                </div>
              </div>

              <div className="px-4 py-2.5 flex flex-col gap-2 border-t border-border">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-muted-foreground">Day Range</span>
                    <span className="text-[10px] tabular-nums text-muted-foreground">
                      {formatINR(item.dayLow)} - {formatINR(item.dayHigh)}
                    </span>
                  </div>
                  <Progress value={dayRange} className="h-1 bg-secondary [&>div]:bg-primary" />
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-muted-foreground">52W Range</span>
                    <span className="text-[10px] tabular-nums text-muted-foreground">
                      {formatINR(item.low52w)} - {formatINR(item.high52w)}
                    </span>
                  </div>
                  <Progress value={range52w} className="h-1 bg-secondary [&>div]:bg-chart-2" />
                </div>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
