import { defineConfig, devices } from "@playwright/test";

/**
 * E2E tests run against a live dev server (Next.js) + a live API (FastAPI).
 * In CI both are started before the test run.
 *
 * In local dev:
 *   pnpm --filter @app/web exec playwright test
 *
 * Requires:
 *   - Next.js dev server on localhost:3000  (pnpm --filter @app/web dev)
 *   - FastAPI on localhost:8000             (uvicorn main:app --reload)
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "list",

  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  // Start Next.js dev server automatically if not already running
  webServer: {
    command: "pnpm --filter @app/web dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
