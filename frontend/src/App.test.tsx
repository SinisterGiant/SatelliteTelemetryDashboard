import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import App from "./App";

const response = {
  data: [
    { satelliteId: "RL-001", timestamp: "2026-07-23T19:00:00.000Z", altitude: 450.5, velocity: 7.7, status: "healthy" },
  ],
  pagination: { page: 1, pageSize: 10, totalItems: 1, totalPages: 1, sortBy: "timestamp", sortOrder: "desc" },
};

describe("Satellite telemetry dashboard", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => response }));
    vi.stubGlobal("confirm", vi.fn().mockReturnValue(true));
  });

  afterEach(() => vi.unstubAllGlobals());

  it("loads and displays telemetry", async () => {
    render(<App />);
    expect(screen.getByText("Loading telemetry…")).toBeInTheDocument();
    expect(await screen.findByText("RL-001")).toBeInTheDocument();
    expect(screen.getByText("450.5")).toBeInTheDocument();
  });

  it("shows an API error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));
    render(<App />);
    expect(await screen.findByText("Telemetry unavailable")).toBeInTheDocument();
    expect(screen.getByText("The telemetry service is unreachable. Check that the API is running.")).toBeInTheDocument();
  });

  it("validates the add form before submitting", async () => {
    render(<App />);
    await screen.findByText("RL-001");
    fireEvent.click(screen.getByRole("button", { name: "Add telemetry" }));
    expect(screen.getByText("satelliteId is required.")).toBeInTheDocument();
    expect(screen.getAllByText("Use a finite number greater than zero.")).toHaveLength(2);
  });

  it("accepts decimal telemetry measurements and sends numbers", async () => {
    render(<App />);
    await screen.findByText("RL-001");
    fireEvent.change(screen.getByPlaceholderText("RL-021"), { target: { value: "RL-021" } });
    fireEvent.change(screen.getByPlaceholderText("450.5"), { target: { value: "11.11" } });
    fireEvent.change(screen.getByPlaceholderText("7.6"), { target: { value: "0.001" } });
    fireEvent.click(screen.getByRole("button", { name: "Add telemetry" }));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/telemetry"),
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"altitude":11.11'),
      }),
    ));
  });

  it("sends a delete request after confirmation", async () => {
    render(<App />);
    await screen.findByText("RL-001");
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/telemetry/RL-001"), expect.objectContaining({ method: "DELETE" })));
  });
});
