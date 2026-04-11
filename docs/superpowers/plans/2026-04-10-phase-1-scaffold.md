# Backtesting App — Phase 1: Project Scaffold

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Initialize a working Turborepo monorepo with Next.js 14 (web), Expo (mobile), FastAPI (backend), shared TypeScript packages, Docker Compose for local dev, and a CI skeleton — everything compiles, tests pass, and `docker compose up` starts all services.

**Architecture:** pnpm workspaces + Turborepo manage three apps (`web`, `mobile`, `api`) and one shared package (`@app/logic`). FastAPI runs in Docker alongside PostgreSQL and Redis. The shared package holds all Zod schemas so both frontend apps share the same validated types.

**Tech Stack:** pnpm 9, Turborepo 2, Next.js 14 (App Router), Expo SDK 51, FastAPI 0.111, Python 3.12, PostgreSQL 15, Redis 7, Tailwind CSS 3, Zod 3, Vitest 1, pytest 8

---

## File Map

```
/                               ← repo root
├── package.json                ← root workspace (private)
├── pnpm-workspace.yaml         ← declares apps/* and packages/*
├── turbo.json                  ← pipeline: build, test, lint
├── .gitignore
├── .env.example                ← documents all required env vars
├── docker-compose.yml          ← postgres, redis, api
├── .github/workflows/ci.yml    ← lint + test on push
│
├── apps/
│   ├── web/                    ← Next.js 14 (App Router)
│   │   ├── package.json
│   │   ├── next.config.ts
│   │   ├── tsconfig.json
│   │   ├── tailwind.config.ts
│   │   ├── postcss.config.mjs
│   │   └── src/
│   │       └── app/
│   │           ├── layout.tsx
│   │           └── page.tsx
│   │
│   ├── mobile/                 ← Expo SDK 51
│   │   ├── package.json
│   │   ├── app.json
│   │   ├── tsconfig.json
│   │   └── app/
│   │       ├── _layout.tsx
│   │       └── index.tsx
│   │
│   └── api/                    ← FastAPI
│       ├── pyproject.toml
│       ├── Dockerfile
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── routers/
│       │   └── health.py
│       └── tests/
│           └── test_health.py
│
└── packages/
    └── logic/                  ← @app/logic shared types
        ├── package.json
        ├── tsconfig.json
        └── src/
            ├── index.ts
            └── types/
                ├── strategy.ts
                ├── market-data.ts
                └── backtest.ts
```

---

## Task 1: Initialize Turborepo Monorepo

**Files:**
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `turbo.json`
- Create: `.gitignore`

- [ ] **Step 1: Check pnpm is available**

```bash
pnpm --version
```
Expected: `9.x.x` (install with `npm install -g pnpm@9` if missing)

- [ ] **Step 2: Create root `package.json`**

```json
{
  "name": "backtesting-app",
  "private": true,
  "version": "0.0.1",
  "scripts": {
    "build": "turbo build",
    "dev": "turbo dev --parallel",
    "test": "turbo test",
    "lint": "turbo lint"
  },
  "devDependencies": {
    "turbo": "^2.0.0",
    "typescript": "^5.4.0"
  },
  "engines": {
    "node": ">=20",
    "pnpm": ">=9"
  },
  "packageManager": "pnpm@9.0.0"
}
```

- [ ] **Step 3: Create `pnpm-workspace.yaml`**

```yaml
packages:
  - "apps/*"
  - "packages/*"
```

- [ ] **Step 4: Create `turbo.json`**

```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "!.next/cache/**", "dist/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "test": {
      "dependsOn": ["^build"],
      "outputs": ["coverage/**"]
    },
    "lint": {}
  }
}
```

- [ ] **Step 5: Create `.gitignore`**

```gitignore
# Dependencies
node_modules/
.pnp
.pnp.js

# Build outputs
.next/
dist/
out/
build/

# Turbo
.turbo/

# Env
.env
.env.local
.env.*.local

# Python
__pycache__/
*.pyc
*.pyo
.venv/
.pytest_cache/
.ruff_cache/

# Expo
.expo/
android/
ios/

# Misc
.DS_Store
*.log
coverage/
```

