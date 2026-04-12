"use client";

import { useEffect, useRef, useState } from "react";

type Option<T extends string> = { value: T; label: string };

type SelectProps<T extends string> = {
  options: Option<T>[];
  value: T | "";
  onChange: (v: T) => void;
  placeholder?: string;
};

export function Select<T extends string>({
  options,
  value,
  onChange,
  placeholder = "Select…",
}: SelectProps<T>) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onMouseDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onMouseDown);
    return () => document.removeEventListener("mousedown", onMouseDown);
  }, [open]);

  const selected = options.find((o) => o.value === value);

  return (
    <div ref={ref} className="relative">
      {/* Trigger — styled as an input; focus changes border to Body per design spec */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`w-full flex items-center justify-between px-3 py-2 bg-surface border rounded-md text-small transition-colors duration-[80ms] focus-visible:outline-none focus-visible:border-[#37352F] ${
          open ? "border-[#37352F]" : "border-border"
        }`}
      >
        <span className={selected ? "text-[#191919]" : "text-muted"}>
          {selected?.label ?? placeholder}
        </span>
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
          className={`text-muted flex-shrink-0 transition-transform duration-[80ms] ${open ? "rotate-180" : ""}`}
        >
          <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div className="absolute z-20 mt-1 w-full bg-surface border border-border rounded-lg overflow-hidden shadow-float">
          {options.length === 0 ? (
            <p className="px-3 py-2 text-small text-muted">No options available.</p>
          ) : (
            options.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => {
                  onChange(opt.value);
                  setOpen(false);
                }}
                className={`w-full text-left px-3 py-2 text-small transition-colors duration-[80ms] ${
                  opt.value === value
                    ? "text-[#191919] bg-background"
                    : "text-[#37352F] hover:bg-background"
                }`}
              >
                {opt.label}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
