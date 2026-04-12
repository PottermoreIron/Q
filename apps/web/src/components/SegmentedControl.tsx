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
          className={`px-3 py-1.5 rounded text-small font-medium transition-colors duration-[80ms] ${
            opt.value === value
              ? "bg-ink text-white"
              : "bg-surface border border-border text-body hover:bg-background"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
