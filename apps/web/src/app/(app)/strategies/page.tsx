"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { strategies as api, type Strategy } from "@/lib/api";

export default function StrategiesPage() {
  const [items, setItems] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.list().then(setItems).finally(() => setLoading(false));
  }, []);

  const handleDelete = async (id: string) => {
    await api.delete(id);
    setItems((prev) => prev.filter((s) => s.id !== id));
  };

  return (
    <div>
      <div className="flex items-baseline justify-between mb-8">
        <div>
          <h1 className="font-serif italic text-display text-ink mb-1">Strategies</h1>
          <p className="text-body text-muted">Your saved trading strategies.</p>
        </div>
        <Link
          href="/strategies/new"
          className="px-4 py-2 bg-ink text-white text-body font-medium rounded-md active:scale-[0.97] transition-transform duration-[80ms]"
        >
          New Strategy
        </Link>
      </div>

      {loading ? (
        <div className="py-24 text-center">
          <p className="font-serif italic text-title text-muted">Loading…</p>
        </div>
      ) : items.length === 0 ? (
        <div className="py-24 text-center">
          <p className="font-serif italic text-title text-muted mb-4">No strategies yet.</p>
          <Link
            href="/strategies/new"
            className="px-4 py-2 bg-ink text-white text-body font-medium rounded-md"
          >
            Create your first strategy
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((s, i) => (
            <div
              key={s.id}
              className="bg-surface border border-border rounded-lg px-5 py-4 flex items-center justify-between animate-slide-up-fade"
              style={{ animationDelay: `${i * 40}ms` }}
            >
              <div>
                <Link href={`/strategies/${s.id}`} className="font-serif italic text-title text-ink hover:opacity-70 transition-opacity duration-[80ms]">
                  {s.name}
                </Link>
                {s.description && (
                  <p className="text-small text-muted mt-0.5">{s.description}</p>
                )}
                <p className="text-small text-muted mt-1">
                  {s.blocks.length} block{s.blocks.length !== 1 ? "s" : ""} ·{" "}
                  {new Date(s.updated_at).toLocaleDateString("en-US", {
                    month: "short", day: "numeric", year: "numeric",
                  })}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <Link
                  href={`/strategies/${s.id}`}
                  className="text-small text-muted hover:text-body transition-colors duration-[80ms]"
                >
                  Edit
                </Link>
                <button
                  onClick={() => handleDelete(s.id)}
                  className="text-small text-muted hover:text-negative transition-colors duration-[80ms]"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
