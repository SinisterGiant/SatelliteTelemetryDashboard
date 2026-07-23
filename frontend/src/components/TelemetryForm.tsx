import { FormEvent, useState } from "react";

import type { TelemetryPayload, TelemetryStatus } from "../types";

interface Props {
  submitting: boolean;
  onSubmit: (payload: TelemetryPayload) => Promise<void>;
}

interface FormState {
  satelliteId: string;
  timestamp: string;
  altitude: string;
  velocity: string;
  status: TelemetryStatus;
}

function localDateTimeValue(date: Date) {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

const initialForm = (): FormState => ({
  satelliteId: "",
  timestamp: localDateTimeValue(new Date()),
  altitude: "",
  velocity: "",
  status: "healthy",
});

function parsePositiveNumber(value: string): number | null {
  const normalized = value.trim();
  if (!normalized) return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function TelemetryForm({ submitting, onSubmit }: Props) {
  const [form, setForm] = useState<FormState>(initialForm);
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors: Partial<Record<keyof FormState, string>> = {};
    const altitude = parsePositiveNumber(form.altitude);
    const velocity = parsePositiveNumber(form.velocity);
    if (!form.satelliteId.trim()) nextErrors.satelliteId = "satelliteId is required.";
    else if (form.satelliteId.trim().length > 64) nextErrors.satelliteId = "Use 64 characters or fewer.";
    if (!form.timestamp || Number.isNaN(new Date(form.timestamp).getTime())) nextErrors.timestamp = "Enter a valid timestamp.";
    if (altitude === null) nextErrors.altitude = "Use a finite number greater than zero.";
    if (velocity === null) nextErrors.velocity = "Use a finite number greater than zero.";
    setErrors(nextErrors);
    if (altitude === null || velocity === null || Object.keys(nextErrors).length > 0) return;

    try {
      await onSubmit({
        satelliteId: form.satelliteId.trim(),
        timestamp: new Date(form.timestamp).toISOString(),
        altitude,
        velocity,
        status: form.status,
      });
      setForm(initialForm());
    } catch (error) {
      setErrors({ satelliteId: error instanceof Error ? error.message : "Unable to save telemetry." });
    }
  }

  function update(field: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  }

  return (
    <section className="panel form-panel" aria-labelledby="add-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Manual entry</p>
          <h2 id="add-title">Add telemetry</h2>
        </div>
        <span className="orbit-mark" aria-hidden="true">+</span>
      </div>
      <form onSubmit={handleSubmit} noValidate>
        <label>
          <span>Satellite ID</span>
          <input value={form.satelliteId} onChange={(event) => update("satelliteId", event.target.value)} placeholder="RL-021" />
          {errors.satelliteId && <small className="field-error">{errors.satelliteId}</small>}
        </label>
        <label>
          <span>Timestamp</span>
          <input type="datetime-local" value={form.timestamp} onChange={(event) => update("timestamp", event.target.value)} />
          {errors.timestamp && <small className="field-error">{errors.timestamp}</small>}
        </label>
        <div className="form-grid">
          <label>
            <span>Altitude <em>km</em></span>
            <input type="text" inputMode="decimal" value={form.altitude} onChange={(event) => update("altitude", event.target.value)} placeholder="450.5" aria-invalid={Boolean(errors.altitude)} />
            {errors.altitude && <small className="field-error">{errors.altitude}</small>}
          </label>
          <label>
            <span>Velocity <em>km/s</em></span>
            <input type="text" inputMode="decimal" value={form.velocity} onChange={(event) => update("velocity", event.target.value)} placeholder="7.6" aria-invalid={Boolean(errors.velocity)} />
            {errors.velocity && <small className="field-error">{errors.velocity}</small>}
          </label>
        </div>
        <label>
          <span>Health status</span>
          <select value={form.status} onChange={(event) => update("status", event.target.value)}>
            <option value="healthy">Healthy</option>
            <option value="degraded">Degraded</option>
            <option value="critical">Critical</option>
          </select>
        </label>
        <button className="button button-primary submit-button" type="submit" disabled={submitting}>
          {submitting ? "Saving…" : "Add telemetry"}
        </button>
      </form>
    </section>
  );
}
