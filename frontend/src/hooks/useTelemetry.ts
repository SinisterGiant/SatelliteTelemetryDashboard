import { useCallback, useEffect, useReducer } from "react";

import { createTelemetry, deleteTelemetry, getTelemetry } from "../api";
import type { TelemetryEntry, TelemetryPayload, TelemetryQuery, TelemetryListResponse } from "../types";

interface State {
  data: TelemetryEntry[];
  pagination: TelemetryListResponse["pagination"] | null;
  loading: boolean;
  error: string | null;
  submitting: boolean;
  deletingSatelliteId: string | null;
  refreshToken: number;
}

type Action =
  | { type: "fetch-start" }
  | { type: "fetch-success"; payload: TelemetryListResponse }
  | { type: "fetch-error"; message: string }
  | { type: "submit-start" }
  | { type: "submit-end" }
  | { type: "delete-start"; satelliteId: string }
  | { type: "delete-end" }
  | { type: "refresh" };

const initialState: State = {
  data: [],
  pagination: null,
  loading: true,
  error: null,
  submitting: false,
  deletingSatelliteId: null,
  refreshToken: 0,
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "fetch-start":
      return { ...state, loading: true, error: null };
    case "fetch-success":
      return { ...state, loading: false, error: null, data: action.payload.data, pagination: action.payload.pagination };
    case "fetch-error":
      return { ...state, loading: false, error: action.message };
    case "submit-start":
      return { ...state, submitting: true };
    case "submit-end":
      return { ...state, submitting: false };
    case "delete-start":
      return { ...state, deletingSatelliteId: action.satelliteId };
    case "delete-end":
      return { ...state, deletingSatelliteId: null };
    case "refresh":
      return { ...state, refreshToken: state.refreshToken + 1 };
    default:
      return state;
  }
}

export function useTelemetry(query: TelemetryQuery) {
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    const controller = new AbortController();
    dispatch({ type: "fetch-start" });
    getTelemetry(query, controller.signal)
      .then((payload) => dispatch({ type: "fetch-success", payload }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        if (error instanceof Error) dispatch({ type: "fetch-error", message: error.message });
        else dispatch({ type: "fetch-error", message: "Unable to load telemetry." });
      });
    return () => controller.abort();
  }, [query.page, query.pageSize, query.satelliteId, query.sortBy, query.sortOrder, query.status, state.refreshToken]);

  const add = useCallback(async (payload: TelemetryPayload) => {
    dispatch({ type: "submit-start" });
    try {
      await createTelemetry(payload);
      dispatch({ type: "refresh" });
    } finally {
      dispatch({ type: "submit-end" });
    }
  }, []);

  const remove = useCallback(async (satelliteId: string) => {
    dispatch({ type: "delete-start", satelliteId });
    try {
      await deleteTelemetry(satelliteId);
      dispatch({ type: "refresh" });
    } finally {
      dispatch({ type: "delete-end" });
    }
  }, []);

  const refresh = useCallback(() => dispatch({ type: "refresh" }), []);

  return { ...state, add, remove, refresh };
}
