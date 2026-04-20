"use client";

import { useCallback, useState } from "react";
import { data as dataApi, type AssetClass, type DataPreview, type SymbolResult, type Timeframe } from "@/lib/api";

const ASSET_CLASSES: { value: AssetClass; label: string }[] = [
  { value: "crypto", label: "Crypto" },
  { value: "stock", label: "Stock" },
  { value: "forex", label: "Forex" },
  { value: "futures", label: "Futures" },
];

const TIMEFRAMES: { value: Timeframe; label: string }[] = [
  { value: "1m", label: "1m" }, { value: "5m", label: "5m" },
  { value: "15m", label: "15m" }, { value: "30m", label: "30m" },
  { value: "1h", label: "1h" }, { value: "4h", label: "4h" },
  { value: "1d", label: "1D" }, { value: "1w", label: "1W" },
  { value: "1M", label: "1M" },
];

const SOURCES = [
  { value: "csv",     label: "CSV Upload" },
  { value: "yahoo",   label: "Yahoo Finance" },
  { value: "binance", label: "Binance" },
  { value: "akshare", label: "AkShare" },
];

export default function DataPage() {
  const [source, setSource] = useState<string>("yahoo");
  const [assetClass, setAssetClass] = useState<AssetClass>("stock");
  const [timeframe, setTimeframe] = useState<Timeframe>("1d");
  const [startDate, setStartDate] = useState("2022-01-01");
  const [endDate, setEndDate] = useState("2023-12-31");

  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SymbolResult[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<SymbolResult | null>(null);

  const [preview, setPreview] = useState<DataPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  const handleSearch = useCallback(async (q: string) => {
    setQuery(q);
    if (q.length < 1) { setSearchResults([]); return; }
    try {
      const results = await dataApi.search(q, assetClass);
      setSearchResults(results);
    } catch {
      setSearchResults([]);
    }
  }, [assetClass]);

  const handleSelectSymbol = (s: SymbolResult) => {
    setSelectedSymbol(s);
    setAssetClass(s.asset_class);
    setQuery(s.symbol);
    setSearchResults([]);
  };

  const handlePreview = async () => {
    if (!selectedSymbol) return;
    setError(null);
    setIsPending(true);
    try {
      const result = await dataApi.fetch({
        symbol: selectedSymbol.symbol,
        asset_class: selectedSymbol.asset_class,
        timeframe,
        start_date: startDate,
        end_date: endDate,
      });
      setPreview(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch data");
    } finally {
      setIsPending(false);
    }
  };

  const handleCSVUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsPending(true);
    try {
      await dataApi.upload(file);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setIsPending(false);
    }
  };

  return (
    <div>
      {/* Page header */}
      <h1 className="font-serif italic text-display text-ink mb-1">Data</h1>
      <p className="text-body text-muted mb-8">Configure your data source before running a backtest.</p>

      <div className="grid grid-cols-[1fr_1fr] gap-6">
        {/* Left column — configuration */}
        <div className="space-y-6">

          {/* Source */}
          <section>
            <h2 className="text-heading font-medium text-body mb-2 pb-2 border-b border-border">Source</h2>
            <div className="flex gap-2">
              {SOURCES.map((s) => (
                <button
                  key={s.value}
                  onClick={() => setSource(s.value)}
                  className={`px-3 py-1.5 text-body rounded-md border transition-colors duration-[80ms] ${
                    source === s.value
                      ? "bg-ink text-white border-ink"
                      : "bg-surface text-body border-border hover:border-body"
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </section>

          {source === "csv" ? (
            <section>
              <h2 className="text-heading font-medium text-body mb-2 pb-2 border-b border-border">Upload CSV</h2>
              <p className="text-small text-muted mb-3">
                Expected columns: timestamp, open, high, low, close, volume
              </p>
              <label className="flex items-center justify-center h-24 border-2 border-dashed border-border rounded-lg cursor-pointer hover:border-body transition-colors duration-[80ms]">
                <span className="text-body text-muted">Drop a CSV file or click to browse</span>
                <input type="file" accept=".csv" className="sr-only" onChange={handleCSVUpload} />
              </label>
            </section>
          ) : (
            <>
              {/* Symbol search */}
              <section>
                <h2 className="text-heading font-medium text-body mb-2 pb-2 border-b border-border">Symbol</h2>
                <div className="relative">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => handleSearch(e.target.value)}
                    placeholder="Search BTC, AAPL, EUR/USD…"
                    className="w-full px-3 py-2 text-body bg-surface border border-border rounded-md outline-none focus:border-body transition-colors duration-[80ms] placeholder:text-muted"
                  />
                  {searchResults.length > 0 && (
                    <ul className="absolute z-10 w-full mt-1 bg-surface border border-border rounded-md shadow-float overflow-hidden">
                      {searchResults.map((r) => (
                        <li key={r.symbol}>
                          <button
                            onClick={() => handleSelectSymbol(r)}
                            className="w-full flex items-center justify-between px-3 py-2 text-body hover:bg-background transition-colors duration-[80ms]"
                          >
                            <span className="font-medium text-ink">{r.symbol}</span>
                            <span className="text-small text-muted">{r.name}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                {selectedSymbol && (
                  <p className="mt-2 text-small text-muted">
                    {selectedSymbol.name} · {selectedSymbol.exchange}
                  </p>
                )}
              </section>

              {/* Asset class */}
              <section>
                <h2 className="text-heading font-medium text-body mb-2 pb-2 border-b border-border">Asset Class</h2>
                <div className="flex gap-2 flex-wrap">
                  {ASSET_CLASSES.map((ac) => (
                    <button
                      key={ac.value}
                      onClick={() => setAssetClass(ac.value)}
                      className={`px-3 py-1.5 text-body rounded-md border transition-colors duration-[80ms] ${
                        assetClass === ac.value
                          ? "bg-ink text-white border-ink"
                          : "bg-surface text-body border-border hover:border-body"
                      }`}
                    >
                      {ac.label}
                    </button>
                  ))}
                </div>
              </section>

              {/* Timeframe */}
              <section>
                <h2 className="text-heading font-medium text-body mb-2 pb-2 border-b border-border">Timeframe</h2>
                <div className="flex gap-1.5 flex-wrap">
                  {TIMEFRAMES.map((tf) => (
                    <button
                      key={tf.value}
                      onClick={() => setTimeframe(tf.value)}
                      className={`w-10 py-1.5 text-small font-medium rounded-sm border transition-colors duration-[80ms] ${
                        timeframe === tf.value
                          ? "bg-ink text-white border-ink"
                          : "bg-surface text-muted border-border hover:border-body hover:text-body"
                      }`}
                    >
                      {tf.label}
                    </button>
                  ))}
                </div>
              </section>

              {/* Date range */}
              <section>
                <h2 className="text-heading font-medium text-body mb-2 pb-2 border-b border-border">Date Range</h2>
                <div className="flex gap-3">
                  <div className="flex-1">
                    <label className="block text-label uppercase tracking-widest text-muted mb-1">From</label>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="w-full px-3 py-2 text-small text-[#191919] bg-surface border border-border rounded-md outline-none focus:border-[#37352F] transition-colors duration-[80ms] [color-scheme:light] [&::-webkit-calendar-picker-indicator]:opacity-40 [&::-webkit-calendar-picker-indicator]:cursor-pointer"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="block text-label uppercase tracking-widest text-muted mb-1">To</label>
                    <input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="w-full px-3 py-2 text-small text-[#191919] bg-surface border border-border rounded-md outline-none focus:border-[#37352F] transition-colors duration-[80ms] [color-scheme:light] [&::-webkit-calendar-picker-indicator]:opacity-40 [&::-webkit-calendar-picker-indicator]:cursor-pointer"
                    />
                  </div>
                </div>
              </section>

              {/* Actions */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={handlePreview}
                  disabled={!selectedSymbol || isPending}
                  className="px-5 py-2 bg-ink text-white text-body font-medium rounded-md disabled:opacity-40 active:scale-[0.97] transition-[opacity,transform] duration-[80ms]"
                >
                  {isPending ? "Loading…" : "Preview Data"}
                </button>
              </div>
            </>
          )}
        </div>

        {/* Right column — preview */}
        <div>
          {error && (
            <div className="p-4 bg-surface border border-border rounded-lg">
              <p className="text-body text-negative">{error}</p>
            </div>
          )}

          {preview && (
            <div className="bg-surface border border-border rounded-lg p-5 animate-slide-up-fade">
              <div className="flex items-baseline justify-between mb-4">
                <h2 className="font-serif italic text-title text-ink">{preview.symbol}</h2>
                <span className="text-small text-muted">{preview.bar_count.toLocaleString()} bars</span>
              </div>

              <div className="flex gap-6 mb-5">
                <div>
                  <p className="text-data text-ink">{preview.timeframe}</p>
                  <p className="text-label uppercase tracking-widest text-muted mt-0.5">Timeframe</p>
                </div>
                <div>
                  <p className="text-data text-ink">{preview.start_date}</p>
                  <p className="text-label uppercase tracking-widest text-muted mt-0.5">From</p>
                </div>
                <div>
                  <p className="text-data text-ink">{preview.end_date}</p>
                  <p className="text-label uppercase tracking-widest text-muted mt-0.5">To</p>
                </div>
              </div>

              {/* Sample bars table */}
              <table className="w-full text-small">
                <thead>
                  <tr className="border-b border-border">
                    {["Date", "Open", "High", "Low", "Close", "Volume"].map((h) => (
                      <th key={h} className="text-left pb-2 text-label uppercase tracking-widest text-muted font-medium">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.bars.map((bar) => {
                    const date = new Date(bar.timestamp).toLocaleDateString("en-US", {
                      month: "short", day: "numeric", year: "numeric",
                    });
                    const isUp = bar.close >= bar.open;
                    return (
                      <tr key={bar.timestamp} className="border-b border-border last:border-0">
                        <td className="py-2 text-muted font-mono text-mono">{date}</td>
                        <td className="py-2 font-mono text-mono text-body">{bar.open.toFixed(2)}</td>
                        <td className="py-2 font-mono text-mono text-body">{bar.high.toFixed(2)}</td>
                        <td className="py-2 font-mono text-mono text-body">{bar.low.toFixed(2)}</td>
                        <td className={`py-2 font-mono text-mono font-medium ${isUp ? "text-positive" : "text-negative"}`}>
                          {bar.close.toFixed(2)}
                        </td>
                        <td className="py-2 font-mono text-mono text-muted">
                          {bar.volume.toLocaleString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              <p className="text-small text-muted mt-3">Showing first 5 bars of {preview.bar_count.toLocaleString()}</p>
            </div>
          )}

          {!preview && !error && (
            <div className="h-full flex items-center justify-center py-24">
              <p className="font-serif italic text-title text-muted text-center">
                Configure a source and preview data.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
