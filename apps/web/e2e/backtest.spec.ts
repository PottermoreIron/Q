/**
 * E2E: Run Backtest + Results Explorer flow
 *
 * Critical path: select strategy → configure data → run → see results.
 * The API is mocked at the network layer so no live data fetch is needed.
 */

import { expect, test } from "@playwright/test";

// Shared mock strategy + run response
const MOCK_STRATEGY = {
  id: "e2e-strategy-1",
  name: "E2E EMA Crossover",
  description: null,
  blocks: [],
  python_code: "import pandas as pd\ndef run(ohlcv):\n    close = ohlcv['close']\n    fast = close.ewm(span=5).mean()\n    slow = close.ewm(span=20).mean()\n    return {'entries': fast > slow, 'exits': fast < slow}\n",
  user_id: null,
  created_at: "2024-01-01T00:00:00",
  updated_at: "2024-01-01T00:00:00",
};

const MOCK_RUN = {
  id: "e2e-run-1",
  strategy_id: "e2e-strategy-1",
  strategy_name: "E2E EMA Crossover",
  data_config: {
    source: "yahoo", symbol: "AAPL", asset_class: "stock",
    timeframe: "1d", start_date: "2023-01-01", end_date: "2023-12-31",
  },
  status: "completed",
  engine: "simple",
  metrics: {
    sharpe_ratio: 1.23,
    sortino_ratio: 1.85,
    cagr: 0.18,
    max_drawdown: -0.12,
    win_rate: 0.6,
    total_trades: 15,
    profit_factor: 1.8,
    final_value: 118000,
  },
  equity_curve: Array.from({ length: 50 }, (_, i) => [
    new Date(2023, 0, i + 1).toISOString(),
    100_000 + i * 360,
  ]),
  trades: [
    { entry_price: 130.5, exit_price: 145.2, pnl: 1130, side: "long" },
    { entry_price: 148.0, exit_price: 142.3, pnl: -570, side: "long" },
  ],
  error_message: null,
  log_output: "Ran 252 bars inline. 15 trades.",
  created_at: "2024-01-01T10:00:00",
  completed_at: "2024-01-01T10:00:01",
};

test.describe("Run Backtest", () => {
  test.beforeEach(async ({ page }) => {
    // Mock the API so tests don't need a live backend
    await page.route("**/strategies**", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({ json: [MOCK_STRATEGY] });
      } else {
        await route.continue();
      }
    });

    await page.route("**/backtests**", async (route) => {
      const method = route.request().method();
      if (method === "POST") {
        await route.fulfill({ status: 201, json: MOCK_RUN });
      } else if (method === "GET") {
        await route.fulfill({ json: [MOCK_RUN] });
      } else {
        await route.continue();
      }
    });

    await page.route("**/backtests/e2e-run-1", async (route) => {
      await route.fulfill({ json: MOCK_RUN });
    });
  });

  test("run page loads and shows form", async ({ page }) => {
    await page.goto("/run");
    await expect(page.getByText("Run Backtest")).toBeVisible();
    await expect(page.getByLabel("Symbol")).toBeVisible();
  });

  test("strategy picker shows mocked strategies", async ({ page }) => {
    await page.goto("/run");
    const select = page.locator("select").first();
    await expect(select).toBeVisible();
    await expect(page.getByText("E2E EMA Crossover")).toBeVisible();
  });

  test("submitting form shows completed run metrics", async ({ page }) => {
    await page.goto("/run");

    // Select the strategy
    await page.locator("select").first().selectOption("e2e-strategy-1");

    // Submit
    await page.getByRole("button", { name: /run backtest/i }).click();

    // Results panel should appear
    await expect(page.getByText("Final value")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("$118,000")).toBeVisible();
  });

  test("run detail shows sharpe and drawdown", async ({ page }) => {
    await page.goto("/run");
    await page.locator("select").first().selectOption("e2e-strategy-1");
    await page.getByRole("button", { name: /run backtest/i }).click();

    await expect(page.getByText("1.23")).toBeVisible({ timeout: 5000 });   // sharpe
    await expect(page.getByText("-12.00%")).toBeVisible();                  // max drawdown
  });
});

test.describe("Results Explorer", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/backtests**", async (route) => {
      await route.fulfill({ json: [MOCK_RUN] });
    });
    await page.route("**/backtests/e2e-run-1", async (route) => {
      await route.fulfill({ json: MOCK_RUN });
    });
  });

  test("results page loads completed runs", async ({ page }) => {
    await page.goto("/results");
    await expect(page.getByText("Results")).toBeVisible();
    await expect(page.getByText("E2E EMA Crossover")).toBeVisible();
  });

  test("selecting a run shows equity curve section", async ({ page }) => {
    await page.goto("/results");
    await page.getByText("E2E EMA Crossover").click();
    await expect(page.getByText("Equity curve")).toBeVisible({ timeout: 3000 });
  });

  test("selecting a run shows trade log tab", async ({ page }) => {
    await page.goto("/results");
    await page.getByText("E2E EMA Crossover").click();
    await expect(page.getByText(/Trades/)).toBeVisible({ timeout: 3000 });
    await page.getByText(/Trades/).click();
    // Trade log table header
    await expect(page.getByText("Entry")).toBeVisible();
    await expect(page.getByText("P&L")).toBeVisible();
  });

  test("export buttons are visible for completed run", async ({ page }) => {
    await page.goto("/results");
    await page.getByText("E2E EMA Crossover").click();
    await expect(page.getByRole("button", { name: /export equity/i })).toBeVisible({ timeout: 3000 });
    await expect(page.getByRole("button", { name: /export trades/i })).toBeVisible();
  });
});