- [ ] **Step 6: Install root deps**

```bash
pnpm install
```
Expected: `node_modules` created at root, `pnpm-lock.yaml` generated.

- [ ] **Step 7: Commit**

```bash
git add package.json pnpm-workspace.yaml turbo.json .gitignore pnpm-lock.yaml
git commit -m "chore: initialize Turborepo monorepo"
```

---

## Task 2: Shared @app/logic Package

**Files:**
- Create: `packages/logic/package.json`
- Create: `packages/logic/tsconfig.json`
- Create: `packages/logic/src/types/strategy.ts`
- Create: `packages/logic/src/types/market-data.ts`
- Create: `packages/logic/src/types/backtest.ts`
- Create: `packages/logic/src/index.ts`
- Create: `packages/logic/src/index.test.ts`

- [ ] **Step 1: Create `packages/logic/package.json`**

```json
{
  "name": "@app/logic",
  "version": "0.0.1",
  "private": true,
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "import": "./dist/index.js",
      "types": "./dist/index.d.ts"
    }
  },
  "scripts": {
    "build": "tsc -p tsconfig.json",
    "test": "vitest run",
    "lint": "tsc --noEmit"
  },
  "dependencies": {
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "typescript": "^5.4.0",
    "vitest": "^1.6.0"
  }
}
```

- [ ] **Step 2: Create `packages/logic/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "lib": ["ES2022"],
    "declaration": true,
    "declarationMap": true,
    "strict": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "skipLibCheck": true
  },
  "include": ["src"],
  "exclude": ["dist", "node_modules"]
}
```

- [ ] **Step 3: Write the failing test**

Create `packages/logic/src/index.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import {
  StrategySchema,
  MarketDataSchema,
  BacktestConfigSchema,
  AssetClass,
  Timeframe,
} from "./index";

describe("StrategySchema", () => {
  it("accepts a valid no-code strategy", () => {
    const result = StrategySchema.safeParse({
      id: "strat-001",
      name: "EMA Cross",
      type: "no-code",
      blocks: [],
      assetClass: "crypto",
      createdAt: new Date().toISOString(),
    });
    expect(result.success).toBe(true);
  });

  it("accepts a valid python strategy", () => {
    const result = StrategySchema.safeParse({
      id: "strat-002",
      name: "RSI Bot",
      type: "python",
      code: "def run(data): pass",
      assetClass: "stocks",
      createdAt: new Date().toISOString(),
    });
    expect(result.success).toBe(true);
  });

  it("rejects strategy with no name", () => {
    const result = StrategySchema.safeParse({
      id: "strat-003",
      type: "no-code",
      blocks: [],
      assetClass: "crypto",
      createdAt: new Date().toISOString(),
    });
    expect(result.success).toBe(false);
  });
});

describe("MarketDataSchema", () => {
  it("accepts valid OHLCV bar", () => {
    const result = MarketDataSchema.safeParse({
      symbol: "BTC/USDT",
      timeframe: "1d",
      open: 60000,
      high: 61000,
      low: 59000,
      close: 60500,
      volume: 1234.56,
      timestamp: new Date().toISOString(),
    });
    expect(result.success).toBe(true);
  });
});

describe("BacktestConfigSchema", () => {
  it("accepts valid config", () => {
    const result = BacktestConfigSchema.safeParse({
      strategyId: "strat-001",
      symbol: "AAPL",
      assetClass: "stocks",
      timeframe: "1d",
      startDate: "2022-01-01",
      endDate: "2023-01-01",
      initialCapital: 10000,
    });
    expect(result.success).toBe(true);
  });
});

describe("AssetClass enum", () => {
  it("lists all supported asset classes", () => {
    expect(AssetClass.options).toEqual(
      expect.arrayContaining(["stocks", "crypto", "forex", "futures"])
    );
  });
});

describe("Timeframe enum", () => {
  it("includes common timeframes", () => {
    expect(Timeframe.options).toEqual(
      expect.arrayContaining(["1m", "5m", "15m", "1h", "4h", "1d", "1w"])
    );
  });
});
```

