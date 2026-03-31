import { NextRequest, NextResponse } from "next/server"

/**
 * DEPRECATED: This proxy route is no longer used.
 * Direct frontend-to-backend communication is preferred to avoid Vercel constraints.
 */
export async function POST(req: NextRequest) {
  return NextResponse.json({ 
    error: "This proxy route is deprecated. Use direct Hugging Face URL instead.",
    details: "Vercel serverless functions have a 4.5MB payload limit and 10s timeout, which causes failures for large image OCR tasks. The frontend has been updated to call the backend directly."
  }, { status: 410 }) 
}
