"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";
import { strategies as api, type Strategy, type StrategyBlock } from "@/lib/api";
import { BLOCK_BY_NAME, BLOCK_CATALOG, BLOCKS_BY_TYPE, type BlockDef } from "@/lib/block-catalog";

// Monaco is large — load it lazily so the page shell renders immediately
const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

const TYPE_LABEL: Record<string, string> = {
  indicator: "Indicators",
  condition: "Conditions",
  action:    "Risk",
};

const TYPE_ORDER = ["indicator", "condition", "action"] as const;

function newBlock(def: BlockDef): StrategyBlock {
  return {
    id: crypto.randomUUID(),
    type: def.type,
    name: def.name,
    params: { ...def.defaultParams },
  };
}

export default function StrategyBuilderPage({ params }: { params: { id: string } }) {
  const isNew = params.id === "new";

  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const [name, setName] = useState("Untitled Strategy");
  const [blocks, setBlocks] = useState<StrategyBlock[]>([]);
  const [code, setCode] = useState("");
  const [mode, setMode] = useState<"blocks" | "code">("blocks");
  const [codeManual, setCodeManual] = useState(false); // user edited code directly
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [paletteOpen, setPaletteOpen] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load existing strategy
  useEffect(() => {
    if (!isNew) {
      api.get(params.id).then((s) => {
        setStrategy(s);
        setName(s.name);
        setBlocks(s.blocks as StrategyBlock[]);
        setCode(s.python_code ?? "");
      });
    } else {
      api.compile([]).then((r) => setCode(r.python_code));
    }
  }, [params.id, isNew]);

  // When blocks change (and user hasn't manually edited code), recompile
  const recompile = useCallback(async (newBlocks: StrategyBlock[]) => {
    if (codeManual) return;
    const result = await api.compile(newBlocks);
    setCode(result.python_code);
  }, [codeManual]);

  const handleAddBlock = (def: BlockDef) => {
    const block = newBlock(def);
    const next = [...blocks, block];
    setBlocks(next);
    recompile(next);
    setPaletteOpen(null);
  };

  const handleRemoveBlock = (id: string) => {
    const next = blocks.filter((b) => b.id !== id);
    setBlocks(next);
    recompile(next);
  };

  const handleParamChange = (blockId: string, key: string, value: unknown) => {
    const next = blocks.map((b) => b.id === blockId ? { ...b, params: { ...b.params, [key]: value } } : b);
    setBlocks(next);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => recompile(next), 400);
  };

  const handleCodeChange = (value: string | undefined) => {
    const v = value ?? "";
    setCode(v);
    setCodeManual(true);
    // Debounced validation
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      const result = await api.validate(v);
      setValidationErrors(result.errors);
    }, 600);
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      const payload = {
        name,
        blocks: codeManual ? [] : blocks,
        python_code: codeManual ? code : undefined,
      };
      if (isNew || !strategy) {
        const s = await api.create(payload);
        setStrategy(s);
        // Update URL without full navigation
        window.history.replaceState({}, "", `/strategies/${s.id}`);
      } else {
        const s = await api.update(strategy.id, payload);
        setStrategy(s);
      }
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-0px)] -my-12 -mx-8">
      {/* Top bar */}
      <header className="flex items-center gap-4 px-8 py-4 bg-surface border-b border-border flex-shrink-0">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="font-serif italic text-title text-ink bg-transparent outline-none border-b border-transparent focus:border-border w-72 transition-colors duration-[80ms]"
          placeholder="Strategy name"
        />

        {/* Mode toggle */}
        <div className="flex items-center bg-background border border-border rounded-md p-0.5 ml-4">
          {(["blocks", "code"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-3 py-1 text-small font-medium rounded-sm transition-colors duration-[80ms] capitalize ${
                mode === m ? "bg-surface text-ink shadow-float" : "text-muted hover:text-body"
              }`}
            >
              {m === "blocks" ? "Blocks" : "Python"}
            </button>
          ))}
        </div>

        {codeManual && mode === "code" && (
          <button
            onClick={() => { setCodeManual(false); recompile(blocks); }}
            className="text-small text-muted hover:text-body transition-colors duration-[80ms]"
          >
            ← Reset to blocks
          </button>
        )}

        <div className="ml-auto flex items-center gap-3">
          {saveError && <span className="text-small text-negative">{saveError}</span>}
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-1.5 w-20 bg-ink text-white text-body font-medium rounded-md disabled:opacity-50 active:scale-[0.97] transition-transform duration-[80ms]"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left panel */}
        <div className="w-72 flex-shrink-0 bg-surface border-r border-border flex flex-col overflow-y-auto">
          {mode === "blocks" ? (
            <div className="p-4 space-y-5">
              {/* Add block palette */}
              <div>
                <p className="text-label uppercase tracking-widest text-muted mb-3">Add Block</p>
                {TYPE_ORDER.map((type) => (
                  <div key={type} className="mb-3">
                    <button
                      onClick={() => setPaletteOpen(paletteOpen === type ? null : type)}
                      className="w-full flex items-center justify-between text-heading font-medium text-body hover:text-ink transition-colors duration-[80ms] mb-1"
                    >
                      <span>{TYPE_LABEL[type]}</span>
                      <span className="text-muted text-small">{paletteOpen === type ? "−" : "+"}</span>
                    </button>
                    {paletteOpen === type && (
                      <div className="space-y-1 pl-2 animate-slide-in-left">
                        {BLOCKS_BY_TYPE[type].map((def) => (
                          <button
                            key={def.name}
                            onClick={() => handleAddBlock(def)}
                            className="w-full text-left px-3 py-2 rounded-md text-body hover:bg-background transition-colors duration-[80ms] group"
                          >
                            <span className="font-medium text-ink">{def.label}</span>
                            <span className="block text-small text-muted">{def.description}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Current blocks */}
              {blocks.length > 0 && (
                <div>
                  <p className="text-label uppercase tracking-widest text-muted mb-3">Strategy ({blocks.length})</p>
                  <div className="space-y-2">
                    {blocks.map((block) => {
                      const def = BLOCK_BY_NAME[block.name];
                      return (
                        <div key={block.id} className="bg-background border border-border rounded-md p-3 animate-slide-in-left">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-body font-medium text-ink">{def?.label ?? block.name}</span>
                            <button
                              onClick={() => handleRemoveBlock(block.id)}
                              className="text-small text-muted hover:text-negative transition-colors duration-[80ms]"
                            >
                              ×
                            </button>
                          </div>
                          {def?.paramDefs.map((pd) => (
                            <div key={pd.key} className="flex items-center justify-between mt-1">
                              <label className="text-small text-muted">{pd.label}</label>
                              <input
                                type="number"
                                value={block.params[pd.key] as number}
                                min={pd.min}
                                max={pd.max}
                                onChange={(e) => handleParamChange(block.id, pd.key, parseFloat(e.target.value))}
                                className="w-16 text-right text-small text-ink bg-surface border border-border rounded px-1.5 py-0.5 outline-none focus:border-body transition-colors duration-[80ms]"
                              />
                            </div>
                          ))}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {blocks.length === 0 && (
                <p className="font-serif italic text-body text-muted text-center py-8">
                  Add blocks to build your strategy.
                </p>
              )}
            </div>
          ) : (
            <div className="p-4">
              <p className="text-label uppercase tracking-widest text-muted mb-3">Validation</p>
              {validationErrors.length === 0 ? (
                <p className="text-small text-positive">✓ No issues</p>
              ) : (
                <ul className="space-y-1">
                  {validationErrors.map((e, i) => (
                    <li key={i} className="text-small text-negative">{e}</li>
                  ))}
                </ul>
              )}

              <div className="mt-6">
                <p className="text-label uppercase tracking-widest text-muted mb-3">Block Catalog</p>
                <div className="space-y-1">
                  {BLOCK_CATALOG.map((def) => (
                    <div key={def.name} className="text-small text-muted">
                      <span className="text-ink font-medium">{def.label}</span>
                      {" — "}{def.description}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right panel — Monaco editor */}
        <div className="flex-1 overflow-hidden">
          <MonacoEditor
            language="python"
            value={code}
            onChange={handleCodeChange}
            theme="vs"
            options={{
              fontSize: 13,
              fontFamily: "'JetBrains Mono', 'Menlo', monospace",
              fontLigatures: true,
              lineHeight: 22,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              renderLineHighlight: "none",
              overviewRulerBorder: false,
              hideCursorInOverviewRuler: true,
              padding: { top: 20, bottom: 20 },
              lineNumbersMinChars: 3,
              glyphMargin: false,
              folding: true,
              tabSize: 4,
              wordWrap: "on",
            }}
          />
        </div>
      </div>
    </div>
  );
}