- [ ] **Step 4: Run test — verify it fails**

```bash
cd packages/logic && pnpm install && pnpm test
```
Expected: `Error: Cannot find module './index'` or similar.

- [ ] **Step 5: Create `packages/logic/src/types/market-data.ts`**

```typescript
import { z } from "zod";

export const Timeframe = z.enum([
  "1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M",
]);
export type Timeframe = z.infer<typeof Timeframe>;

export const AssetClass = z.enum(["stocks", "crypto", "forex", "futures"]);
export type AssetClass = z.infer<typeof AssetClass>;

export const MarketDataSchema = z.object({
  symbol: z.string().min(1),
  timeframe: Timeframe,
  open: z.number().positive(),
  high: z.number().positive(),
  low: z.number().positive(),
  close: z.number().positive(),
  volume: z.number().nonnegative(),
  timestamp: z.string().datetime(),
});
export type MarketData = z.infer<typeof MarketDataSchema>;

export const DataSourceSchema = z.object({
  type: z.enum(["csv", "yahoo", "binance", "alphavantage", "polygon", "alpaca"]),
  apiKey: z.string().optional(),
});
export type DataSource = z.infer<typeof DataSourceSchema>;
```

- [ ] **Step 6: Create `packages/logic/src/types/strategy.ts`**

```typescript
import { z } from "zod";
import { AssetClass } from "./market-data";

export const StrategyBlockSchema = z.object({
  id: z.string(),
  type: z.enum([
    "ema", "sma", "rsi", "macd", "bollinger",
    "entry", "exit", "stop_loss", "take_profit", "position_size",
  ]),
  params: z.record(z.union([z.string(), z.number(), z.boolean()])),
});
export type StrategyBlock = z.infer<typeof StrategyBlockSchema>;

export const StrategySchema = z.discriminatedUnion("type", [
  z.object({
    id: z.string(),
    name: z.string().min(1),
    type: z.literal("no-code"),
    blocks: z.array(StrategyBlockSchema),
    assetClass: AssetClass,
    createdAt: z.string().datetime(),
    updatedAt: z.string().datetime().optional(),
  }),
  z.object({
    id: z.string(),
    name: z.string().min(1),
    type: z.literal("python"),
    code: z.string().min(1),
    assetClass: AssetClass,
    createdAt: z.string().datetime(),
    updatedAt: z.string().datetime().optional(),
  }),
]);
export type Strategy = z.infer<typeof StrategySchema>;
```

- [ ] **Step 7: Create `packages/logic/src/types/backtest.ts`**

```typescript
import { z } from "zod";
import { AssetClass, Timeframe } from "./market-data";

export const BacktestConfigSchema = z.object({
  strategyId: z.string(),
  symbol: z.string().min(1),
  assetClass: AssetClass,
  timeframe: Timeframe,
  startDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  endDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  initialCapital: z.number().positive(),
  commission: z.number().min(0).default(0.001),
});
export type BacktestConfig = z.infer<typeof BacktestConfigSchema>;

export const BacktestMetricsSchema = z.object({
  sharpeRatio: z.number(),
  sortinoRatio: z.number(),
  maxDrawdown: z.number(),
  cagr: z.number(),
  winRate: z.number().min(0).max(1),
  totalTrades: z.number().int().nonnegative(),
  profitFactor: z.number(),
  finalCapital: z.number(),
});
export type BacktestMetrics = z.infer<typeof BacktestMetricsSchema>;

export const BacktestStatusSchema = z.enum([
  "pending", "running", "completed", "failed", "cancelled",
]);
export type BacktestStatus = z.infer<typeof BacktestStatusSchema>;

export const BacktestRunSchema = z.object({
  id: z.string(),
  config: BacktestConfigSchema,
  status: BacktestStatusSchema,
  metrics: BacktestMetricsSchema.optional(),
  errorMessage: z.string().optional(),
  createdAt: z.string().datetime(),
  completedAt: z.string().datetime().optional(),
  engine: z.enum(["vectorbt", "backtrader"]),
});
export type BacktestRun = z.infer<typeof BacktestRunSchema>;
```

