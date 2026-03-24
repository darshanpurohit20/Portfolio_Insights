"use client"

import { useState } from "react"
import { Upload, FileSearch, ArrowRight, Loader2, Image as ImageIcon, CheckCircle2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { toast } from "sonner"
import { PortfolioStock } from "@/lib/types"
import { NSE_STOCKS } from "@/lib/nse-stocks"

interface PortfolioOCRProps {
  onAddStocks: (stocks: PortfolioStock[]) => void
}

export function PortfolioOCR({ onAddStocks }: PortfolioOCRProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [base64Image, setBase64Image] = useState<string | null>(null)
  const [extractedData, setExtractedData] = useState<any[] | null>(null)

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith("image/")) {
      toast.error("Please upload an image file")
      return
    }

    const reader = new FileReader()
    reader.onloadend = () => {
      setBase64Image(reader.result as string)
    }
    reader.readAsDataURL(file)

    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    setExtractedData(null)
  }

  const handleExtract = async () => {
    if (!base64Image) return
    
    setIsUploading(true)
    try {
      const response = await fetch("/api/portfolio/extract", {
        method: "POST",
        body: JSON.stringify({ image: base64Image }),
        headers: { "Content-Type": "application/json" }
      })

      const result = await response.json()
      
      if (!response.ok) {
        throw new Error(result.error || `Extraction failed (${response.status})`)
      }
      
      if (result.success && result.data) {
        setExtractedData(result.data)
        toast.success("Portfolio extracted successfully!")
      } else if (result.data && result.data.length === 0) {
        toast.error("No portfolio data found in the image. Please try a clearer screenshot showing your stock holdings.")
      } else {
        throw new Error(result.error || "Failed to extract data")
      }
    } catch (error: any) {
      toast.error(error?.message || "Failed to extract portfolio details. Please try again.")
    } finally {
      setIsUploading(false)
    }
  }

  const handleConfirm = () => {
    if (!extractedData) return

    const newStocks: PortfolioStock[] = extractedData.map((item: any) => {
      // Try to find the matching NSE stock for yfinSymbol
      const stockInfo = NSE_STOCKS.find(s => 
        s.symbol.toUpperCase() === item.symbol.toUpperCase() || 
        s.name.toUpperCase().includes(item.symbol.toUpperCase())
      )

      return {
        id: Math.random().toString(36).substr(2, 9),
        symbol: item.symbol,
        name: stockInfo?.name || item.symbol,
        qty: item.qty,
        buyPrice: item.buyPrice,
        yfinSymbol: stockInfo?.yfinSymbol || `${item.symbol}.NS`,
        addedAt: new Date().toISOString()
      }
    })

    onAddStocks(newStocks)
    setExtractedData(null)
    setPreviewUrl(null)
    setBase64Image(null)
    toast.success(`Successfully added ${newStocks.length} stocks to portfolio`)
  }

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      <Card className="col-span-1 lg:col-span-1 border-dashed">
        <CardHeader>
          <CardTitle>Step 1: Upload Portfolio</CardTitle>
          <CardDescription>
            Upload a screenshot from Zerodha, Groww, or any broker.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center justify-center space-y-4 py-8">
          <div className="flex h-40 w-full items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 bg-muted/50 transition-colors hover:bg-muted">
            {previewUrl ? (
              <img src={previewUrl} alt="Preview" className="h-full object-contain" />
            ) : (
              <label className="flex h-full w-full cursor-pointer flex-col items-center justify-center gap-2">
                <Upload className="h-10 w-10 text-muted-foreground" />
                <span className="text-sm font-medium text-muted-foreground">Click to upload image</span>
                <input type="file" className="hidden" accept="image/*" onChange={handleFileChange} />
              </label>
            )}
          </div>
          {previewUrl && (
            <Button variant="outline" size="sm" onClick={() => setPreviewUrl(null)}>
              Change Image
            </Button>
          )}
        </CardContent>
      </Card>

      <Card className="col-span-1 lg:col-span-2">
        <CardHeader>
          <CardTitle>Step 2: AI Analysis</CardTitle>
          <CardDescription>
            Using Groq AI to extract stock scrip, quantity, and average price.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center justify-center space-y-6 py-12">
          {!previewUrl ? (
            <div className="flex flex-col items-center gap-4 text-center">
              <div className="rounded-full bg-muted p-4">
                <ImageIcon className="h-8 w-8 text-muted-foreground" />
              </div>
              <div>
                <p className="text-lg font-semibold">No image selected</p>
                <p className="text-sm text-muted-foreground">Please upload your portfolio screenshot first</p>
              </div>
            </div>
          ) : extractedData ? (
            <div className="w-full space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-muted-foreground">AI Extracted Potential Holdings:</p>
                <div className="flex items-center gap-1 text-xs text-green-500 font-bold">
                  <CheckCircle2 className="h-3 w-3" />
                  Verified Symbols
                </div>
              </div>
              <div className="grid gap-2">
                {extractedData.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between rounded-md border p-3 text-sm">
                    <div className="flex flex-col">
                      <span className="font-bold">{item.symbol}</span>
                      <span className="text-xs text-muted-foreground">
                        Qty: {item.qty} @ ₹{item.buyPrice}
                      </span>
                    </div>
                    <div className="flex flex-col items-end">
                      <span className="text-muted-foreground">Invested</span>
                      <span className="font-medium">₹{(item.qty * item.buyPrice).toLocaleString("en-IN")}</span>
                    </div>
                  </div>
                ))}
              </div>
              <Button size="lg" className="w-full mt-4" onClick={handleConfirm}>
                Confirm and Add to Portfolio
              </Button>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-6 text-center w-full max-w-sm">
              <div className="rounded-full bg-primary/10 p-4 text-primary animate-pulse">
                <FileSearch className="h-10 w-10" />
              </div>
              <div>
                <p className="text-xl font-bold">Ready to analyze</p>
                <p className="text-sm text-muted-foreground">
                  Our AI will scan the image and identify all your stocks automatically.
                </p>
              </div>
              <Button size="lg" className="w-full" onClick={handleExtract} disabled={isUploading}>
                {isUploading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Extracting Data...
                  </>
                ) : (
                  <>
                    Start Scanning
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
