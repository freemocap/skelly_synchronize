import { useEffect, useState } from "react";
import { ApiError, cancelJob } from "../api/client";
import { useJobPolling } from "../hooks/useJobPolling";
import { ErrorBanner } from "../components/ErrorBanner";
import "./ProgressScreen.css";

interface ProgressScreenProps {
  jobId: string;
  onSucceeded: (jobId: string) => void;
  onBackToSetup: () => void;
}

const TERMINAL_STATUSES = ["succeeded", "failed", "cancelled"];

export function ProgressScreen({ jobId, onSucceeded, onBackToSetup }: ProgressScreenProps) {
  const { status, progress, progressMessage, error } = useJobPolling(jobId);
  const [cancelling, setCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "succeeded") {
      onSucceeded(jobId);
    }
  }, [status, jobId, onSucceeded]);

  const handleCancel = async () => {
    setCancelling(true);
    setCancelError(null);
    try {
      await cancelJob(jobId);
    } catch (e) {
      setCancelError(e instanceof ApiError ? e.detail : "failed to cancel job");
    } finally {
      setCancelling(false);
    }
  };

  const isTerminal = status !== null && TERMINAL_STATUSES.includes(status);
  const isIndeterminate = status === "pending" || (status === "running" && progress <= 0);

  return (
    <section className="progress-screen">
      <h2>Synchronizing…</h2>
      <ErrorBanner message={cancelError} />

      <div className={`progress-bar-track${isIndeterminate ? " indeterminate" : ""}`}>
        <div
          className="progress-bar-fill"
          style={isIndeterminate ? undefined : { width: `${Math.round(progress * 100)}%` }}
        />
      </div>
      <p className="progress-status">
        {status ?? "loading…"}
        {progressMessage ? ` — ${progressMessage}` : ""}
      </p>

      {status === "failed" && (
        <>
          <ErrorBanner message={error ?? "sync job failed"} />
          <button onClick={onBackToSetup}>Back to setup</button>
        </>
      )}

      {status === "cancelled" && (
        <>
          <p>Job cancelled.</p>
          <button onClick={onBackToSetup}>Back to setup</button>
        </>
      )}

      {!isTerminal && status !== null && (
        <button onClick={handleCancel} disabled={cancelling}>
          {cancelling ? "Cancelling…" : "Cancel"}
        </button>
      )}
    </section>
  );
}
