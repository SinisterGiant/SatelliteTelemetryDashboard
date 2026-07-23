import type { SortField, SortOrder, TelemetryEntry } from "../types";

interface Props {
  data: TelemetryEntry[];
  loading: boolean;
  deletingSatelliteId: string | null;
  sortBy: SortField;
  sortOrder: SortOrder;
  onSort: (field: SortField) => void;
  onDelete: (entry: TelemetryEntry) => void;
}

const headings: Array<{ label: string; field: SortField }> = [
  { label: "satelliteId", field: "satelliteId" },
  { label: "Timestamp", field: "timestamp" },
  { label: "Altitude", field: "altitude" },
  { label: "Velocity", field: "velocity" },
  { label: "Health status", field: "status" },
];

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "medium" }).format(new Date(value));
}

function SortButton({ label, field, activeField, order, onSort }: { label: string; field: SortField; activeField: SortField; order: SortOrder; onSort: (field: SortField) => void }) {
  const active = activeField === field;
  return (
    <button className={`sort-button ${active ? "active" : ""}`} type="button" onClick={() => onSort(field)}>
      {label} <span aria-hidden="true">{active ? (order === "asc" ? "↑" : "↓") : "↕"}</span>
    </button>
  );
}

export function TelemetryTable({ data, loading, deletingSatelliteId, sortBy, sortOrder, onSort, onDelete }: Props) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {headings.map((heading) => (
              <th key={heading.field} scope="col"><SortButton {...heading} activeField={sortBy} order={sortOrder} onSort={onSort} /></th>
            ))}
            <th scope="col"><span className="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr><td colSpan={6} className="table-message"><span className="spinner" /> Loading telemetry…</td></tr>
          ) : data.length === 0 ? (
            <tr><td colSpan={6} className="table-message">No telemetry matches these filters.</td></tr>
          ) : (
            data.map((entry) => (
              <tr key={entry.satelliteId}>
                <td className="satellite-cell"><span className="satellite-dot" />{entry.satelliteId}</td>
                <td className="timestamp-cell">{formatDate(entry.timestamp)}</td>
                <td>{entry.altitude.toLocaleString(undefined, { maximumFractionDigits: 2 })} <span className="unit">km</span></td>
                <td>{entry.velocity.toLocaleString(undefined, { maximumFractionDigits: 2 })} <span className="unit">km/s</span></td>
                <td><span className={`status status-${entry.status}`}>{entry.status}</span></td>
                <td className="action-cell"><button className="delete-button" type="button" onClick={() => onDelete(entry)} disabled={deletingSatelliteId === entry.satelliteId}>{deletingSatelliteId === entry.satelliteId ? "…" : "Delete"}</button></td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
