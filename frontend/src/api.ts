import * as generated from "./generated/services/general";

export type BatchKind = "sale" | "rent";
export interface SheetInfo { name: string; hidden: boolean; rows: number; cols: number; headerRow: number; preview: string[][]; }
export interface MappingSuggestion { source: string; target: string; confidence: number; reason: string; samples: string[]; }
export interface UploadResponse { sheets: SheetInfo[]; received: { name: string; size: number; sizeMB: number }; }
export interface SelectSheetResponse { targets: string[]; suggestions: MappingSuggestion[]; }
export type EstateSelectionMethod = "manual" | "batch-all" | "batch-compatible";
export interface EstateReviewBuilding { key: string; rawBuilding: string; rows: number[]; candidateIds: string[]; }
export interface EstateReviewCandidate {
  id: string;
  outputName: string;
  estate: string;
  phase: string;
  district: string;
  businessArea: string;
  score: number;
  compatibleBuildingKeys: string[];
  uniqueBuildingKeys: string[];
  unknownBuildingKeys: string[];
  coverageCount: number;
  uniqueCoverageCount: number;
  conflictCount: number;
  canApplyAll: boolean;
  canApplyCompatible: boolean;
}
export interface EstateReviewGroup {
  key: string;
  raw: string;
  rawVariants: string[];
  rows: number[];
  buildings: EstateReviewBuilding[];
  buildingCount: number;
  unresolvedCount: number;
  candidates: EstateReviewCandidate[];
}
export interface MappingResponse { reviews: EstateReviewGroup[]; errors: Array<Record<string, unknown>>; autoCount: number; }
export interface BuildingReviewItem { key: string; estate: string; base_estate: string; raw: string; rows: number[]; candidates: string[]; reason: string; selected: string; }
export interface BuildingReviewResponse { reviews: BuildingReviewItem[]; }
export interface ExportResponse {
  file: string | null;
  downloadId: string | null;
  ossUrl: string | null;
  downloadUrl: string | null;
  ossObjectKey: string | null;
  report: { 最终输出记录数: number; 阻断异常数量: number; [key: string]: unknown };
  audit: number;
  exceptions: Array<Record<string, unknown>>;
}
export interface ReportItem { id: number; user_id: number | null; owner: { id: number; username: string; name: string } | null; task_id: string; kind: BatchKind; original_name: string; entrust_date: string; started_at: string; completed_at: string; input_rows: number; output_rows: number; blocking_count: number; audit_count: number; source_url: string | null; source_object_key: string | null; output_file: string | null; output_url: string | null; output_object_key: string | null; report: Record<string, unknown>; }
export interface ReportsResponse { items: ReportItem[]; total: number; page: number; pageSize: number; }
export interface UserInfo { id: number; username: string; name: string; role: "admin" | "user"; mustChangePassword: boolean; isActive: boolean; createdAt: string; }

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(url, {
    ...options,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `请求失败（${response.status}）`);
  return data as T;
}

function send<T>(method: PromiseLike<unknown>): Promise<T> {
  return Promise.resolve(method).then((data) => data as T);
}

export const api = {
  login: (username: string, password: string) => request<{ user: UserInfo }>("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  me: () => request<{ user: UserInfo }>("/api/auth/me"),
  changePassword: (currentPassword: string, newPassword: string) => request<{ ok: boolean; user: UserInfo }>("/api/auth/change-password", { method: "POST", body: JSON.stringify({ currentPassword, newPassword }) }),
  logout: () => request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
  users: () => request<{ items: UserInfo[] }>("/api/users"),
  createUser: (username: string, name: string, initialPassword: string) => request<{ user: UserInfo }>("/api/users", { method: "POST", body: JSON.stringify({ username, name, initialPassword }) }),
  resetUserPassword: (userId: number, initialPassword: string) => request<{ user: UserInfo }>(`/api/users/${encodeURIComponent(String(userId))}/reset-password`, { method: "POST", body: JSON.stringify({ initialPassword }) }),
  status: () => send<Record<string, unknown>>(generated.getStatus()),
  createTask: (kind: BatchKind) => send<{ taskId: string; headers: string[] }>(generated.createTask({ data: { kind } })),
  upload: (taskId: string, file: File) => {
    // Alova's fetch adapter does not treat File as a special request body in
    // all environments and may JSON-serialize it to `{}`. Wrap it as Blob so
    // the original XLSX bytes are sent unchanged.
    const body = new Blob([file], { type: file.type || "application/octet-stream" });
    return send<UploadResponse>(
      generated.uploadSourceFile({
        data: body,
        headers: {
          "Content-Type": body.type,
          "X-Task-Id": taskId,
          "X-Filename": encodeURIComponent(file.name),
        },
      }),
    );
  },
  selectSheet: (taskId: string, sheet: SheetInfo) => send<SelectSheetResponse>(generated.selectSheet({ data: { taskId, sheet: sheet.name, headerRow: sheet.headerRow } })),
  mapping: (taskId: string, mapping: Record<string, string>) => send<MappingResponse>(generated.saveMapping({ data: { taskId, mapping } })),
  review: (taskId: string, selected: Record<string, string>, entrustDate: string, selectionMethods: Record<string, EstateSelectionMethod> = {}) => send<{ ok: boolean }>(generated.reviewEstate({ data: { taskId, selected, selectionMethods, entrustDate } })),
  buildingReview: (taskId: string, selected: Record<string, string>, selectionMethods: Record<string, EstateSelectionMethod> = {}) => send<BuildingReviewResponse>(generated.reviewBuilding({ data: { taskId, selected, selectionMethods } })),
  buildingConfirm: (taskId: string, selected: Record<string, string>, entrustDate: string) => send<{ ok: boolean }>(generated.confirmBuilding({ data: { taskId, selected, entrustDate } })),
  export: (taskId: string, cleanOnly: boolean) => send<ExportResponse>(generated.exportTask({ data: { taskId, cleanOnly } })),
  reports: (page: number, pageSize: number, kind?: BatchKind, ownerSearch?: string) => send<ReportsResponse>(generated.listReports({ params: { page, pageSize, ...(kind ? { kind } : {}), ...(ownerSearch ? { ownerSearch } : {}) } })),
};
