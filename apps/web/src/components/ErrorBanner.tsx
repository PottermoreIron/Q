type ErrorBannerProps = {
  message: string;
  title?: string;
  variant?: "block" | "inline";
  onRetry?: () => void;
  retryLabel?: string;
};

export function ErrorBanner({
  message,
  title = "Backend unavailable",
  variant = "block",
  onRetry,
  retryLabel = "Retry",
}: ErrorBannerProps) {
  if (variant === "inline") {
    return (
      <div className="flex items-center gap-2 text-small text-negative">
        <span>{message}</span>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="underline underline-offset-2 hover:opacity-70 transition-opacity duration-[80ms]"
          >
            {retryLabel}
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="border border-border rounded-lg px-5 py-4 bg-surface">
      <p className="font-serif italic text-title text-ink">{title}</p>
      <p className="text-body text-muted mt-1">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 px-3 py-1.5 border border-border rounded-md text-small text-muted hover:text-body transition-colors duration-[80ms]"
        >
          {retryLabel}
        </button>
      )}
    </div>
  );
}
