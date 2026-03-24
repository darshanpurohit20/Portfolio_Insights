"use client"

import { useState } from "react"
import { Upload, FileSearch, ArrowRight, Loader2, Image as ImageIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { toast } from "sonner"

export function PortfolioOCR() {
  const [isUploading, setIsUploading] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith("image/")) {
      toast.error("Please upload an image file")
      return
    }

    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
  }

  const handleExtract = async () => {
    if (!previewUrl) return
    
    setIsUploading(true)
    try {
      // Logic for Groq API extraction will be added to the API route
      // This is a placeholder for the integration
      const response = await fetch("/api/portfolio/extract", {
        method: "POST",
        body: JSON.stringify({ image: previewUrl }), // We'll need to handle base64 encoding later
        headers: { "Content-Type": "application/json" }
      })

      if (!response.ok) throw new Error("Extraction failed")
      
      const data = await response.json()
      toast.success("Portfolio extracted successfully!")
      console.log(data)
    } catch (error) {
      toast.error("Failed to extract portfolio details. Please try again.")
    } finally {
      setIsUploading(false)
    }
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
