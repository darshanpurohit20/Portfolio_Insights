import { NextRequest, NextResponse } from "next/server"

interface StockHolding {
  symbol: string
  qty: number | string
  buyPrice: number | string
}

export async function POST(req: NextRequest) {
  try {
    const { image } = await req.json()

    if (!image) {
      return NextResponse.json({ error: "No image provided" }, { status: 400 })
    }

    // Get Python backend URL from environment
    const backendUrl = process.env.PYTHON_BACKEND_URL || "http://0.0.0.0:7860"
    const extractUrl = `${backendUrl}/api/portfolio/extract`

    console.log(`📤 Proxying portfolio extraction to Python backend: ${extractUrl}`)

    // Forward request to Python backend
    const backendResponse = await fetch(extractUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ image })
    })

    if (!backendResponse.ok) {
      const error = await backendResponse.json()
      console.error("Backend extraction error:", error)
      
      return NextResponse.json(
        { error: error.error || error.message || "Failed to extract portfolio" },
        { status: backendResponse.status }
      )
    }

    const result = await backendResponse.json()
    
    console.log(`✅ Backend returned ${result.data?.length || 0} stocks`)

    // Validate and normalize the data from backend
    const validatedStocks = (result.data || [])
      .filter((item: any) => {
        return item.symbol && (item.qty || item.qty === 0) && (item.buyPrice || item.buyPrice === 0)
      })
      .map((item: any) => ({
        symbol: String(item.symbol).toUpperCase().trim(),
        qty: parseInt(String(item.qty).replace(/[^0-9.]/g, '')) || 0,
        buyPrice: parseFloat(String(item.buyPrice).replace(/[^0-9.]/g, '')) || 0
      }))
      .filter(item => item.qty > 0 && item.buyPrice > 0)

    if (validatedStocks.length === 0) {
      return NextResponse.json({ 
        success: true,
        data: [],
        message: result.message || "No portfolio data found in the image. Please try another screenshot showing your stock holdings." 
      })
    }

    return NextResponse.json({ 
      success: true, 
      data: validatedStocks,
      message: result.message || `Successfully extracted ${validatedStocks.length} stocks from your portfolio image`
    })

  } catch (error: any) {
    console.error("Portfolio extraction error:", error)
    return NextResponse.json({ 
      error: error.message || "Failed to extract portfolio from image" 
    }, { status: 500 })
  }
}
