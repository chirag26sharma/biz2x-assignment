import { defineConfig, devices } from "@playwright/test";
import path from "path";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";
const apiBase = process.env.PLAYWRIGHT_API_BASE ?? "http://localhost:5001";
const backendDir = path.join(__dirname, "..", "backend");
const isCI = Boolean(process.env.CI);

const backendCommand = isCI
  ? "python -m uvicorn app.main:app --host 127.0.0.1 --port 5001"
  : process.platform === "win32"
    ? ".venv\\Scripts\\python -m uvicorn app.main:app --host 127.0.0.1 --port 5001"
    : "python -m uvicorn app.main:app --host 127.0.0.1 --port 5001";

const frontendCommand = isCI
  ? "npm run build && npm run start -- -p 3000"
  : "npm run dev -- --port 3000";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  retries: isCI ? 1 : 0,
  reporter: isCI ? "github" : "list",
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  globalSetup: require.resolve("./e2e/global-setup.ts"),
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : [
        {
          command: backendCommand,
          cwd: backendDir,
          url: `${apiBase}/ready`,
          reuseExistingServer: !isCI,
          timeout: 120_000,
        },
        {
          command: frontendCommand,
          url: baseURL,
          reuseExistingServer: !isCI,
          timeout: isCI ? 180_000 : 120_000,
          env: {
            ...process.env,
            NEXT_PUBLIC_API_BASE: apiBase,
          },
        },
      ],
});
