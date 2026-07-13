import { NextRequest, NextResponse } from "next/server"

// Server-side only usage of this var (Route Handlers run on the server),
// matching the name your quote/route.ts already uses.
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:7860"

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get("q") ?? ""

  if (q.trim().length < 1) {
    return NextResponse.json({ results: [] })
  }

  try {
    const res = await fetch(
      `${BACKEND_URL}/api/stocks/search?q=${encodeURIComponent(q)}`,
      { signal: AbortSignal.timeout(6000), cache: "no-store" }
    )

    if (!res.ok) {
      return NextResponse.json({ results: [] }, { status: 200 })
    }

    const data = await res.json()
    return NextResponse.json(data)
  } catch (err) {
    // Backend down / network issue — fail soft so the frontend's
    // static-list fallback takes over instead of showing an error.
    return NextResponse.json({ results: [], error: String(err) }, { status: 200 })
  }
}