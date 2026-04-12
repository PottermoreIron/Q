/**
 * Design tokens for the Backtesting App.
 * Copy the `theme.extend` block into apps/web/tailwind.config.ts.
 * These tokens implement docs/design/design-principles.md exactly.
 */

import type { Config } from "tailwindcss";

const tokens: Config["theme"] = {
  extend: {
    // ─── Color ────────────────────────────────────────────────────────────
    colors: {
      // Base palette (no accent)
      background: "#F7F6F3", // warm off-white — page canvas
      surface: "#FFFFFF",    // pure white — cards, panels, inputs
      border: "#E9E9E7",     // warm light gray — dividers, card edges
      muted: "#9B9A97",      // mid gray — secondary text, placeholders
      body: "#37352F",       // warm dark gray — primary content text
      ink: "#191919",        // near-black — headings, CTAs, high-emphasis

      // Semantic (data only — never UI decoration)
      positive: "#16A34A",   // profit, positive return, success
      negative: "#DC2626",   // loss, drawdown, error
      warning: "#D97706",    // pending, in-progress, caution
    },

    // ─── Typography ───────────────────────────────────────────────────────
    fontFamily: {
      serif: ["DM Serif Display", "Georgia", "serif"],
      sans: ["DM Sans", "system-ui", "sans-serif"],
      mono: ["JetBrains Mono", "Menlo", "monospace"],
    },

    fontSize: {
      // [size, { lineHeight, letterSpacing, fontWeight }]
      display: ["2rem",     { lineHeight: "1.15", letterSpacing: "-0.01em" }],
      title:   ["1.375rem", { lineHeight: "1.25", letterSpacing: "0" }],
      heading: ["1rem",     { lineHeight: "1.5",  letterSpacing: "0" }],
      body:    ["0.875rem", { lineHeight: "1.6",  letterSpacing: "0" }],
      small:   ["0.75rem",  { lineHeight: "1.5",  letterSpacing: "0" }],
      label:   ["0.6875rem",{ lineHeight: "1.4",  letterSpacing: "0.09em" }],
      data:    ["1.25rem",  { lineHeight: "1.2",  letterSpacing: "-0.02em" }],
      mono:    ["0.8125rem",{ lineHeight: "1.6",  letterSpacing: "0" }],
    },

    // ─── Spacing (8pt grid) ───────────────────────────────────────────────
    spacing: {
      // Tailwind's default scale is already 4px-based (1 = 4px).
      // These named tokens map to the design principles doc.
      // Use Tailwind's numeric scale directly in components.
      // Reference:
      //   space-1  = p-1  (4px)
      //   space-2  = p-2  (8px)
      //   space-3  = p-3  (12px)
      //   space-4  = p-4  (16px)
      //   space-5  = p-5  (20px)
      //   space-6  = p-6  (24px)
      //   space-8  = p-8  (32px)
      //   space-12 = p-12 (48px)
      //   space-16 = p-16 (64px)
    },

    // ─── Border radius ────────────────────────────────────────────────────
    borderRadius: {
      // Override defaults to match design principles
      none: "0",
      sm:   "4px",   // tight elements (tags, badges)
      md:   "6px",   // inputs, secondary buttons, primary buttons
      lg:   "8px",   // cards
      xl:   "12px",  // modals, sheets — maximum allowed
      // No values larger than 12px per design principles
    },

    // ─── Box shadow ───────────────────────────────────────────────────────
    boxShadow: {
      // No decorative shadows — only floating elements
      none:     "none",
      float:    "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)",
      // Usage: dropdowns, command palette, tooltips only
    },

    // ─── Animation ────────────────────────────────────────────────────────
    transitionTimingFunction: {
      // Named easings from design principles
      "spring":    "cubic-bezier(0.34, 1.56, 0.64, 1)",  // strategy block add
      "out-expo":  "cubic-bezier(0.16, 1, 0.3, 1)",      // reveals, results
      "in-press":  "ease-in",                             // button press
    },

    transitionDuration: {
      "80":  "80ms",   // button press
      "180": "180ms",  // modal open
      "200": "200ms",  // page transition
      "220": "220ms",  // block add
      "320": "320ms",  // result card appear
      "600": "600ms",  // metric count-up
    },

    // ─── Layout ───────────────────────────────────────────────────────────
    maxWidth: {
      content: "1080px", // max width of main content area
    },

    width: {
      sidebar: "240px",  // fixed sidebar width
    },

    keyframes: {
      // Result card reveal
      "slide-up-fade": {
        "0%":   { opacity: "0", transform: "translateY(8px)" },
        "100%": { opacity: "1", transform: "translateY(0)" },
      },
      // Metric count-up (use with JS counter, this handles the fade-in)
      "fade-in": {
        "0%":   { opacity: "0" },
        "100%": { opacity: "1" },
      },
      // Success pulse on result card border
      "border-pulse": {
        "0%, 100%": { borderColor: "#E9E9E7" },
        "50%":      { borderColor: "#191919" },
      },
      // Modal open
      "scale-in": {
        "0%":   { opacity: "0", transform: "scale(0.97)" },
        "100%": { opacity: "1", transform: "scale(1)" },
      },
      // Strategy block slides in from left
      "slide-in-left": {
        "0%":   { opacity: "0", transform: "translateX(-6px)" },
        "100%": { opacity: "1", transform: "translateX(0)" },
      },
    },

    animation: {
      "slide-up-fade":  "slide-up-fade 320ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
      "fade-in":        "fade-in 200ms ease-out forwards",
      "border-pulse":   "border-pulse 400ms ease-in-out",
      "scale-in":       "scale-in 180ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
      "slide-in-left":  "slide-in-left 220ms cubic-bezier(0.34, 1.56, 0.64, 1) forwards",
    },
  },
};

export default tokens;

/**
 * Usage in apps/web/tailwind.config.ts:
 *
 * import tokens from "../../docs/design/tailwind-tokens";
 * const config: Config = {
 *   content: [...],
 *   theme: tokens,
 *   plugins: [],
 * };
 */
