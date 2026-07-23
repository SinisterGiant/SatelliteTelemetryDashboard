export type TelemetryStatus = "healthy" | "degraded" | "critical";
export type SortField = "timestamp" | "altitude" | "velocity" | "satelliteId" | "status";
export type SortOrder = "asc" | "desc";

export interface TelemetryEntry {
  satelliteId: string;
  timestamp: string;
  altitude: number;
  velocity: number;
  status: TelemetryStatus;
}

export interface TelemetryQuery {
  satelliteId: string;
  status: TelemetryStatus | "";
  page: number;
  pageSize: number;
  sortBy: SortField;
  sortOrder: SortOrder;
}

export interface Pagination {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  sortBy: SortField;
  sortOrder: SortOrder;
}

export interface TelemetryListResponse {
  data: TelemetryEntry[];
  pagination: Pagination;
  summary: TelemetryStatusSummary;
}

export interface TelemetryStatusSummary {
  healthy: number;
  degraded: number;
  critical: number;
}

export interface TelemetryPayload {
  satelliteId: string;
  timestamp: string;
  altitude: number;
  velocity: number;
  status: TelemetryStatus;
}
