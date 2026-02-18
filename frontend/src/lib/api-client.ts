import type { ApiError } from "./types";

/**
 * Centralized API client.
 * - Includes session cookie via credentials: "include"
 * - Sends CSRF token from cookie
 * - Auto-redirects on 401
 * - Shows upgrade modal on 402/403
 */

function getCsrfToken(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  if (match) return match[1];
  const meta = document.querySelector<HTMLMetaElement>(
    'meta[name="csrf-token"]'
  );
  return meta?.content ?? "";
}

class ApiClient {
  private baseUrl: string;
  private onUnauthorized?: () => void;
  private onUpgradeRequired?: (type: "credits" | "plan", plan?: string) => void;

  constructor(baseUrl = "") {
    this.baseUrl = baseUrl;
  }

  setOnUnauthorized(cb: () => void) {
    this.onUnauthorized = cb;
  }

  setOnUpgradeRequired(
    cb: (type: "credits" | "plan", plan?: string) => void
  ) {
    this.onUpgradeRequired = cb;
  }

  private async request<T>(
    url: string,
    options: RequestInit = {}
  ): Promise<T> {
    const csrfToken = getCsrfToken();

    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    // Don't set Content-Type for FormData (browser sets boundary)
    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = headers["Content-Type"] ?? "application/json";
    }

    if (csrfToken) {
      headers["X-CSRFToken"] = csrfToken;
    }

    const res = await fetch(`${this.baseUrl}${url}`, {
      ...options,
      headers,
      credentials: "include",
    });

    if (res.status === 401) {
      this.onUnauthorized?.();
      throw new ApiRequestError("Authentication required", 401);
    }

    if (res.status === 402) {
      this.onUpgradeRequired?.("credits");
      throw new ApiRequestError("Insufficient credits", 402);
    }

    if (res.status === 403) {
      try {
        const body: ApiError = await res.clone().json();
        if (body.required_plan) {
          this.onUpgradeRequired?.("plan", body.required_plan);
          throw new ApiRequestError(
            `Upgrade to ${body.required_plan} required`,
            403
          );
        }
      } catch (e) {
        if (e instanceof ApiRequestError) throw e;
      }
      throw new ApiRequestError("Forbidden", 403);
    }

    if (!res.ok) {
      let message = `Request failed: ${res.status}`;
      try {
        const body: ApiError = await res.json();
        message = body.message ?? body.error ?? message;
      } catch {
        // response wasn't JSON
      }
      throw new ApiRequestError(message, res.status);
    }

    const contentType = res.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      return res.json() as Promise<T>;
    }

    return res as unknown as T;
  }

  get<T>(url: string): Promise<T> {
    return this.request<T>(url);
  }

  post<T>(url: string, data?: unknown): Promise<T> {
    return this.request<T>(url, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  postForm<T>(url: string, formData: FormData): Promise<T> {
    return this.request<T>(url, {
      method: "POST",
      body: formData,
    });
  }

  put<T>(url: string, data?: unknown): Promise<T> {
    return this.request<T>(url, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  patch<T>(url: string, data?: unknown): Promise<T> {
    return this.request<T>(url, {
      method: "PATCH",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  delete<T>(url: string): Promise<T> {
    return this.request<T>(url, { method: "DELETE" });
  }

  /**
   * SSE streaming request — returns a ReadableStream for progressive reading.
   */
  async stream(
    url: string,
    data?: unknown
  ): Promise<ReadableStream<Uint8Array>> {
    const csrfToken = getCsrfToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    };
    if (csrfToken) headers["X-CSRFToken"] = csrfToken;

    const res = await fetch(`${this.baseUrl}${url}`, {
      method: "POST",
      headers,
      credentials: "include",
      body: data ? JSON.stringify(data) : undefined,
    });

    if (!res.ok) {
      let message = `Stream failed: ${res.status}`;
      try {
        const body: ApiError = await res.json();
        message = body.message ?? body.error ?? message;
      } catch {
        // not JSON
      }
      throw new ApiRequestError(message, res.status);
    }

    if (!res.body) {
      throw new ApiRequestError("No response body for stream", 500);
    }

    return res.body;
  }
}

export class ApiRequestError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
  }
}

export const api = new ApiClient();
