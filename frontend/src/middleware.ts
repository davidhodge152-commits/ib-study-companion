import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/** Routes that don't require authentication */
const PUBLIC_ROUTES = [
  "/",
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/try",
  "/pricing",
];

function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip API routes, static files, and Next.js internals
  if (
    pathname.startsWith("/api") ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/static") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  // Check for session cookie (Flask-Login sets "session" or "remember_token")
  const sessionCookie =
    request.cookies.get("session") ?? request.cookies.get("remember_token");

  // Redirect unauthenticated users to login (skip public routes)
  if (!sessionCookie && !isPublicRoute(pathname)) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // NOTE: We intentionally do NOT redirect authenticated users away from
  // public routes here. The session cookie may exist but be invalidated
  // server-side (e.g. after logout), so we can't trust it. Client-side
  // auth checks handle redirecting authenticated users to /dashboard.

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all paths except:
     * - api routes
     * - _next (Next.js internals)
     * - static files with extensions
     */
    "/((?!api|_next/static|_next/image|favicon.ico|.*\\.).*)",
  ],
};
