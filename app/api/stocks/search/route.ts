import { NextRequest, NextResponse } from "next/server"
import { searchStocks } from "@/lib/nse-stocks"

export async function GET(req: NextRequest) {
  const query = req.nextUrl.searchParams.get("q") || ""
  const results = searchStocks(query)
  return NextResponse.json(results)
}
