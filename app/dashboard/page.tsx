import { redirect } from "next/navigation"
import { getUser } from "@/lib/auth"
import { Dashboard } from "@/components/dashboard"

export default async function DashboardPage() {
  const user = await getUser()
  if (!user) redirect("/")
  return <Dashboard username={user.username} />
}
