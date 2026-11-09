import apiClient from "@/api";

/**
 * Record a product event for beta measurement. Fire-and-forget: failures are
 * ignored and never affect the page. Only allowlisted names and short
 * properties are accepted by the server; never pass user-entered text.
 */
export function track(name, props = {}) {
  try {
    apiClient.post("/api/events", { name, props }).catch(() => {});
  } catch {
    // Tracking must never break the UI.
  }
}
