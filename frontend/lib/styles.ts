export function severityClass(severity: string): string {
  switch (severity) {
    case "Critical":
      return "sev-critical";
    case "High":
      return "sev-high";
    case "Medium":
      return "sev-medium";
    case "Low":
      return "sev-low";
    default:
      return "sev-info";
  }
}

export function categoryClass(category: string): string {
  switch (category) {
    case "Critical":
      return "sev-critical";
    case "High Risk":
      return "sev-high";
    case "Watchlist":
      return "sev-medium";
    default:
      return "sev-info";
  }
}