- [ ] **Step 8: Create `packages/logic/src/index.ts`**

```typescript
export * from "./types/market-data";
export * from "./types/strategy";
export * from "./types/backtest";
```

- [ ] **Step 9: Run tests — verify they pass**

```bash
cd packages/logic && pnpm test
```
Expected output:
```
 ✓ src/index.test.ts (8)
   ✓ StrategySchema > accepts a valid no-code strategy
   ✓ StrategySchema > accepts a valid python strategy
   ✓ StrategySchema > rejects strategy with no name
   ✓ MarketDataSchema > accepts valid OHLCV bar
   ✓ BacktestConfigSchema > accepts valid config
   ✓ AssetClass enum > lists all supported asset classes
   ✓ Timeframe enum > includes common timeframes

Test Files  1 passed (1)
Tests       7 passed (7)
```

- [ ] **Step 10: Build the package**

```bash
cd packages/logic && pnpm build
```
Expected: `dist/` folder created with `index.js` and `index.d.ts`.

- [ ] **Step 11: Commit**

```bash
cd /Users/yecao/Claude/Q
git add packages/
git commit -m "feat: add @app/logic shared Zod schemas (strategy, market-data, backtest)"
```

---

## Task 3: Next.js 14 Web App

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/tailwind.config.ts`
- Create: `apps/web/postcss.config.mjs`
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/page.tsx`
- Create: `apps/web/src/app/page.test.tsx`

- [ ] **Step 1: Create `apps/web/package.json`**

```json
{
  "name": "@app/web",
  "version": "0.0.1",
  "private": true,
  "scripts": {
    "build": "next build",
    "dev": "next dev --port 3000",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest run"
  },
  "dependencies": {
    "@app/logic": "workspace:*",
    "next": "14.2.5",
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  },
  "devDependencies": {
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.4.0",
    "@types/node": "^20.0.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.0",
    "jsdom": "^24.0.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.4.0",
    "vitest": "^1.6.0"
  }
}
```

- [ ] **Step 2: Create `apps/web/next.config.ts`**

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@app/logic"],
};

export default nextConfig;
```

- [ ] **Step 3: Create `apps/web/tsconfig.json`**

```json
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 4: Create `apps/web/tailwind.config.ts`**

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eff6ff",
          500: "#3b82f6",
          900: "#1e3a8a",
        },
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 5: Create `apps/web/postcss.config.mjs`**

```javascript
/** @type {import('postcss').Config} */
const config = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};

export default config;
```

- [ ] **Step 6: Write the failing test**

Create `apps/web/src/app/page.test.tsx`:

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import Page from "./page";

describe("Home page", () => {
  it("renders the app title", () => {
    render(<Page />);
    expect(screen.getByRole("heading", { name: /backtesting/i })).toBeInTheDocument();
  });

  it("renders a call-to-action button", () => {
    render(<Page />);
    expect(
      screen.getByRole("link", { name: /new strategy/i })
    ).toBeInTheDocument();
  });
});
```

Also add a Vitest config at `apps/web/vitest.config.ts`:

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: [],
    globals: true,
  },
});
```

- [ ] **Step 7: Run test — verify it fails**

```bash
cd apps/web && pnpm install && pnpm test
```
Expected: `Error: Cannot find module './page'`

- [ ] **Step 8: Create `apps/web/src/app/layout.tsx`**

```typescript
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Backtesting App",
  description: "Test trading strategies across crypto, stocks, forex, and futures",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-white text-slate-900 antialiased">{children}</body>
    </html>
  );
}
```

