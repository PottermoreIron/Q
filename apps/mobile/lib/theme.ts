import { Platform } from "react-native";

export const C = {
  bg: "#F7F6F3",
  surface: "#FFFFFF",
  border: "#E9E9E7",
  muted: "#9B9A97",
  body: "#37352F",
  ink: "#191919",
  positive: "#16A34A",
  negative: "#DC2626",
  warning: "#D97706",
} as const;

export const FONT = {
  serif: {
    fontStyle: "italic" as const,
    fontFamily: Platform.select({ ios: "Georgia", android: "serif", default: "serif" }),
  },
  mono: {
    fontFamily: Platform.select({
      ios: "Courier New",
      android: "monospace",
      default: "monospace",
    }),
  },
} as const;

export const RADIUS = {
  card: 8,
  input: 6,
  tag: 4,
} as const;
