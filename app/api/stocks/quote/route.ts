import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

export async function GET(req: NextRequest) {
  try {
    const symbols = req.nextUrl.searchParams.get("symbols")
    if (!symbols) {
      return NextResponse.json({ error: "No symbols provided" }, { status: 400 })
    }

    console.log(`📊 Proxying request to Python backend for: ${symbols}`)

    // Call the Python backend
    const backendUrl = `${BACKEND_URL}/api/stocks/quote?symbols=${encodeURIComponent(symbols)}`
    console.log(`🔗 Backend URL: ${backendUrl}`)

    const response = await fetch(backendUrl, {
      method: "GET",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
      },
    })

    if (!response.ok) {
      console.error(`Backend error: ${response.status}`)
      throw new Error(`Backend returned ${response.status}`)
    }

    const data = await response.json()
    console.log(`✅ Received data from backend for ${symbols}`)
    
    return NextResponse.json(data)
  } catch (error: any) {
    console.error("API Error:", error.message)
    return NextResponse.json(
      { 
        error: "Failed to fetch stock data", 
        message: error?.message,
        hint: "Make sure the Python backend is running on " + (process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000")
      },
      { status: 500 }
    )
  }
}
