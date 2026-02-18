/**
 * Lightweight analytics module.
 * Currently sends events to our own backend.
 * Can be swapped for PostHog/Mixpanel/Amplitude later.
 */

type EventProperties = Record<string, string | number | boolean | null>;

class Analytics {
  private enabled = true;

  /** Track a named event with optional properties */
  track(event: string, properties?: EventProperties) {
    if (!this.enabled) return;
    // Fire-and-forget -- don't await, don't block UI
    this.send({ type: "event", event, properties });
  }

  /** Track a page view */
  pageView(path: string) {
    if (!this.enabled) return;
    this.send({ type: "pageview", path });
  }

  /** Identify a user (call after login) */
  identify(userId: number, traits?: EventProperties) {
    if (!this.enabled) return;
    this.send({ type: "identify", userId, traits });
  }

  private send(payload: Record<string, unknown>) {
    try {
      const body = JSON.stringify({
        ...payload,
        timestamp: new Date().toISOString(),
        url: typeof window !== "undefined" ? window.location.href : "",
      });
      // Use sendBeacon for reliability (survives page unload)
      if (typeof navigator !== "undefined" && navigator.sendBeacon) {
        navigator.sendBeacon("/api/analytics/event", body);
      } else {
        fetch("/api/analytics/event", {
          method: "POST",
          body,
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          keepalive: true,
        }).catch(() => {});
      }
    } catch {
      // Analytics should never break the app
    }
  }
}

export const analytics = new Analytics();
