"use client"

import { useState } from "react"
import { signIn } from "next-auth/react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { TrendingUp, Mail } from "lucide-react"

export function LoginForm() {
  const [loading, setLoading] = useState(false)

  async function handleGoogleLogin() {
    setLoading(true)
    await signIn("google", { redirectTo: "/dashboard" })
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10">
            <TrendingUp className="h-7 w-7 text-primary" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">StockFolio</h1>
          <p className="text-sm text-muted-foreground">Real-time portfolio tracker for NSE</p>
        </div>

        <Card className="border-border bg-card">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg text-card-foreground">Sign In</CardTitle>
            <CardDescription>
              Sign in with your Google account to track your portfolio.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button 
              onClick={handleGoogleLogin} 
              disabled={loading} 
              variant="outline" 
              className="w-full border-border bg-secondary text-foreground hover:bg-secondary/80 flex items-center justify-center gap-2"
            >
              <Mail className="h-4 w-4" />
              {loading ? "Signing in..." : "Continue with Google"}
            </Button>
          </CardContent>
        </Card>

        <p className="mt-4 text-center text-xs text-muted-foreground">
          Portfolio data is stored locally in your browser.
        </p>
      </div>
    </div>
  )
}
