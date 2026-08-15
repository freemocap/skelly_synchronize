import { useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { ApiError, createJob } from "../api/client";
import type { SyncMethod, VideoBackendKind } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import "./SetupScreen.css";

interface SetupScreenProps {
  onJobCreated: (jobId: string) => void;
}

export function SetupScreen({ onJobCreated }: SetupScreenProps) {
  const [rawFolderPath, setRawFolderPath] = useState("");
  const [outputFolderPath, setOutputFolderPath] = useState("");
  const [method, setMethod] = useState<SyncMethod>("audio cross-correlation");
  const [videoHandler, setVideoHandler] = useState<VideoBackendKind>("deffcode");
  const [brightnessRatioThreshold, setBrightnessRatioThreshold] = useState(1000);
  const [createDebugArtifacts, setCreateDebugArtifacts] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleBrowse = async (setPath: (path: string) => void) => {
    const selected = await open({ directory: true, multiple: false });
    if (typeof selected === "string") {
      setPath(selected);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    try {
      const response = await createJob({
        raw_video_folder_path: rawFolderPath,
        synchronized_video_folder_path: outputFolderPath.trim() || null,
        method,
        video_handler: videoHandler,
        brightness_ratio_threshold: brightnessRatioThreshold,
        create_debug_artifacts: createDebugArtifacts,
      });
      onJobCreated(response.job_id);
    } catch (e) {
      setSubmitError(e instanceof ApiError ? e.detail : "failed to start sync job");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="setup-screen">
      <h2>New synchronization</h2>
      <ErrorBanner message={submitError} />
      <form onSubmit={handleSubmit}>
        <label>
          Raw video folder path
          <div className="path-input-row">
            <input
              type="text"
              value={rawFolderPath}
              onChange={(e) => setRawFolderPath(e.target.value)}
              placeholder="/path/to/raw_videos"
              required
            />
            <button
              type="button"
              onClick={() => handleBrowse(setRawFolderPath)}
            >
              Browse…
            </button>
          </div>
        </label>

        <label>
          Sync method
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value as SyncMethod)}
          >
            <option value="audio cross-correlation">Audio cross-correlation</option>
            <option value="brightness change detection">
              Brightness change detection
            </option>
          </select>
        </label>

        {method === "brightness change detection" && (
          <label>
            Brightness ratio threshold
            <input
              type="number"
              value={brightnessRatioThreshold}
              onChange={(e) => setBrightnessRatioThreshold(Number(e.target.value))}
              step="any"
            />
          </label>
        )}

        <label>
          Video backend
          <select
            value={videoHandler}
            onChange={(e) => setVideoHandler(e.target.value as VideoBackendKind)}
          >
            <option value="deffcode">deffcode</option>
            <option value="ffmpeg">ffmpeg</option>
          </select>
        </label>

        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={createDebugArtifacts}
            onChange={(e) => setCreateDebugArtifacts(e.target.checked)}
          />
          Create debug artifacts
        </label>

        <label>
          Output folder path (optional)
          <div className="path-input-row">
            <input
              type="text"
              value={outputFolderPath}
              onChange={(e) => setOutputFolderPath(e.target.value)}
              placeholder="defaults to a synchronized_videos folder next to the raw folder"
            />
            <button
              type="button"
              onClick={() => handleBrowse(setOutputFolderPath)}
            >
              Browse…
            </button>
          </div>
        </label>

        <button type="submit" disabled={submitting}>
          {submitting ? "Starting…" : "Start sync"}
        </button>
      </form>
    </section>
  );
}
