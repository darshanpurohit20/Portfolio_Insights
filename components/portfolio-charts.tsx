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

export function PortfolioCharts({ items }: Props) {
  const [view, setView] = useState("stock")

  const chartData = useMemo(() => {
    if (!items.length) return []

    if (view === "stock") {
      return items
        .map((item) => ({
          name: item.name,
          value: item.currentValue,
        }))
        .sort((a, b) => b.value - a.value)
    }

    if (view === "sector") {
      const sectors: Record<string, number> = {}
      items.forEach((item) => {
        const s = item.sector || "Other"
        sectors[s] = (sectors[s] || 0) + item.currentValue
      })
      return Object.entries(sectors)
        .map(([name, value]) => ({ name, value }))
        .sort((a, b) => b.value - a.value)
    }

    if (view === "cap") {
      const caps: Record<string, number> = {}
      items.forEach((item) => {
        const c = item.capType || "Small Cap"
        caps[c] = (caps[c] || 0) + item.currentValue
      })
      return Object.entries(caps)
        .map(([name, value]) => ({ name, value }))
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
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: "hsl(var(--card))", 
                  borderColor: "hsl(var(--border))",
                  borderRadius: "8px",
                  color: "hsl(var(--foreground))"
                }}
                itemStyle={{ color: "hsl(var(--foreground))" }}
                formatter={(value: number) => `₹${value.toLocaleString("en-IN")}`}
              />
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
