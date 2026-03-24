import { redirect } from "next/navigation"
import { getUser } from "@/lib/auth"
import { LoginForm } from "@/components/login-form"

export default async function HomePage() {
  const user = await getUser()
  if (user) redirect("/dashboard")
  return <LoginForm />
}
