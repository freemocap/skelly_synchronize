import type {
  Job,
  JobCreateResponse,
  SyncRequest,
  VideosResponse,
} from "./types";

export const API_BASE = "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  detail: string;
  stderr?: string;

  constructor(status: number, detail: string, stderr?: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.stderr = stderr;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);

  if (!response.ok) {
    let detail = response.statusText;
    let stderr: string | undefined;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        detail = body.detail;
      }
      if (typeof body?.stderr === "string") {
        stderr = body.stderr;
      }
    } catch {
      // response body wasn't JSON; fall back to statusText
    }
    throw new ApiError(response.status, detail, stderr);
  }

  return response.json() as Promise<T>;
}

export function getHealth(): Promise<{ status: string }> {
  return request("/health");
}

export function listVideos(folderPath: string): Promise<VideosResponse> {
  const query = new URLSearchParams({ folder_path: folderPath });
  return request(`/videos?${query.toString()}`);
}

export function createJob(req: SyncRequest): Promise<JobCreateResponse> {
  return request("/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export function getJob(jobId: string): Promise<Job> {
  return request(`/jobs/${jobId}`);
}

export function listJobs(): Promise<Job[]> {
  return request("/jobs");
}

export function cancelJob(jobId: string): Promise<Job> {
  return request(`/jobs/${jobId}`, { method: "DELETE" });
}

export function debugPlotUrl(jobId: string): string {
  return `${API_BASE}/jobs/${jobId}/debug-plot`;
}