Create `apps/web/src/app/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 9: Create `apps/web/src/app/page.tsx`**

```typescript
export default function Page() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4">
      <h1 className="text-4xl font-bold text-slate-900 mb-4">
        Backtesting App
      </h1>
      <p className="text-slate-500 mb-8 text-center max-w-md">
        Test trading strategies across crypto, stocks, forex, and futures.
      </p>
      <a
        href="/strategies/new"
        className="bg-brand-500 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-600 transition-colors"
      >
        New Strategy
      </a>
    </main>
  );
}
```

- [ ] **Step 10: Run tests — verify they pass**

```bash
cd apps/web && pnpm test
```
Expected:
```
 ✓ src/app/page.test.tsx (2)
   ✓ Home page > renders the app title
   ✓ Home page > renders a call-to-action button
Test Files  1 passed (1)
```

- [ ] **Step 11: Verify dev server starts**

```bash
cd apps/web && pnpm dev
```
Expected: `▲ Next.js 14.x.x` / `- Local: http://localhost:3000`. Open browser, see heading "Backtesting App". Stop with Ctrl+C.

- [ ] **Step 12: Commit**

```bash
cd /Users/yecao/Claude/Q
git add apps/web/
git commit -m "feat: scaffold Next.js 14 web app with Tailwind"
```

---

## Task 4: Expo Mobile App

**Files:**
- Create: `apps/mobile/package.json`
- Create: `apps/mobile/app.json`
- Create: `apps/mobile/tsconfig.json`
- Create: `apps/mobile/app/_layout.tsx`
- Create: `apps/mobile/app/index.tsx`

- [ ] **Step 1: Create `apps/mobile/package.json`**

```json
{
  "name": "@app/mobile",
  "version": "0.0.1",
  "private": true,
  "main": "expo-router/entry",
  "scripts": {
    "start": "expo start",
    "android": "expo run:android",
    "ios": "expo run:ios",
    "build": "echo 'mobile build handled by EAS'",
    "test": "echo 'no mobile unit tests in phase 1'"
  },
  "dependencies": {
    "@app/logic": "workspace:*",
    "expo": "~51.0.0",
    "expo-router": "~3.5.0",
    "expo-status-bar": "~1.12.0",
    "react": "18.2.0",
    "react-native": "0.74.1",
    "react-native-safe-area-context": "4.10.1",
    "react-native-screens": "3.31.1"
  },
  "devDependencies": {
    "@babel/core": "^7.24.0",
    "@types/react": "~18.2.0",
    "typescript": "^5.4.0"
  }
}
```

- [ ] **Step 2: Create `apps/mobile/app.json`**

```json
{
  "expo": {
    "name": "Backtesting App",
    "slug": "backtesting-app",
    "version": "1.0.0",
    "orientation": "portrait",
    "scheme": "backtesting",
    "userInterfaceStyle": "light",
    "assetBundlePatterns": ["**/*"],
    "ios": {
      "supportsTablet": true,
      "bundleIdentifier": "com.backtestingapp.mobile"
    },
    "android": {
      "adaptiveIcon": {
        "backgroundColor": "#3b82f6"
      },
      "package": "com.backtestingapp.mobile"
    },
    "plugins": ["expo-router"]
  }
}
```

- [ ] **Step 3: Create `apps/mobile/tsconfig.json`**

```json
{
  "extends": "expo/tsconfig.base",
  "compilerOptions": {
    "strict": true,
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["**/*.ts", "**/*.tsx", ".expo/types/**/*.d.ts", "expo-env.d.ts"]
}
```

- [ ] **Step 4: Create `apps/mobile/app/_layout.tsx`**

```typescript
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

export default function RootLayout() {
  return (
    <>
      <Stack>
        <Stack.Screen name="index" options={{ title: "Backtesting App" }} />
      </Stack>
      <StatusBar style="auto" />
    </>
  );
}
```

- [ ] **Step 5: Create `apps/mobile/app/index.tsx`**

