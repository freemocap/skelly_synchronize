import { getHealth } from "../api/client";
import { usePolling } from "./usePolling";

const READINESS_BACKOFF_MS = [500, 1000, 2000, 3000];

/** Polls GET /health with backoff until the Tauri-spawned API sidecar is up. */
export function useApiReadiness(): { ready: boolean } {
  const { value } = usePolling<{ status: string }>({
    fetcher: () => getHealth(),
    isTerminal: (latest) => latest.status === "ok",
    backoffMs: READINESS_BACKOFF_MS,
  });

  return { ready: value?.status === "ok" };
}
