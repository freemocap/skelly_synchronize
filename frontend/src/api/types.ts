export type VideoBackendKind = "ffmpeg" | "deffcode";

export type SyncMethod = "audio cross-correlation" | "brightness change detection";

export type JobStatus = "pending" | "running" | "succeeded" | "failed" | "cancelled";

export interface VideoInfo {
  filepath: string;
  video_name: string;
  duration_seconds: number;
  fps: number;
  frame_count: number | null;
}

export interface LagResult {
  video_name: string;
  lag_seconds: number;
  confidence: number | null;
}

export interface SyncRequest {
  raw_video_folder_path: string;
  synchronized_video_folder_path?: string | null;
  method: SyncMethod;
  video_handler: VideoBackendKind;
  brightness_ratio_threshold: number;
  create_debug_artifacts: boolean;
}

export interface SyncResult {
  synchronized_video_folder_path: string;
  videos_before: VideoInfo[];
  videos_after: VideoInfo[];
  lags: LagResult[];
  debug_artifact_paths: string[];
  elapsed_seconds: number;
  synchronized_frame_count: number | null;
}

export interface Job {
  id: string;
  status: JobStatus;
  progress: number;
  progress_message: string | null;
  created_at: string;
  updated_at: string;
  request: SyncRequest;
  result: SyncResult | null;
  error: string | null;
}

export interface JobCreateResponse {
  job_id: string;
  status: JobStatus;
}

export interface VideoPreview {
  video_name: string;
  filepath: string;
}

export interface VideosResponse {
  folder_path: string;
  videos: VideoPreview[];
}
