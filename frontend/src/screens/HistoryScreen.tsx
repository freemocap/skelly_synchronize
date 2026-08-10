import { useEffect, useState } from "react";
import { ApiError, listJobs } from "../api/client";
import type { Job } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import "./HistoryScreen.css";

interface HistoryScreenProps {
  onSelectJob: (jobId: string) => void;
  onBackToSetup: () => void;
}

export function HistoryScreen({ onSelectJob, onBackToSetup }: HistoryScreenProps) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    listJobs()
      .then(setJobs)
      .catch((e) =>
        setLoadError(e instanceof ApiError ? e.detail : "failed to load job history"),
      );
  }, []);

  return (
    <section className="history-screen">
      <h2>Job history</h2>
      <ErrorBanner message={loadError} />

      {jobs.length === 0 && loadError === null && <p>No jobs yet.</p>}

      {jobs.length > 0 && (
        <table className="history-table">
          <thead>
            <tr>
              <th>Created</th>
              <th>Method</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id} onClick={() => onSelectJob(job.id)}>
                <td>{new Date(job.created_at).toLocaleString()}</td>
                <td>{job.request.method}</td>
                <td>{job.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <button onClick={onBackToSetup}>Back to setup</button>
    </section>
  );
}
