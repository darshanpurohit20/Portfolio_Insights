import { SignJWT, jwtVerify } from "jose"
import { cookies } from "next/headers"

const SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET || "portfolio-dashboard-secret-key-change-me"
)

const USERS: Record<string, string> = (() => {
  const raw = process.env.USERS_JSON
  if (raw) {
    try {
      return JSON.parse(raw)
    } catch {
      /* fall through */
    }
  }
  return { admin: "admin123", demo: "demo123" }
})()

export async function createToken(username: string) {
  return new SignJWT({ username })
    .setProtectedHeader({ alg: "HS256" })
    .setExpirationTime("7d")
    .sign(SECRET)
}

export async function verifyToken(token: string) {
  try {
    const { payload } = await jwtVerify(token, SECRET)
    return payload as { username: string }
  } catch {
    return null
  }
}

export function validateCredentials(username: string, password: string) {
  return USERS[username] === password
}

export async function getUser() {
  const cookieStore = await cookies()
  const token = cookieStore.get("auth-token")?.value
  if (!token) return null
  return verifyToken(token)
}
