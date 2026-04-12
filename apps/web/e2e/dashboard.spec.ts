/**
 * E2E: Dashboard
 *
 * Verifies the dashboard renders correctly with mocked data.
 */

import { expect, test } from "@playwright/test";

const MOCK_STRATEGIES = [
  {
    id: "s1", name: "My EMA Strategy", description: "EMA crossover",
    blocks: [], python_code: null, user_id: null,
    created_at: "2024-01-01T00:00:00", updated_at: "2024-01-01T00:00:00",
  },
];

const MOCK_RUNS = [
  {
    id: "r1", strategy_id: "s1", strategy_name: "My EMA Strategy",
    data_config: { source: "yahoo", symbol: "AAPL", asset_class: "stock", timeframe: "1d", start_date: "2023-01-01", end_date: "2023-12-31" },
    status: "completed", engine: "simple",
    metrics: { sharpe_ratio: 0.95, sortino_ratio: 1.1, cagr: 0.12, max_drawdown: -0.08, win_rate: 0.55, total_trades: 12, profit_factor: 1.4, final_value: 112000 },
    equity_curve: null, trades: null,
    error_message: null, log_output: "Done.",
    created_at: "2024-01-02T10:00:00", completed_at: "2024-01-02T10:00:02",
  },
];

test.describe("Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/strategies**", async (route) => {
      await route.fulfill({ json: MOCK_STRATEGIES });
    });
    await page.route("**/backtests**", async (route) => {
      await route.fulfill({ json: MOCK_RUNS });
    });
  });

  test("renders dashboard heading", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();
  });

  test("shows strategy count stat", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByText("Strategies")).toBeVisible();
    await expect(page.getByText("1")).toBeVisible();
  });

  test("shows completed run with final value", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByText("My EMA Strategy")).toBeVisible();
    await expect(page.getByText("$112,000")).toBeVisible();
  });

  test("new strategy CTA navigates correctly", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("link", { name: /new strategy/i }).click();
    await expect(page).toHaveURL(/\/strategies\/new/);
  });

  test("root redirect lands on dashboard", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();
  });
});
