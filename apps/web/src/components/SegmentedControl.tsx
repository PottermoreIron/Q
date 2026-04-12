"use client";

type Option<T extends string> = { value: T; label: string };

type SegmentedControlProps<T extends string> = {
  options: Option<T>[];
  value: T;
  onChange: (v: T) => void;
};

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
}: SegmentedControlProps<T>) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`px-3 py-1.5 rounded text-small font-medium transition-colors duration-[80ms] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 focus-visible:ring-[#191919] ${
            opt.value === value
              ? "bg-[#191919] text-white"
              : "bg-surface border border-border text-[#37352F] hover:bg-background"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
