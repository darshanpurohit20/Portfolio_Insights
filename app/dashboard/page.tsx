import { redirect } from "next/navigation"
import { auth } from "@/auth"
import { Dashboard } from "@/components/dashboard"

export default async function DashboardPage() {
  const session = await auth()
  if (!session?.user) redirect("/")
  return <Dashboard username={session.user.name || session.user.email || "User"} />
}
