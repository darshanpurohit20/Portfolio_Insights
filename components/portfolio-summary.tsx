"use client"

import { Card, CardContent } from "@/components/ui/card"
import { TrendingUp, TrendingDown, IndianRupee, BarChart3, ArrowUpRight, ArrowDownRight } from "lucide-react"
import type { PortfolioItem } from "@/lib/types"

function formatINR(value: number): string {
  if (Math.abs(value) >= 10000000) return `${(value / 10000000).toFixed(2)}Cr`
  if (Math.abs(value) >= 100000) return `${(value / 100000).toFixed(2)}L`
  return value.toLocaleString("en-IN", { maximumFractionDigits: 0 })
}

interface Props {
  items: PortfolioItem[]
  loading: boolean
}

export function PortfolioSummary({ items, loading }: Props) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <Card key={i} className="border-border bg-card animate-pulse">
            <CardContent className="p-4">
              <div className="h-3 w-20 rounded bg-secondary mb-3" />
              <div className="h-6 w-24 rounded bg-secondary mb-2" />
              <div className="h-3 w-16 rounded bg-secondary" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const totalInvested = items.reduce((s, i) => s + i.invested, 0)
  const totalValue = items.reduce((s, i) => s + i.currentValue, 0)
  const totalPnl = totalValue - totalInvested
  const totalPnlPct = totalInvested ? (totalPnl / totalInvested) * 100 : 0

  const totalDayHigh = items.reduce((s, i) => s + i.dayHighValue, 0)
  const totalDayLow = items.reduce((s, i) => s + i.dayLowValue, 0)
  const total52High = items.reduce((s, i) => s + i.high52wValue, 0)
  const total52Low = items.reduce((s, i) => s + i.low52wValue, 0)

  const dayHighPnl = totalDayHigh - totalInvested
  const dayLowPnl = totalDayLow - totalInvested
  const high52Pnl = total52High - totalInvested
  const low52Pnl = total52Low - totalInvested

  const metrics = [
    {
      label: "Total Invested",
      value: totalInvested,
      icon: IndianRupee,
      color: "text-foreground",
    },
    {
      label: "Current Value",
      value: totalValue,
      pnl: totalPnl,
      pnlPct: totalPnlPct,
      icon: BarChart3,
      color: totalPnl >= 0 ? "text-profit" : "text-loss",
    },
    {
      label: "Total P&L",
      value: totalPnl,
      pnlPct: totalPnlPct,
      icon: totalPnl >= 0 ? TrendingUp : TrendingDown,
      color: totalPnl >= 0 ? "text-profit" : "text-loss",
      isBig: true,
    },
    {
      label: "Day Range",
      high: totalDayHigh,
      low: totalDayLow,
      highPnl: dayHighPnl,
      lowPnl: dayLowPnl,
      icon: ArrowUpRight,
    },
    {
      label: "52W Range",
      high: total52High,
      low: total52Low,
      highPnl: high52Pnl,
      lowPnl: low52Pnl,
      icon: ArrowDownRight,
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
      {metrics.map((m) => (
        <Card
          key={m.label}
          className={`border-border bg-card ${m.isBig ? "col-span-2 md:col-span-1" : ""}`}
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <m.icon className={`h-4 w-4 ${m.color || "text-muted-foreground"}`} />
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {m.label}
              </span>
            </div>

            {"high" in m ? (
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">High</span>
                  <span className="text-sm font-semibold text-profit">
                    {formatINR(m.high!)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Low</span>
                  <span className="text-sm font-semibold text-loss">
                    {formatINR(m.low!)}
                  </span>
                </div>
                <div className="mt-1 flex items-center justify-between border-t border-border pt-1">
                  <span className="text-[10px] text-muted-foreground">P&L Range</span>
                  <span className="text-[10px]">
                    <span className="text-loss">{formatINR(m.lowPnl!)}</span>
                    {" - "}
                    <span className="text-profit">{formatINR(m.highPnl!)}</span>
                  </span>
                </div>
              </div>
            ) : (
              <>
                <p className={`text-xl font-bold tabular-nums ${m.color || "text-foreground"}`}>
                  {formatINR(m.value!)}
                </p>
                {m.pnlPct !== undefined && (
                  <p className={`text-xs tabular-nums ${m.pnlPct >= 0 ? "text-profit" : "text-loss"}`}>
                    {m.pnlPct >= 0 ? "+" : ""}{m.pnlPct.toFixed(2)}%
                    {m.pnl !== undefined && ` (${m.pnl >= 0 ? "+" : ""}${formatINR(m.pnl)})`}
                  </p>
                )}
              </>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
