"use client"

import { useState, useMemo } from "react"
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import type { PortfolioItem } from "@/lib/types"

const COLORS = [
  "#3b82f6", "#10b981", "#f59e0b", "#6366f1", "#ec4899", 
  "#8b5cf6", "#06b6d4", "#f43f5e", "#14b8a6", "#f97316"
]

interface Props {
  items: PortfolioItem[]
}

const CustomTooltip = ({ active, payload, totalValue }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload
    const percentage = ((data.value / totalValue) * 100).toFixed(1)
    
    return (
      <div className="bg-card border border-border p-3 rounded-lg shadow-xl max-w-[200px]">
        <p className="text-sm font-bold text-foreground mb-1">{data.name}</p>
        <div className="flex justify-between items-center gap-4 mb-2">
          <span className="text-xs text-muted-foreground">₹{data.value.toLocaleString("en-IN")}</span>
          <span className="text-xs font-semibold text-primary">{percentage}%</span>
        </div>
        {data.stocks && data.stocks.length > 0 && (
          <div className="border-t border-border pt-2">
            <p className="text-[10px] text-muted-foreground uppercase mb-1">Stocks</p>
            <div className="flex flex-wrap gap-1">
              {data.stocks.map((s: string, i: number) => (
                <span key={i} className="text-[10px] bg-secondary px-1.5 py-0.5 rounded text-foreground">
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }
  return null
}

export function PortfolioCharts({ items }: Props) {
  const [view, setView] = useState("stock")

  const totalValue = useMemo(() => 
    items.reduce((sum, item) => sum + item.currentValue, 0), 
  [items])

  const chartData = useMemo(() => {
    if (!items.length) return []

    if (view === "stock") {
      return items
        .map((item) => ({
          name: item.name,
          value: item.currentValue,
          stocks: []
        }))
        .sort((a, b) => b.value - a.value)
    }

    if (view === "sector") {
      const sectors: Record<string, { value: number, stocks: string[] }> = {}
      items.forEach((item) => {
        const s = item.sector || "Other"
        if (!sectors[s]) sectors[s] = { value: 0, stocks: [] }
        sectors[s].value += item.currentValue
        sectors[s].stocks.push(item.symbol)
      })
      return Object.entries(sectors)
        .map(([name, data]) => ({ name, value: data.value, stocks: data.stocks }))
        .sort((a, b) => b.value - a.value)
    }

    if (view === "cap") {
      const caps: Record<string, { value: number, stocks: string[] }> = {}
      items.forEach((item) => {
        const c = item.capType || "Small Cap"
        if (!caps[c]) caps[c] = { value: 0, stocks: [] }
        caps[c].value += item.currentValue
        caps[c].stocks.push(item.symbol)
      })
      return Object.entries(caps)
        .map(([name, data]) => ({ name, value: data.value, stocks: data.stocks }))
        .sort((a, b) => {
            const order = { "Large Cap": 3, "Mid Cap": 2, "Small Cap": 1 }
            return (order[b.name as keyof typeof order] || 0) - (order[a.name as keyof typeof order] || 0)
        })
    }

    return []
  }, [items, view])

  if (items.length === 0) return null

  return (
    <Card className="border-border bg-card shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0 text-foreground">
        <CardTitle className="text-base font-semibold">Portfolio Allocation</CardTitle>
        <Tabs value={view} onValueChange={setView}>
          <TabsList className="bg-secondary h-8">
            <TabsTrigger value="stock" className="text-xs h-7">Stock</TabsTrigger>
            <TabsTrigger value="sector" className="text-xs h-7">Sector</TabsTrigger>
            <TabsTrigger value="cap" className="text-xs h-7">Market Cap</TabsTrigger>
          </TabsList>
        </Tabs>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
                stroke="transparent"
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip totalValue={totalValue} />} />
              <Legend 
                 verticalAlign="bottom" 
                 align="center"
                 iconType="circle"
                 wrapperStyle={{ fontSize: '10px', paddingTop: '20px' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