```typescript
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { Link } from "expo-router";

export default function HomeScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Backtesting App</Text>
      <Text style={styles.subtitle}>
        Test trading strategies across crypto, stocks, forex, and futures.
      </Text>
      <Link href="/strategies/new" asChild>
        <TouchableOpacity style={styles.button}>
          <Text style={styles.buttonText}>New Strategy</Text>
        </TouchableOpacity>
      </Link>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
    backgroundColor: "#ffffff",
  },
  title: {
    fontSize: 32,
    fontWeight: "700",
    color: "#0f172a",
    marginBottom: 12,
    textAlign: "center",
  },
  subtitle: {
    fontSize: 16,
    color: "#64748b",
    textAlign: "center",
    marginBottom: 32,
    maxWidth: 320,
  },
  button: {
    backgroundColor: "#3b82f6",
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  buttonText: {
    color: "#ffffff",
    fontWeight: "600",
    fontSize: 16,
  },
});
```

- [ ] **Step 6: Install mobile deps**

```bash
cd apps/mobile && pnpm install
```
Expected: dependencies installed, no errors.

- [ ] **Step 7: Verify Expo starts**

```bash
cd apps/mobile && pnpm start
```
Expected: QR code displayed in terminal, Expo DevTools open. Press `w` to open in web browser — should show title "Backtesting App" and a blue button. Stop with Ctrl+C.

- [ ] **Step 8: Commit**

```bash
cd /Users/yecao/Claude/Q
git add apps/mobile/
git commit -m "feat: scaffold Expo mobile app"
```

---

## Task 5: FastAPI Backend + Health Check

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/config.py`
- Create: `apps/api/database.py`
- Create: `apps/api/main.py`
- Create: `apps/api/routers/health.py`
- Create: `apps/api/routers/__init__.py`
- Create: `apps/api/tests/__init__.py`
- Create: `apps/api/tests/test_health.py`

- [ ] **Step 1: Create `apps/api/pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "backtesting-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi==0.111.0",
    "uvicorn[standard]==0.30.0",
    "pydantic==2.7.0",
    "pydantic-settings==2.3.0",
    "sqlalchemy==2.0.30",
    "asyncpg==0.29.0",
    "redis==5.0.4",
    "celery==5.4.0",
    "httpx==0.27.0",
    "python-jose[cryptography]==3.3.0",
    "passlib[bcrypt]==1.7.4",
    "python-multipart==0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest==8.2.0",
    "pytest-asyncio==0.23.0",
    "httpx==0.27.0",
    "ruff==0.4.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Set up Python virtual environment**

```bash
cd apps/api && python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```
Expected: all packages installed, no errors.

- [ ] **Step 3: Create `apps/api/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Backtesting API"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/backtesting"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "changeme-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


settings = Settings()
```

- [ ] **Step 4: Create `apps/api/database.py`**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from .config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

- [ ] **Step 5: Create `apps/api/routers/__init__.py`**

```python
# routers package
```

- [ ] **Step 6: Write the failing test**

Create `apps/api/tests/__init__.py` (empty).

Create `apps/api/tests/test_health.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from apps.api.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


async def test_health_returns_ok(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


async def test_health_includes_service_name(client: AsyncClient):
    response = await client.get("/health")
    assert response.json()["service"] == "Backtesting API"
```

- [ ] **Step 7: Run test — verify it fails**

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_health.py -v
```
Expected: `ModuleNotFoundError: No module named 'apps'`

- [ ] **Step 8: Create `apps/__init__.py` and `apps/api/__init__.py`**

```bash
touch /Users/yecao/Claude/Q/apps/__init__.py
touch /Users/yecao/Claude/Q/apps/api/__init__.py
```

- [ ] **Step 9: Create `apps/api/routers/health.py`**

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])

__version__ = "0.1.0"


class HealthResponse(BaseModel):
    status: str
    version: str
    service: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=__version__,
        service="Backtesting API",
    )
```

- [ ] **Step 10: Create `apps/api/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers.health import router as health_router

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
```

- [ ] **Step 11: Run tests — verify they pass**

