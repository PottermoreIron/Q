const NETWORK_ERROR_RE = /failed to fetch|networkerror|load failed|fetch failed/i;

export function formatApiError(error: unknown, fallback: string): string {
  if (!(error instanceof Error)) return fallback;

  const message = error.message.trim();
  if (!message) return fallback;

  if (NETWORK_ERROR_RE.test(message)) {
    return "Cannot reach API server. Start backend at localhost:8000 or set NEXT_PUBLIC_API_URL.";
  }

  if (message.toLowerCase().includes("cors")) {
    return "Request blocked by CORS policy. Check API CORS settings for the web origin.";
  }

  return message;
}