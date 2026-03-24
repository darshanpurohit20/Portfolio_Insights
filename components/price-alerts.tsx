"use client"

import { useState } from "react"
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
import { Badge } from "@/components/ui/badge"
import { Bell, BellOff, Trash2, Plus, ArrowUp, ArrowDown } from "lucide-react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { PriceAlert, PortfolioItem } from "@/lib/types"

interface Props {
  alerts: PriceAlert[]
  items: PortfolioItem[]
  onAddAlert: (alert: PriceAlert) => void
  onRemoveAlert: (id: string) => void
  onToggleAlert: (id: string) => void
}

export function PriceAlerts({ alerts, items, onAddAlert, onRemoveAlert, onToggleAlert }: Props) {
  const [open, setOpen] = useState(false)
  const [symbol, setSymbol] = useState("")
  const [targetPrice, setTargetPrice] = useState("")
  const [condition, setCondition] = useState<"above" | "below">("above")

  function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    const stock = items.find((i) => i.yfinSymbol === symbol)
    if (!stock || !targetPrice) return

    onAddAlert({
      id: `alert-${Date.now()}`,
      symbol: stock.yfinSymbol,
      name: stock.name,
      targetPrice: parseFloat(targetPrice),
      condition,
      active: true,
      triggered: false,
    })

    setSymbol("")
    setTargetPrice("")
    setOpen(false)
  }

  return (
    <>
      <Button
        variant="outline"
        onClick={() => setOpen(true)}
        className="border-border text-foreground hover:bg-secondary"
      >
        <Bell className="h-4 w-4 mr-1" />
        Alerts
        {alerts.filter((a) => a.triggered).length > 0 && (
          <Badge className="ml-1 bg-loss text-loss-foreground h-5 w-5 p-0 flex items-center justify-center">
            {alerts.filter((a) => a.triggered).length}
          </Badge>
        )}
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="bg-card border-border max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-foreground">Price Alerts</DialogTitle>
            <DialogDescription>
              Get notified when a stock hits your target price.
            </DialogDescription>
          </DialogHeader>

          {alerts.length > 0 && (
            <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`flex items-center justify-between rounded-lg border px-3 py-2 ${
                    alert.triggered
                      ? "border-loss/50 bg-loss/5"
                      : "border-border bg-secondary/50"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {alert.condition === "above" ? (
                      <ArrowUp className="h-3.5 w-3.5 text-profit" />
                    ) : (
                      <ArrowDown className="h-3.5 w-3.5 text-loss" />
                    )}
                    <div>
                      <span className="text-sm font-medium text-foreground">{alert.name}</span>
                      <span className="text-xs text-muted-foreground ml-2">
                        {alert.condition === "above" ? ">" : "<"} {alert.targetPrice.toLocaleString("en-IN")}
                      </span>
                    </div>
                    {alert.triggered && (
                      <Badge className="bg-loss/15 text-loss border-loss/20">Triggered</Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => onToggleAlert(alert.id)}
                    >
                      {alert.active ? (
                        <Bell className="h-3.5 w-3.5 text-primary" />
                      ) : (
                        <BellOff className="h-3.5 w-3.5 text-muted-foreground" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-muted-foreground hover:text-loss"
                      onClick={() => onRemoveAlert(alert.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <form onSubmit={handleAdd} className="flex flex-col gap-3 border-t border-border pt-3">
            <Label className="text-sm text-foreground">New Alert</Label>
            <div className="grid grid-cols-3 gap-2">
              <Select value={symbol} onValueChange={setSymbol}>
                <SelectTrigger className="bg-secondary border-border text-foreground">
                  <SelectValue placeholder="Stock" />
                </SelectTrigger>
                <SelectContent className="bg-card border-border">
                  {items.map((i) => (
                    <SelectItem key={i.yfinSymbol} value={i.yfinSymbol}>
                      {i.symbol}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={condition} onValueChange={(v) => setCondition(v as "above" | "below")}>
                <SelectTrigger className="bg-secondary border-border text-foreground">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-card border-border">
                  <SelectItem value="above">Above</SelectItem>
                  <SelectItem value="below">Below</SelectItem>
                </SelectContent>
              </Select>

              <Input
                type="number"
                min="0.01"
                step="0.01"
                value={targetPrice}
                onChange={(e) => setTargetPrice(e.target.value)}
                placeholder="Price"
                className="bg-secondary border-border text-foreground"
              />
            </div>

            <DialogFooter>
              <Button
                type="submit"
                disabled={!symbol || !targetPrice}
                className="bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Alert
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}