```bash
cd /Users/yecao/Claude/Q && source apps/api/.venv/bin/activate
python -m pytest apps/api/tests/test_health.py -v
```
Expected:
```
PASSED tests/test_health.py::test_health_returns_ok
PASSED tests/test_health.py::test_health_includes_service_name
2 passed in 0.xxs
```

- [ ] **Step 12: Commit**

```bash
git add apps/api/ apps/__init__.py
git commit -m "feat: scaffold FastAPI backend with health check endpoint"
```

---

## Task 6: Docker Compose for Local Dev

**Files:**
- Create: `apps/api/Dockerfile`
- Create: `docker-compose.yml`
- Create: `.env.example`

- [ ] **Step 1: Create `apps/api/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir hatch

COPY apps/api/pyproject.toml .
RUN pip install --no-cache-dir ".[dev]"

COPY apps/ ./apps/

EXPOSE 8000

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- [ ] **Step 2: Create `.env.example`**

```bash
# Copy to .env and fill in values
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/backtesting
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=changeme-in-production
DEBUG=true
```

- [ ] **Step 3: Create `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: backtesting
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    build:
      context: .
      dockerfile: apps/api/Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/backtesting
      REDIS_URL: redis://redis:6379/0
      DEBUG: "true"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./apps:/app/apps

volumes:
  postgres_data:
```

- [ ] **Step 4: Start services**

```bash
cd /Users/yecao/Claude/Q
cp .env.example .env
docker compose up -d
```
Expected: all three containers start (`postgres`, `redis`, `api`). No errors.

- [ ] **Step 5: Verify all services are healthy**

```bash
docker compose ps
```
Expected:
```
NAME         STATUS
api          Up (running)
postgres     Up (healthy)
redis        Up (healthy)
```

- [ ] **Step 6: Verify health endpoint via Docker**

```bash
curl http://localhost:8000/health
```
Expected: `{"status":"ok","version":"0.1.0","service":"Backtesting API"}`

- [ ] **Step 7: Stop containers**

```bash
docker compose down
```

- [ ] **Step 8: Commit**

```bash
git add docker-compose.yml apps/api/Dockerfile .env.example
git commit -m "feat: add Docker Compose for local dev (postgres, redis, api)"
```

---

## Task 7: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test-frontend:
    name: Frontend Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v4
        with:
          version: 9

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm

      - name: Install dependencies
        run: pnpm install

      - name: Build @app/logic
        run: pnpm --filter @app/logic build

      - name: Test @app/logic
        run: pnpm --filter @app/logic test

      - name: Test web app
        run: pnpm --filter @app/web test

  test-backend:
    name: Backend Tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: backtesting_test
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: apps/api/pyproject.toml

      - name: Install API dependencies
        run: pip install -e "apps/api/.[dev]"

      - name: Run API tests
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/backtesting_test
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: ci-test-secret
        run: python -m pytest apps/api/tests/ -v

  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v4
        with:
          version: 9

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm

      - name: Install dependencies
        run: pnpm install

      - name: Type-check @app/logic
        run: pnpm --filter @app/logic lint

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install ruff
        run: pip install ruff

      - name: Lint Python
        run: ruff check apps/api/
```

- [ ] **Step 2: Commit and push**

```bash
git add .github/
git commit -m "ci: add GitHub Actions workflow (frontend, backend, lint)"
git push origin main
```

- [ ] **Step 3: Verify CI passes**

Open GitHub → Actions tab. All three jobs (`Frontend Tests`, `Backend Tests`, `Lint`) should be green.

---

## Done — Phase 1 Complete

At this point:
- `pnpm install && pnpm test` passes for `@app/logic` and `@app/web`
- `python -m pytest apps/api/tests/ -v` passes
- `docker compose up` starts all three services
- `curl http://localhost:8000/health` returns `{"status":"ok",...}`
- CI is green on GitHub

**Next:** Proceed to Phase 2 (Auth & Data Ingestion) — write the Phase 2 plan from `docs/superpowers/specs/2026-04-10-backtesting-app-design.md`.
