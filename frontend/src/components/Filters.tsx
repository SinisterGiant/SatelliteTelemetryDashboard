import type { TelemetryQuery, TelemetryStatus } from "../types";

interface Props {
  filters: Pick<TelemetryQuery, "satelliteId" | "status">;
  onChange: (filters: Pick<TelemetryQuery, "satelliteId" | "status">) => void;
  onClear: () => void;
}

export function Filters({ filters, onChange, onClear }: Props) {
  return (
    <section className="panel filters-panel" aria-labelledby="filters-title">
      <div>
        <p className="eyebrow">Telemetry stream</p>
        <h2 id="filters-title">Find a signal</h2>
      </div>
      <div className="filter-controls">
        <label>
          <span>Satellite ID</span>
          <input
            value={filters.satelliteId}
            onChange={(event) => onChange({ ...filters, satelliteId: event.target.value })}
            placeholder="e.g. RL-001"
            aria-label="Filter by satelliteId"
          />
        </label>
        <label>
          <span>Health status</span>
          <select
            value={filters.status}
            onChange={(event) => onChange({ ...filters, status: event.target.value as TelemetryStatus | "" })}
            aria-label="Filter by health status"
          >
            <option value="">All statuses</option>
            <option value="healthy">Healthy</option>
            <option value="degraded">Degraded</option>
            <option value="critical">Critical</option>
          </select>
        </label>
        <button className="button button-quiet" type="button" onClick={onClear}>
          Clear filters
        </button>
      </div>
    </section>
  );
}
