import "./ErrorBanner.css";

interface ErrorBannerProps {
  message: string | null | undefined;
  detail?: string;
}

export function ErrorBanner({ message, detail }: ErrorBannerProps) {
  if (!message) {
    return null;
  }

  return (
    <div className="error-banner" role="alert">
      <p>{message}</p>
      {detail && (
        <details>
          <summary>Details</summary>
          <pre>{detail}</pre>
        </details>
      )}
    </div>
  );
}
