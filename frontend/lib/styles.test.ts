import { describe, expect, it } from "vitest";
import { categoryClass, severityClass } from "./styles";

describe("severityClass", () => {
  it("maps known severities", () => {
    expect(severityClass("Critical")).toBe("sev-critical");
    expect(severityClass("High")).toBe("sev-high");
    expect(severityClass("Medium")).toBe("sev-medium");
    expect(severityClass("Low")).toBe("sev-low");
  });

  it("defaults unknown severity to info", () => {
    expect(severityClass("Unknown")).toBe("sev-info");
  });
});

describe("categoryClass", () => {
  it("maps risk categories", () => {
    expect(categoryClass("Critical")).toBe("sev-critical");
    expect(categoryClass("High Risk")).toBe("sev-high");
    expect(categoryClass("Watchlist")).toBe("sev-medium");
  });

  it("defaults low and unknown categories to info", () => {
    expect(categoryClass("Low")).toBe("sev-info");
    expect(categoryClass("Something else")).toBe("sev-info");
  });
});
