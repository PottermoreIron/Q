import Link from "next/link";
import { type ReactNode } from "react";

const NAV = [
  { href: "/dashboard",  label: "Dashboard"  },
  { href: "/strategies", label: "Strategies" },
  { href: "/data",       label: "Data"       },
  { href: "/run",        label: "Run"        },
  { href: "/results",    label: "Results"    },
];

const BOTTOM_NAV = [{ href: "/settings", label: "Settings" }];

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-sidebar flex-shrink-0 bg-surface border-r border-border flex flex-col">
        {/* Logo */}
        <div className="px-5 py-6 border-b border-border">
          <span className="font-serif italic text-title text-ink">Backtest</span>
        </div>

        {/* Primary nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {NAV.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center px-3 py-2 text-body text-body rounded-md transition-colors duration-[80ms] linear hover:bg-background"
            >
              {label}
            </Link>
          ))}
        </nav>

        {/* Bottom nav */}
        <nav className="px-3 py-4 border-t border-border space-y-0.5">
          {BOTTOM_NAV.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center px-3 py-2 text-body text-muted rounded-md transition-colors duration-[80ms] linear hover:bg-background hover:text-body"
            >
              {label}
            </Link>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-content mx-auto px-8 py-12">{children}</div>
      </main>
    </div>
  );
}
