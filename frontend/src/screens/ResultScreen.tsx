import { debugPlotUrl } from "../api/client";
import { useJobPolling } from "../hooks/useJobPolling";
import { ErrorBanner } from "../components/ErrorBanner";
import "./ResultScreen.css";

interface ResultScreenProps {
  jobId: string;
  onRunAnother: () => void;
}

export function ResultScreen({ jobId, onRunAnother }: ResultScreenProps) {
  const { job, status, result, error } = useJobPolling(jobId);

  if (job === null) {
    return <p>Loading…</p>;
  }

  if (status === "failed" || status === "cancelled") {
    return (
      <section className="result-screen">
        <h2>Job {status}</h2>
        <ErrorBanner message={error ?? `job was ${status}`} />
        <button onClick={onRunAnother}>Run another sync</button>
      </section>
    );
  }

  if (result === null) {
    return <p>Loading result…</p>;
  }

  return (
    <section className="result-screen">
      <h2>Synchronization complete</h2>

      <table className="lag-table">
        <thead>
          <tr>
            <th>Video</th>
            <th>Lag (s)</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {result.lags.map((lag) => (
            <tr key={lag.video_name}>
              <td>{lag.video_name}</td>
              <td>{lag.lag_seconds.toFixed(3)}</td>
              <td>{lag.confidence !== null ? lag.confidence.toFixed(3) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {job.request.create_debug_artifacts && (
        <div className="debug-plot">
          <h3>Debug plot</h3>
          <img src={debugPlotUrl(jobId)} alt="Synchronization debug plot" />
        </div>
      )}

      <p className="output-path">
        Output folder: <span className="selectable">{result.synchronized_video_folder_path}</span>
      </p>

      <button onClick={onRunAnother}>Run another sync</button>
    </section>
  );
}
