import { getJob } from "../api/client";
import type { Job, JobStatus, SyncResult } from "../api/types";
import { usePolling } from "./usePolling";

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
  const { value: job, error } = usePolling<Job>({
    fetcher: () => getJob(jobId as string),
    isTerminal: (latest) => TERMINAL_STATUSES.includes(latest.status),
    intervalMs: POLL_INTERVAL_MS,
    enabled: jobId !== null,
    restartKey: jobId,
  });

  return {
    job,
    status: job?.status ?? null,
    progress: job?.progress ?? 0,
    progressMessage: job?.progress_message ?? null,
    result: job?.result ?? null,
    error: error ?? job?.error ?? null,
  };
}
