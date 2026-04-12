# Design Principles

> The single reference every engineer and contributor reads before touching the UI.

---

## Philosophy

**Stillness is the canvas. Detail is the reward.**

Inspired by Apple's restraint and Notion's editorial calm. The interface exists to make complex financial data feel approachable, trustworthy, and even beautiful. It should never compete with the user's work — it should disappear into it.

Four principles govern every decision:

1. **Content is the hero.** The strategy, the chart, the result — never the chrome around it.
2. **Earn every pixel.** If an element can be removed without losing meaning, remove it.
3. **Stillness by default, motion by intention.** UI rests quietly; animation is reserved for moments that deserve it.
4. **Numbers deserve respect.** Financial data is serious. Typography and spacing must make it feel authoritative, not cramped.

---

## Typography

### Typefaces

| Role | Font | Weight | Style |
|---|---|---|---|
| Page titles, section headings, key labels | DM Serif Display | 400 | Italic |
| All other text — body, data, labels, UI | DM Sans | 300 / 400 / 500 | Normal |
| Monospace (code editor, Python) | JetBrains Mono | 400 / 500 | Normal |

**Rule:** Serif italic appears only at the top of a hierarchy — page titles, section headings, and the names of strategies/runs. It never appears in tables, form fields, buttons, or data. This contrast is what gives the UI its vintage editorial character.

### Type Scale

| Token | Size | Weight | Font | Usage |
|---|---|---|---|---|
| `text-display` | 2rem / 32px | 400 italic | DM Serif Display | Page hero titles |
| `text-title` | 1.375rem / 22px | 400 italic | DM Serif Display | Section headings, card titles |
| `text-heading` | 1rem / 16px | 500 | DM Sans | Sub-section labels |
| `text-body` | 0.875rem / 14px | 400 | DM Sans | Primary body copy, list items |
| `text-small` | 0.75rem / 12px | 400 | DM Sans | Secondary info, metadata |
| `text-label` | 0.6875rem / 11px | 500 | DM Sans | ALL CAPS + tracked, axis labels, tags |
| `text-data` | 1.25rem / 20px | 300 | DM Sans | Key metric numbers (Sharpe, CAGR…) |
| `text-mono` | 0.8125rem / 13px | 400 | JetBrains Mono | Code, Python editor |

**Letter-spacing rule:** Labels in ALL CAPS use `tracking-widest` (0.1em). All other text uses default or `tracking-tight` for large display numbers.

---

## Color

### Palette

The palette has no accent color. Hierarchy is created entirely through value (lightness) contrast, not hue.

```
Background    #F7F6F3   warm off-white   — page backgrounds, canvas
Surface       #FFFFFF   pure white       — cards, panels, inputs
Border        #E9E9E7   warm light gray  — dividers, input borders, card edges
Muted         #9B9A97   mid gray         — secondary text, placeholders, icons
Body          #37352F   warm dark gray   — primary text, most content
Ink           #191919   near-black       — headings, CTAs, high-emphasis text
```

**Semantic colors** (used sparingly, never as accents):

```
Positive      #16A34A   green    — profit, positive return, success state
Negative      #DC2626   red      — loss, drawdown, error state
Warning       #D97706   amber    — pending, in-progress, caution
```

Semantic colors appear **only** in data context (a positive return number, an error message). They never color UI chrome (buttons, backgrounds, borders).

### Usage Rules

- **Primary button:** `Ink` background, white text
- **Secondary button:** `Surface` background, `Body` text, `Border` border
- **Page background:** `Background`
- **Card/panel background:** `Surface`
- **All borders:** `Border`
- **Primary text:** `Body`
- **Headings:** `Ink`
- **Disabled / placeholder:** `Muted`

---

## Spacing

8-point grid throughout. All spacing values are multiples of 4px.

| Token | Value | Usage |
|---|---|---|
| `space-1` | 4px | Icon padding, tight inline gaps |
| `space-2` | 8px | Element internal padding (small) |
| `space-3` | 12px | Default padding inside compact components |
| `space-4` | 16px | Default gap between related elements |
| `space-5` | 20px | Card internal padding |
| `space-6` | 24px | Section padding, between card groups |
| `space-8` | 32px | Between major sections |
| `space-12` | 48px | Page-level vertical rhythm |
| `space-16` | 64px | Hero areas, landing sections |

---

## Surfaces & Depth

No drop shadows on standard UI elements. Depth is communicated through **borders and background contrast**, not shadows.

