import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Backtesting App",
  description: "Test your trading strategies",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
