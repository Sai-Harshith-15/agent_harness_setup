import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  // Simple auth gate: check for a 'token' cookie or Authorization header
  const token = request.cookies.get('mission_control_token')?.value
  const authHeader = request.headers.get('Authorization')

  // Allow unrestricted access to the login page
  if (request.nextUrl.pathname.startsWith('/login')) {
    return NextResponse.next()
  }

  // If there's no valid token and no auth header, redirect to /login
  const expectedPin = process.env.MISSION_CONTROL_PIN || 'admin-token-123'
  if (token !== expectedPin && authHeader !== `Bearer ${expectedPin}`) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