| Surface type | Treatment |
|---|---|
| Page | `Background` (#F7F6F3), no border |
| Card | `Surface` (#FFF), 1px `Border` border, `rounded-lg` (8px) |
| Modal / sheet | `Surface`, 1px `Border`, `rounded-xl` (12px), subtle backdrop blur |
| Input | `Surface`, 1px `Border`, `rounded-md` (6px); focus: border becomes `Body` |
| Button (primary) | `Ink` fill, `rounded-md` (6px), no border |
| Button (secondary) | `Surface` fill, 1px `Border`, `rounded-md` (6px) |

**Shadow exception:** One shadow is permitted — a faint `0 1px 3px rgba(0,0,0,0.06)` on floating elements (dropdowns, command palette, tooltips) to separate them from the page. Nothing else.

---

## Motion

**Default state: still.** UI elements do not animate on idle. Hover states use fast, simple transitions only.

### Hover (idle UI)
- Background tint: `80ms linear`
- Opacity shift: `100ms linear`
- No scale, no translate, no spring on routine hover

### Purposeful moments (earned animation)
These are the moments that make users love the app. Each one is intentional.

| Moment | Animation | Duration | Easing |
|---|---|---|---|
| Backtest result appears | Card slides up from 8px below + fades in | 320ms | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Metric number reveals | Counts up from 0 to final value | 600ms | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Page transition | Fade + 4px upward shift | 200ms | `ease-out` |
| Modal opens | Scale 0.97→1 + fade | 180ms | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Success state (run complete) | Brief pulse on result card border | 400ms | `ease-in-out` |
| Strategy block added | Slides in from left, 6px | 220ms | `cubic-bezier(0.34, 1.56, 0.64, 1)` (spring) |
| Button press (primary only) | Scale 0.97 on active | 80ms | `ease-in` |

### Rules
- **Never** animate layout reflows (width, height changes) — use opacity/transform only
- **Never** animate more than 2–3 elements simultaneously
- **Respect** `prefers-reduced-motion` — all animations must have a `no-motion` fallback (instant transition)

---

## Layout

### Web (Next.js)

```
┌─────────────────────────────────────────────┐
│  Sidebar (240px fixed)  │  Main content area │
│                         │                    │
│  Logo                   │  Page title        │
│  ─────                  │  (DM Serif italic) │
│  Dashboard              │                    │
│  Strategies             │  Content           │
│  Data                   │                    │
│  Results                │                    │
│                         │                    │
│  ─────                  │                    │
│  Settings               │                    │
│  Account (optional)     │                    │
└─────────────────────────────────────────────┘
```

- Sidebar: `Surface` background, 1px right `Border`
- Content area: `Background`
- Max content width: 1080px (centered within content area on wide screens)
- Page title always uses `text-display` (DM Serif Display italic)

### Mobile (Expo)

Bottom tab bar navigation: Dashboard · Strategies · Run · Results. No sidebar. Content fills safe area.

---

## Component Patterns

### Metric block
Used for Sharpe, CAGR, drawdown, win rate, etc.
```
[value]           ← text-data (DM Sans 300, 20px, Ink)
[LABEL]           ← text-label (DM Sans 500, 11px, ALL CAPS, Muted)
```
Positive values: `Positive` color. Negative values: `Negative` color. Neutral (e.g., Sharpe): `Ink`.

### Strategy card
```
┌────────────────────────────┐
│ Strategy Name              │  ← text-title (DM Serif italic, Ink)
│ Symbol · Timeframe         │  ← text-small (DM Sans, Muted)
│ ──────────────────         │  ← Border divider
│ 2.41    +47%    −12%       │  ← Metric blocks
│ Sharpe  CAGR    Max DD     │
└────────────────────────────┘
```

### Section heading
```
[Section Name]    ← text-heading (DM Sans 500, Body color)
───────────────   ← 1px Border rule, full width, mt-2 mb-6
```

### Empty state
Centered, DM Serif italic in Muted color, short sentence, one action button below. No illustrations.

---

## Voice & Labels

- **Concise.** "New Strategy" not "Create a New Strategy"
- **Direct.** "Run" not "Run Backtest Now"
- **No jargon in UI chrome.** Save technical terms for data fields where they belong
- **Numbers:** Always show units. `+47% CAGR` not `47`. `−12% Max Drawdown` not `-0.12`
- **Dates:** `Jan 2022 – Dec 2023` not `2022-01-01T00:00:00Z`

---

## Accessibility

- All text meets WCAG AA contrast (4.5:1 minimum) against its background
- Focus rings: 2px `Ink` offset ring, always visible (never hidden with `outline: none`)
- Touch targets: minimum 44×44px on mobile
- `prefers-reduced-motion`: all transitions collapse to `0ms`
- Semantic HTML: use `<main>`, `<nav>`, `<section>`, `<article>` correctly

---

## What This Is Not

- No gradients (except chart fills, which are data)
- No illustrations or decorative icons
- No colored backgrounds on cards or sections
- No more than 2 font families on any screen
- No rounded corners larger than 12px
- No shadows except floating elements
- No accent color used as decoration
