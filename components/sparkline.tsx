"use client"

import { ResponsiveContainer, AreaChart, Area } from "recharts"

interface Props {
  data: { date: string; close: number }[]
  profit: boolean
  height?: number
}

export function Sparkline({ data, profit, height = 40 }: Props) {
  if (!data || data.length === 0) return null

  const color = profit ? "var(--profit)" : "var(--loss)"

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 2 }}>
        <defs>
          <linearGradient id={`grad-${profit ? "up" : "down"}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="close"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#grad-${profit ? "up" : "down"})`}
          dot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
