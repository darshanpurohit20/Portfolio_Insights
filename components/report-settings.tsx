"use client"

import { useState, useEffect } from "react"
import { useSession } from "next-auth/react"
import { toast } from "sonner"
import { Mail, Settings, Download } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { PortfolioItem } from "@/lib/types"

interface ReportSettingsDialogProps {
  portfolioItems: PortfolioItem[]
}

export function ReportSettingsDialog({ portfolioItems }: ReportSettingsDialogProps) {
  const { data: session } = useSession()
  const [open, setOpen] = useState(false)
  const [enabled, setEnabled] = useState(false)
  const [frequency, setFrequency] = useState("Weekly")
  const [loading, setLoading] = useState(false)
  const [downloading, setDownloading] = useState(false)

  // Load preferences from local storage on mount
  useEffect(() => {
    if (session?.user?.email) {
      const saved = localStorage.getItem(`report-settings-${session.user.email}`)
      if (saved) {
        const parsed = JSON.parse(saved)
        setEnabled(parsed.enabled ?? false)
        if (parsed.frequency) {
          setFrequency(parsed.frequency)
        }
      }
    }
  }, [session?.user?.email])

  async function handleSave() {
    if (!session?.user?.email) {
      toast.error("You must be logged in to save report settings.")
      return
    }

    setLoading(true)
    try {
      // 1. Save locally
      localStorage.setItem(`report-settings-${session.user.email}`, JSON.stringify({ enabled, frequency }))
      
      // 2. Sync to Backend
      const res = await fetch("/api/report/schedule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: session.user.email,
          enabled,
          frequency,
          portfolio: portfolioItems.map(item => ({
            symbol: item.symbol,
            qty: item.qty,
            buyPrice: item.buyPrice,
          }))
        })
      })

      if (!res.ok) throw new Error("Failed to sync settings with server")
      
      toast.success("Report settings saved successfully")
      setOpen(false)
    } catch (err: any) {
      toast.error(err.message || "Something went wrong")
    } finally {
      setLoading(false)
    }
  }

  async function handleDownloadNow() {
    if (!session?.user?.email) return
    setDownloading(true)
    try {
      const res = await fetch("/api/report/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: session.user.email,
          portfolio: portfolioItems,
        }),
      })

      if (!res.ok) throw new Error("Failed to generate PDF")
      
      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `Portfolio_Report_${new Date().toISOString().split("T")[0]}.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      toast.success("Report downloaded successfully")
    } catch (err: any) {
      toast.error(err.message || "Failed to download report")
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-primary">
          <Settings className="h-4 w-4" />
          <span className="sr-only">Report Settings</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px] border-border bg-card">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-primary" />
            Scheduled PDF Reports
          </DialogTitle>
          <DialogDescription>
            Receive a beautifully formatted PDF summary of your portfolio directly to your inbox.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 py-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base text-foreground">Enable Email Reports</Label>
              <p className="text-sm text-muted-foreground">
                Sent to {session?.user?.email || "your email"}
              </p>
            </div>
            <Switch
              checked={enabled}
              onCheckedChange={setEnabled}
              aria-readonly={!session?.user?.email}
            />
          </div>

          {enabled && (
            <div className="grid gap-2 animate-in fade-in zoom-in-95">
              <Label htmlFor="frequency" className="text-foreground">Frequency</Label>
              <Select value={frequency} onValueChange={setFrequency}>
                <SelectTrigger id="frequency" className="bg-secondary border-border text-foreground">
                  <SelectValue placeholder="Select frequency" />
                </SelectTrigger>
                <SelectContent className="bg-card border-border">
                  <SelectItem value="Daily">Daily (6 PM IST)</SelectItem>
                  <SelectItem value="Weekly">Weekly (Friday 6 PM IST)</SelectItem>
                  <SelectItem value="Monthly">Monthly (End of Month)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-between pt-4 border-t border-border mt-2">
          <Button 
            variant="outline" 
            onClick={handleDownloadNow} 
            disabled={downloading || portfolioItems.length === 0}
            className="border-border text-foreground hover:bg-secondary"
          >
            <Download className="mr-2 h-4 w-4" />
            {downloading ? "Generating..." : "Download PDF Now"}
          </Button>
          
          <Button 
            onClick={handleSave} 
            disabled={loading}
            className="bg-primary text-primary-foreground hover:bg-primary/90"
          >
            {loading ? "Saving..." : "Save Preferences"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
