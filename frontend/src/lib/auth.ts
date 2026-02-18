import type { User, UserProfile, Gamification } from "./types";
import { api } from "./api-client";

export async function getCurrentUser(): Promise<User | null> {
  try {
    return await api.get<User>("/api/auth/me");
  } catch {
    return null;
  }
}

export async function getUserProfile(): Promise<UserProfile | null> {
  try {
    return await api.get<UserProfile>("/api/profile");
  } catch {
    return null;
  }
}

export async function getGamification(): Promise<Gamification | null> {
  try {
    return await api.get<Gamification>("/api/gamification/status");
  } catch {
    return null;
  }
}

export async function login(
  email: string,
  password: string
): Promise<{ success: boolean; error?: string }> {
  try {
    await api.post("/api/auth/login", { email, password });
    return { success: true };
  } catch (e) {
    return { success: false, error: e instanceof Error ? e.message : "Login failed" };
  }
}

export async function register(data: {
  name: string;
  email: string;
  password: string;
}): Promise<{ success: boolean; error?: string }> {
  try {
    await api.post("/api/auth/register", data);
    return { success: true };
  } catch (e) {
    return { success: false, error: e instanceof Error ? e.message : "Registration failed" };
  }
}

export async function logout(): Promise<void> {
  await api.post("/api/auth/logout");
}

export async function forgotPassword(
  email: string
): Promise<{ success: boolean; error?: string }> {
  try {
    await api.post("/api/auth/forgot-password", { email });
    return { success: true };
  } catch (e) {
    return { success: false, error: e instanceof Error ? e.message : "Request failed" };
  }
}

/** Routes that don't require authentication */
export const PUBLIC_ROUTES = [
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/try",
  "/pricing",
] as const;

export function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );
}
