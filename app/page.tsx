import { redirect } from "next/navigation"
import { auth } from "@/auth"
import { LoginForm } from "@/components/login-form"

export default async function HomePage() {
  const session = await auth()
  if (session?.user) redirect("/dashboard")
  return <LoginForm />
}
