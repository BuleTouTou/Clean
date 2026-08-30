import * as generated from "./generated/services/general";

export type BatchKind = "sale" | "rent";
export interface SheetInfo { name: string; hidden: boolean; rows: number; cols: number; headerRow: number; preview: string[][]; }
export interface MappingSuggestion { source: string; target: string; confidence: number; reason: string; samples: string[]; }
export interface ReportItem { id: number; task_id: string; kind: BatchKind; original_name: string; entrust_date: string; started_at: string; completed_at: string; input_rows: number; output_rows: number; blocking_count: number; audit_count: number; source_url: string | null; source_object_key: string | null; output_file: string | null; output_url: string | null; output_object_key: string | null; report: Record<string, unknown>; }
export interface ReportsResponse { items: ReportItem[]; total: number; page: number; pageSize: number; }

function send<T>(method: PromiseLike<unknown>): Promise<T> {
  return Promise.resolve(method).then((data) => data as T);
}

export const api = {
  status: () => send<Record<string, unknown>>(generated.getStatus()),
  createTask: (kind: BatchKind) => send<{ taskId: string; headers: string[] }>(generated.createTask({ data: { kind } })),
  upload: (taskId: string, file: File) => send<Record<string, unknown>>(generated.uploadSourceFile({ data: file, headers: { "X-Task-Id": taskId, "X-Filename": encodeURIComponent(file.name) } })),
  selectSheet: (taskId: string, sheet: SheetInfo) => send<Record<string, any>>(generated.selectSheet({ data: { taskId, sheet: sheet.name, headerRow: sheet.headerRow } })),
  mapping: (taskId: string, mapping: Record<string, string>) => send<Record<string, any>>(generated.saveMapping({ data: { taskId, mapping } })),
  review: (taskId: string, selected: Record<string, string>, entrustDate: string) => send<{ ok: boolean }>(generated.reviewEstate({ data: { taskId, selected, entrustDate } })),
  buildingReview: (taskId: string, selected: Record<string, string>) => send<Record<string, any>>(generated.reviewBuilding({ data: { taskId, selected } })),
  buildingConfirm: (taskId: string, selected: Record<string, string>, entrustDate: string) => send<{ ok: boolean }>(generated.confirmBuilding({ data: { taskId, selected, entrustDate } })),
  export: (taskId: string, cleanOnly: boolean) => send<Record<string, any>>(generated.exportTask({ data: { taskId, cleanOnly } })),
  reports: (page: number, pageSize: number, kind?: BatchKind) => send<ReportsResponse>(generated.listReports({ params: { page, pageSize, ...(kind ? { kind } : {}) } })),
};
