import { NextRequest, NextResponse } from "next/server"

interface StockHolding {
  symbol: string
  qty: number | string
  buyPrice: number | string
}

export async function POST(req: NextRequest) {
  try {
    const { image } = await req.json()
    const apiKey = process.env.GROQ_API_KEY

    if (!apiKey) {
      return NextResponse.json({ error: "Groq API key not configured" }, { status: 500 })
    }

    if (!image) {
      return NextResponse.json({ error: "No image provided" }, { status: 400 })
    }

    // Extract base64 data (handle data:image/... format)
    let imageBase64 = image
    if (image.includes("base64,")) {
      imageBase64 = image.split("base64,")[1]
    }

    // Get media type from data URL if available
    let mediaType = "image/jpeg"
    if (image.includes("data:image/")) {
      mediaType = image.match(/data:(image\/[a-z]+);/)?.[1] || "image/jpeg"
    }

    // Call Groq Vision API (Llama 3.2 Vision 90B)
    const groqResponse = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: "llama-3.2-11b-vision-preview",
        messages: [
          {
            role: "user",
            content: [
              {
                type: "image_url",
                image_url: {
                  url: `data:${mediaType};base64,${imageBase64}`
                }
              },
              {
                type: "text",
                text: `You are a financial portfolio extraction expert. Analyze this portfolio screenshot and extract ALL stock holdings visible.

IMPORTANT: Extract ONLY stocks that are clearly shown in the image.

Return a JSON array with this exact format (no markdown, just raw JSON):
[
  { "symbol": "STOCKNAME", "qty": 100, "buyPrice": 1234.56 },
  { "symbol": "ANOTHER", "qty": 50, "buyPrice": 5678.90 }
]

Rules:
1. symbol: Use NSE stock symbol (e.g., HDFCBANK, INFY, ITC, RELIANCE)
2. qty: Number of units (integer)
3. buyPrice: Average/buy price per unit (number with decimals)
4. Return ONLY the JSON array, no other text
5. If no portfolio data is found, return: []

Extract all visible holdings from the image.`
              }
            ]
          }
        ],
        temperature: 0.1,
        max_tokens: 2000
      })
    })

    if (!groqResponse.ok) {
      const error = await groqResponse.json()
      console.error("Groq API error:", error)
      return NextResponse.json({ error: "Failed to process image with Groq Vision" }, { status: 500 })
    }

    const groqResult = await groqResponse.json()
    const responseText = groqResult.choices?.[0]?.message?.content || ""

    // Parse the response - extract JSON array
    let extractedStocks: StockHolding[] = []
    
    try {
      // Try direct parsing first
      extractedStocks = JSON.parse(responseText)
    } catch {
      // If that fails, try to extract JSON from the response
      const jsonMatch = responseText.match(/\[[\s\S]*\]/)
      if (jsonMatch) {
        try {
          extractedStocks = JSON.parse(jsonMatch[0])
        } catch {
          console.warn("Could not parse extracted JSON:", responseText)
          extractedStocks = []
        }
      }
    }

    // Validate and normalize the data
    const validatedStocks = extractedStocks
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
        message: "No portfolio data found in the image. Please try another screenshot showing your stock holdings." 
      })
    }

    return NextResponse.json({ 
      success: true, 
      data: validatedStocks,
      message: `Successfully extracted ${validatedStocks.length} stocks from your portfolio image`
    })

  } catch (error: any) {
    console.error("Portfolio extraction error:", error)
    return NextResponse.json({ 
      error: error.message || "Failed to extract portfolio from image" 
    }, { status: 500 })
  }
}
