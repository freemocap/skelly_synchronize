import { useEffect, useState } from "react";
import { ApiError, getJob } from "../api/client";
import type { Job, JobStatus, SyncResult } from "../api/types";

const POLL_INTERVAL_MS = 1000;

const TERMINAL_STATUSES: JobStatus[] = ["succeeded", "failed", "cancelled"];

interface JobPollingState {
  job: Job | null;
  status: JobStatus | null;
  progress: number;
  progressMessage: string | null;
  result: SyncResult | null;
  error: string | null;
}

export function useJobPolling(jobId: string | null): JobPollingState {
  const [job, setJob] = useState<Job | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    setJob(null);
    setFetchError(null);

    if (jobId === null) {
      return;
    }

    let cancelled = false;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    const poll = async () => {
      try {
        const latest = await getJob(jobId);
        if (cancelled) return;
        setJob(latest);
        setFetchError(null);
        if (TERMINAL_STATUSES.includes(latest.status) && intervalId !== null) {
          clearInterval(intervalId);
          intervalId = null;
        }
      } catch (e) {
        if (cancelled) return;
        setFetchError(e instanceof ApiError ? e.detail : "failed to fetch job status");
      }
    };

    poll();
    intervalId = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (intervalId !== null) {
        clearInterval(intervalId);
      }
    };
  }, [jobId]);

  return {
    job,
    status: job?.status ?? null,
    progress: job?.progress ?? 0,
    progressMessage: job?.progress_message ?? null,
    result: job?.result ?? null,
    error: fetchError ?? job?.error ?? null,
  };
}
