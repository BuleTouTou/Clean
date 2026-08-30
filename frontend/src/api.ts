export type BatchKind = "sale" | "rent";

export interface FileStatus {
  key: string;
  name: string;
  exists: boolean;
  size: number;
  mtime: number | null;
}

export interface SheetInfo {
  name: string;
  hidden: boolean;
  rows: number;
  cols: number;
  headerRow: number;
  preview: string[][];
  encoding?: string;
  delimiter?: string;
}

export interface MappingSuggestion {
  source: string;
  target: string;
  confidence: number;
  reason: string;
  samples: string[];
}

export interface StatusResponse {
  files: FileStatus[];
  tasks: number;
}

export interface TaskResponse {
  taskId: string;
  headers: string[];
}

export interface UploadResponse {
  sheets: SheetInfo[];
  received: { name: string; size: number; sizeMB: number };
}

export interface SelectSheetResponse {
  headers: string[];
  rows: number;
  suggestions: MappingSuggestion[];
  targets: string[];
}

export interface ApiError {
  error?: string;
  detail?: string;
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const text = await response.text();
  let payload: T | ApiError;
  try {
    payload = JSON.parse(text) as T | ApiError;
  } catch {
    throw new Error(response.status === 404 ? "当前端口运行的是旧版服务，请重新启动工具" : "服务器返回了无法识别的内容");
  }
  if (!response.ok) {
    const error = payload as ApiError;
    throw new Error(error.error ?? error.detail ?? "请求失败");
  }
  return payload as T;
}

export const api = {
  status: () => request<StatusResponse>("/api/status"),
  createTask: (kind: BatchKind) => request<TaskResponse>("/api/task", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind }),
  }),
  upload: (taskId: string, file: File) => request<UploadResponse>("/api/upload", {
    method: "POST",
    headers: { "X-Task-Id": taskId, "X-Filename": encodeURIComponent(file.name) },
    body: file,
  }),
  selectSheet: (taskId: string, sheet: SheetInfo) => request<SelectSheetResponse>("/api/select-sheet", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ taskId, sheet: sheet.name, headerRow: sheet.headerRow }),
  }),
};
