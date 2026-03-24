"use client"

import { useState } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Sparkline } from "@/components/sparkline"
import { ArrowUpDown, Trash2 } from "lucide-react"
import type { PortfolioItem } from "@/lib/types"

function formatINR(value: number): string {
  return value.toLocaleString("en-IN", { maximumFractionDigits: 2 })
}

type SortKey = "name" | "currentPrice" | "pnl" | "pnlPercent" | "currentValue" | "invested"

interface Props {
  items: PortfolioItem[]
  onRemove: (id: string) => void
  loading: boolean
}

export function PortfolioTable({ items, onRemove, loading }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("pnl")
  const [sortAsc, setSortAsc] = useState(false)

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortAsc(!sortAsc)
    } else {
      setSortKey(key)
      setSortAsc(false)
    }
  }

  const sorted = [...items].sort((a, b) => {
    const av = a[sortKey]
    const bv = b[sortKey]
    if (typeof av === "string" && typeof bv === "string") {
      return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av)
    }
    return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number)
  })

  if (loading) {
    return (
      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <div className="animate-pulse p-6">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex gap-4 mb-4">
              <div className="h-4 w-24 rounded bg-secondary" />
              <div className="h-4 w-16 rounded bg-secondary" />
              <div className="h-4 w-20 rounded bg-secondary" />
              <div className="h-4 w-16 rounded bg-secondary" />
            </div>
          ))}
        </div>
      </div>
    )
  }

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
    <div className="rounded-lg border border-border bg-card overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="border-border hover:bg-secondary/50">
            <TableHead className="text-muted-foreground w-[200px]">
              <button onClick={() => handleSort("name")} className="flex items-center gap-1">
                Stock <ArrowUpDown className="h-3 w-3" />
              </button>
            </TableHead>
            <TableHead className="text-muted-foreground text-right">Qty</TableHead>
            <TableHead className="text-muted-foreground text-right">
              <button onClick={() => handleSort("currentPrice")} className="ml-auto flex items-center gap-1">
                CMP <ArrowUpDown className="h-3 w-3" />
              </button>
            </TableHead>
            <TableHead className="text-muted-foreground text-center hidden md:table-cell">Chart</TableHead>
            <TableHead className="text-muted-foreground text-right">
              <button onClick={() => handleSort("invested")} className="ml-auto flex items-center gap-1">
                Invested <ArrowUpDown className="h-3 w-3" />
              </button>
            </TableHead>
            <TableHead className="text-muted-foreground text-right">
              <button onClick={() => handleSort("currentValue")} className="ml-auto flex items-center gap-1">
                Value <ArrowUpDown className="h-3 w-3" />
              </button>
            </TableHead>
            <TableHead className="text-muted-foreground text-right">
              <button onClick={() => handleSort("pnl")} className="ml-auto flex items-center gap-1">
                {"P&L"} <ArrowUpDown className="h-3 w-3" />
              </button>
            </TableHead>
            <TableHead className="text-muted-foreground text-center hidden lg:table-cell">Day Range</TableHead>
            <TableHead className="text-muted-foreground text-center hidden lg:table-cell">52W Range</TableHead>
            <TableHead className="w-10" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((item) => {
            const dayRange =
              item.dayHigh !== item.dayLow
                ? ((item.currentPrice - item.dayLow) / (item.dayHigh - item.dayLow)) * 100
                : 50

            const range52w =
              item.high52w !== item.low52w
                ? ((item.currentPrice - item.low52w) / (item.high52w - item.low52w)) * 100
                : 50

            return (
              <TableRow key={item.id} className="border-border hover:bg-secondary/30">
                <TableCell>
                  <div className="flex flex-col">
                    <span className="font-medium text-foreground text-sm">{item.name}</span>
                    <span className="text-xs text-muted-foreground">{item.symbol}</span>
                  </div>
                </TableCell>
                <TableCell className="text-right tabular-nums text-foreground">
                  {item.qty}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex flex-col items-end">
                    <span className="font-medium tabular-nums text-foreground">
                      {formatINR(item.currentPrice)}
                    </span>
                    <span className={`text-xs tabular-nums ${item.changePercent >= 0 ? "text-profit" : "text-loss"}`}>
                      {item.changePercent >= 0 ? "+" : ""}{item.changePercent.toFixed(2)}%
                    </span>
                  </div>
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  <div className="w-24 mx-auto">
                    <Sparkline data={item.history} profit={item.pnl >= 0} />
                  </div>
                </TableCell>
                <TableCell className="text-right tabular-nums text-foreground">
                  {formatINR(item.invested)}
                </TableCell>
                <TableCell className="text-right tabular-nums text-foreground">
                  {formatINR(item.currentValue)}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex flex-col items-end gap-0.5">
                    <Badge
                      variant={item.pnl >= 0 ? "default" : "destructive"}
                      className={
                        item.pnl >= 0
                          ? "bg-profit/15 text-profit border-profit/20 hover:bg-profit/20"
                          : "bg-loss/15 text-loss border-loss/20 hover:bg-loss/20"
                      }
                    >
                      {item.pnl >= 0 ? "+" : ""}{formatINR(item.pnl)}
                    </Badge>
                    <span className={`text-xs tabular-nums ${item.pnlPercent >= 0 ? "text-profit" : "text-loss"}`}>
                      {item.pnlPercent >= 0 ? "+" : ""}{item.pnlPercent.toFixed(2)}%
                    </span>
                  </div>
                </TableCell>
                <TableCell className="hidden lg:table-cell">
                  <div className="flex flex-col gap-1 items-center min-w-[100px]">
                    <Progress value={dayRange} className="h-1.5 w-full bg-secondary [&>div]:bg-primary" />
                    <span className="text-[10px] tabular-nums text-muted-foreground">
                      {formatINR(item.dayLow)} - {formatINR(item.dayHigh)}
                    </span>
                  </div>
                </TableCell>
                <TableCell className="hidden lg:table-cell">
                  <div className="flex flex-col gap-1 items-center min-w-[100px]">
                    <Progress value={range52w} className="h-1.5 w-full bg-secondary [&>div]:bg-chart-2" />
                    <span className="text-[10px] tabular-nums text-muted-foreground">
                      {formatINR(item.low52w)} - {formatINR(item.high52w)}
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-muted-foreground hover:text-loss"
                    onClick={() => onRemove(item.id)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    <span className="sr-only">Remove {item.name}</span>
                  </Button>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}
