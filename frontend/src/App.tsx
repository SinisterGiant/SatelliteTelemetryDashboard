import { useEffect, useMemo, useState } from "react";

import { ApiError } from "./api";
import { Filters } from "./components/Filters";
import { Pagination } from "./components/Pagination";
import { TelemetryForm } from "./components/TelemetryForm";
import { TelemetryTable } from "./components/TelemetryTable";
import { useTelemetry } from "./hooks/useTelemetry";
import type { SortField, TelemetryEntry, TelemetryQuery, TelemetryStatus } from "./types";
import "./styles.css";

function useDebouncedValue(value: string, delay: number) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [delay, value]);
  return debounced;
}

function App() {
  const [filters, setFilters] = useState({ satelliteId: "", status: "" as TelemetryStatus | "" });
  const debouncedSatelliteId = useDebouncedValue(filters.satelliteId, 250);
  const [query, setQuery] = useState<TelemetryQuery>({
    satelliteId: "",
    status: "",
    page: 1,
    pageSize: 10,
    sortBy: "timestamp",
    sortOrder: "desc",
  });

  useEffect(() => {
    setQuery((current) => ({ ...current, satelliteId: debouncedSatelliteId.trim(), page: 1 }));
  }, [debouncedSatelliteId]);

  useEffect(() => {
    setQuery((current) => ({ ...current, status: filters.status, page: 1 }));
  }, [filters.status]);

  const telemetry = useTelemetry(query);
  const totalItems = telemetry.pagination?.totalItems ?? 0;
  const statusSummary = useMemo(() => {
    const counts = { healthy: 0, degraded: 0, critical: 0 };
    telemetry.data.forEach((entry) => { counts[entry.status] += 1; });
    return counts;
  }, [telemetry.data]);

  function handleSort(field: SortField) {
    setQuery((current) => ({
      ...current,
      page: 1,
      sortBy: field,
      sortOrder: current.sortBy === field && current.sortOrder === "asc" ? "desc" : "asc",
    }));
  }

  function handleDelete(entry: TelemetryEntry) {
    if (window.confirm(`Delete telemetry from ${entry.satelliteId}?`)) {
      void telemetry.remove(entry.satelliteId).catch(() => undefined);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-orbit" aria-hidden="true">◉</span><span>GROUND / LINK</span></div>
        <span className="connection"><span className="connection-dot" /> Local telemetry node</span>
      </header>

      <main>
        <section className="hero">
          <div>
            <p className="eyebrow">Mission control / live view</p>
            <h1>Satellite telemetry</h1>
            <p className="hero-copy">A clear read on the fleet, from orbit to operator.</p>
          </div>
          <div className="hero-stamp"><span>UTC</span><strong>{new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</strong></div>
        </section>

        <section className="summary-grid" aria-label="Telemetry summary">
          <div className="summary-card"><span className="summary-label">Visible signals</span><strong>{totalItems}</strong><span className="summary-note">matching current view</span></div>
          <div className="summary-card"><span className="summary-label">Healthy</span><strong className="healthy-number">{statusSummary.healthy}</strong><span className="summary-note">nominal condition</span></div>
          <div className="summary-card"><span className="summary-label">Needs attention</span><strong className="critical-number">{statusSummary.degraded + statusSummary.critical}</strong><span className="summary-note">degraded or critical</span></div>
        </section>

        <div className="content-grid">
          <div className="main-column">
            <Filters filters={filters} onChange={setFilters} onClear={() => setFilters({ satelliteId: "", status: "" })} />
            {telemetry.error && <div className="alert" role="alert"><div><strong>Telemetry unavailable</strong><span>{telemetry.error}</span></div><button className="button button-quiet" type="button" onClick={telemetry.refresh}>Retry</button></div>}
            <section className="panel table-panel" aria-labelledby="table-title">
              <div className="panel-heading table-heading"><div><p className="eyebrow">Downlink records</p><h2 id="table-title">Latest readings</h2></div><span className="record-count">{totalItems} records</span></div>
              <TelemetryTable data={telemetry.data} loading={telemetry.loading} deletingSatelliteId={telemetry.deletingSatelliteId} sortBy={query.sortBy} sortOrder={query.sortOrder} onSort={handleSort} onDelete={handleDelete} />
              <Pagination page={telemetry.pagination?.page ?? query.page} totalPages={telemetry.pagination?.totalPages ?? 0} totalItems={totalItems} onPageChange={(page) => setQuery((current) => ({ ...current, page }))} />
            </section>
          </div>
          <aside><TelemetryForm submitting={telemetry.submitting} onSubmit={telemetry.add} /></aside>
        </div>
      </main>
      <footer>LOCAL POC <span>•</span> TELEMETRY OPERATIONS</footer>
    </div>
  );
}

export default App;
