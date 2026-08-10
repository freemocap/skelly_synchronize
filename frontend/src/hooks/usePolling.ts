import { useEffect, useState } from "react";

interface PollingOptions<T> {
  /** Called on every poll tick. Return the latest value. */
  fetcher: () => Promise<T>;
  /** Stop polling once this returns true for the latest fetched value. */
  isTerminal: (value: T) => boolean;
  /** Fixed poll interval in ms. Mutually exclusive with `backoffMs`. */
  intervalMs?: number;
  /**
   * Capped exponential backoff schedule (ms) used instead of a fixed
   * interval, e.g. [500, 1000, 2000, 3000] repeating the last value once
   * exhausted. Useful when the thing being polled may take a moment to
   * become available (e.g. waiting for a just-spawned process to bind its
   * port).
   */
  backoffMs?: number[];
  enabled?: boolean;
  /** Polling restarts whenever this value changes (e.g. a job id). */
  restartKey?: string | number | null;
}

interface PollingState<T> {
  value: T | null;
  error: string | null;
}

/** Generic interval/backoff poller: fetch, store latest value, stop on terminal. */
export function usePolling<T>({
  fetcher,
  isTerminal,
  intervalMs,
  backoffMs,
  enabled = true,
  restartKey = null,
}: PollingOptions<T>): PollingState<T> {
  const [value, setValue] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setValue(null);
    setError(null);

    if (!enabled) {
      return;
    }

    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;

    const nextDelay = () => {
      if (backoffMs && backoffMs.length > 0) {
        const delay = backoffMs[Math.min(attempt, backoffMs.length - 1)];
        attempt += 1;
        return delay;
      }
      return intervalMs ?? 1000;
    };

    const poll = async () => {
      try {
        const latest = await fetcher();
        if (cancelled) return;
        setValue(latest);
        setError(null);
        if (isTerminal(latest)) {
          return;
        }
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "polling failed");
      }
      if (!cancelled) {
        timeoutId = setTimeout(poll, nextDelay());
      }
    };

    poll();

    return () => {
      cancelled = true;
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, restartKey]);

  return { value, error };
}
