import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DpdTrendChart } from "./DpdTrendChart";

describe("DpdTrendChart", () => {
  it("shows empty state when no payments", () => {
    render(<DpdTrendChart payments={[]} />);
    expect(screen.getByText("No payment history to chart.")).toBeInTheDocument();
  });

  it("shows worsening trend when DPD rises more than 5 days", () => {
    render(
      <DpdTrendChart
        payments={[
          { due_date: "2026-04-01", days_past_due: 0, status: "on_time" },
          { due_date: "2026-05-01", days_past_due: 4, status: "late" },
          { due_date: "2026-06-01", days_past_due: 12, status: "late" },
        ]}
      />,
    );

    expect(screen.getByTestId("dpd-trend-chart")).toBeInTheDocument();
    expect(screen.getByText("Worsening")).toBeInTheDocument();
    expect(screen.getByText("12 days")).toBeInTheDocument();
  });

  it("shows stable trend when DPD change is within 5 days", () => {
    render(
      <DpdTrendChart
        payments={[
          { due_date: "2026-04-01", days_past_due: 5, status: "late" },
          { due_date: "2026-05-01", days_past_due: 7, status: "late" },
          { due_date: "2026-06-01", days_past_due: 8, status: "late" },
        ]}
      />,
    );

    expect(screen.getByText("Stable")).toBeInTheDocument();
    expect(screen.getByTestId("dpd-trend-chart")).toBeInTheDocument();
  });
});
