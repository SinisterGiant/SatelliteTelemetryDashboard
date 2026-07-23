import type {
  TelemetryEntry,
  TelemetryListResponse,
  TelemetryPayload,
  TelemetryQuery,
} from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json", ...init?.headers },
      ...init,
    });
  } catch {
    throw new ApiError("The telemetry service is unreachable. Check that the API is running.", 0);
  }

  if (!response.ok) {
    let message = `The request failed with status ${response.status}.`;
    try {
      const body = (await response.json()) as { error?: { message?: string } };
      message = body.error?.message || message;
    } catch {
      // Keep the generic status message when the server did not return JSON.
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function getTelemetry(query: TelemetryQuery, signal?: AbortSignal) {
  const params = new URLSearchParams();
  if (query.satelliteId) params.set("satelliteId", query.satelliteId);
  if (query.status) params.set("status", query.status);
  params.set("page", String(query.page));
  params.set("pageSize", String(query.pageSize));
  params.set("sortBy", query.sortBy);
  params.set("sortOrder", query.sortOrder);
  return request<TelemetryListResponse>(`/telemetry?${params.toString()}`, { signal });
}

export function createTelemetry(payload: TelemetryPayload) {
  return request<{ data: TelemetryEntry }>("/telemetry", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteTelemetry(satelliteId: string) {
  return request<void>(`/telemetry/${encodeURIComponent(satelliteId)}`, { method: "DELETE" });
}
