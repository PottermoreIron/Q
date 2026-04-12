import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { backtests, strategies as api, BacktestRun, Strategy } from "@/lib/api";
import { C, FONT, RADIUS } from "@/lib/theme";

// ── Constants ─────────────────────────────────────────────────────────────────

const ASSET_CLASSES = ["stock", "crypto", "forex", "futures"] as const;
const TIMEFRAMES = ["1d", "4h", "1h", "15m", "1w"] as const;
const SOURCES = ["yahoo", "binance", "polygon", "alpha_vantage", "alpaca"] as const;

type AssetClass = (typeof ASSET_CLASSES)[number];
type Timeframe = (typeof TIMEFRAMES)[number];
type Source = (typeof SOURCES)[number];

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtCurrency(n: number) {
  return "$" + n.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function fmtPct(n: number) {
  const sign = n >= 0 ? "+" : "";
  return sign + (n * 100).toFixed(2) + "%";
}

function isTerminal(status: BacktestRun["status"]) {
  return status === "completed" || status === "failed";
}

// ── Sub-components ────────────────────────────────────────────────────────────

type ChipRowProps<T extends string> = {
  options: readonly T[];
  value: T;
  onChange: (v: T) => void;
};

function ChipRow<T extends string>({ options, value, onChange }: ChipRowProps<T>) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.chipScroll}>
      {options.map((opt) => (
        <Pressable
          key={opt}
          style={[s.chip, value === opt && s.chipActive]}
          onPress={() => onChange(opt)}
        >
          <Text style={[s.chipText, value === opt && s.chipTextActive]}>{opt}</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}

type PickerModalProps = {
  visible: boolean;
  title: string;
  items: Strategy[];
  selected: string | null;
  onSelect: (id: string) => void;
  onClose: () => void;
};

function PickerModal({ visible, title, items, selected, onSelect, onClose }: PickerModalProps) {
  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <SafeAreaView style={pm.safe} edges={["top", "bottom"]}>
        <View style={pm.header}>
          <Text style={pm.title}>{title}</Text>
          <Pressable onPress={onClose} hitSlop={16}>
            <Ionicons name="close" size={22} color={C.body} />
          </Pressable>
        </View>
        <ScrollView contentContainerStyle={pm.list}>
          {items.map((item) => (
            <Pressable
              key={item.id}
              style={[pm.item, selected === item.id && pm.itemActive]}
              onPress={() => { onSelect(item.id); onClose(); }}
            >
              <Text style={pm.itemText} numberOfLines={1}>{item.name}</Text>
              {selected === item.id && (
                <Ionicons name="checkmark" size={18} color={C.ink} />
              )}
            </Pressable>
          ))}
          {items.length === 0 && (
            <Text style={pm.empty}>No strategies found.</Text>
          )}
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}

type MetricRowProps = { label: string; value: string; color?: string };

function MetricRow({ label, value, color }: MetricRowProps) {
  return (
    <View style={s.metricRow}>
      <Text style={s.metricLabel}>{label}</Text>
      <Text style={[s.metricValue, color ? { color } : {}]}>{value}</Text>
    </View>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function RunScreen() {
  const [strats, setStrats] = useState<Strategy[]>([]);
  const [strategyId, setStrategyId] = useState<string | null>(null);
  const [symbol, setSymbol] = useState("AAPL");
  const [assetClass, setAssetClass] = useState<AssetClass>("stock");
  const [timeframe, setTimeframe] = useState<Timeframe>("1d");
  const [source, setSource] = useState<Source>("yahoo");
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2023-12-31");
  const [pickerOpen, setPickerOpen] = useState(false);
  const [running, setRunning] = useState(false);
  const [run, setRun] = useState<BacktestRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    api.list().then((s) => {
      setStrats(s);
      if (s.length > 0) setStrategyId(s[0].id);
    });
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const selectedStrategy = strats.find((s) => s.id === strategyId) ?? null;

  async function handleRun() {
    if (!strategyId) return;
    setError(null);
    setRun(null);
    setRunning(true);

    try {
      const created = await backtests.create({
        strategy_id: strategyId,
        data_config: {
          source,
          symbol: symbol.trim().toUpperCase(),
          asset_class: assetClass,
          timeframe,
          start_date: startDate,
          end_date: endDate,
        },
      });

      setRun(created);

      if (!isTerminal(created.status)) {
        pollRef.current = setInterval(async () => {
          try {
            const updated = await backtests.get(created.id);
            setRun(updated);
            if (isTerminal(updated.status)) {
              clearInterval(pollRef.current!);
              pollRef.current = null;
            }
          } catch {
            clearInterval(pollRef.current!);
            pollRef.current = null;
          }
        }, 1500);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  return (
    <SafeAreaView style={s.safe} edges={["bottom"]}>
      <ScrollView contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
        <Text style={s.heading}>Run Backtest</Text>

        {/* Strategy picker */}
        <Text style={s.fieldLabel}>Strategy</Text>
        <Pressable style={s.selectBox} onPress={() => setPickerOpen(true)}>
          <Text style={selectedStrategy ? s.selectText : s.selectPlaceholder} numberOfLines={1}>
            {selectedStrategy?.name ?? "Select a strategy…"}
          </Text>
          <Ionicons name="chevron-down" size={16} color={C.muted} />
        </Pressable>

        {/* Symbol */}
        <Text style={s.fieldLabel}>Symbol</Text>
        <TextInput
          style={s.input}
          value={symbol}
          onChangeText={setSymbol}
          placeholder="e.g. AAPL"
          placeholderTextColor={C.muted}
          autoCapitalize="characters"
          returnKeyType="done"
        />

        {/* Asset class */}
        <Text style={s.fieldLabel}>Asset class</Text>
        <ChipRow options={ASSET_CLASSES} value={assetClass} onChange={setAssetClass} />

        {/* Timeframe */}
        <Text style={s.fieldLabel}>Timeframe</Text>
        <ChipRow options={TIMEFRAMES} value={timeframe} onChange={setTimeframe} />

        {/* Source */}
        <Text style={s.fieldLabel}>Data source</Text>
        <ChipRow options={SOURCES} value={source} onChange={setSource} />

        {/* Date range */}
        <View style={s.dateRow}>
          <View style={s.dateField}>
            <Text style={s.fieldLabel}>Start date</Text>
            <TextInput
              style={s.input}
              value={startDate}
              onChangeText={setStartDate}
              placeholder="YYYY-MM-DD"
              placeholderTextColor={C.muted}
              keyboardType="numbers-and-punctuation"
              returnKeyType="done"
            />
          </View>
          <View style={s.dateField}>
            <Text style={s.fieldLabel}>End date</Text>
            <TextInput
              style={s.input}
              value={endDate}
              onChangeText={setEndDate}
              placeholder="YYYY-MM-DD"
              placeholderTextColor={C.muted}
              keyboardType="numbers-and-punctuation"
              returnKeyType="done"
            />
          </View>
        </View>

        {/* Run button */}
        <Pressable
          style={({ pressed }) => [s.runBtn, (!strategyId || running) && s.runBtnDisabled, pressed && s.runBtnPressed]}
          onPress={handleRun}
          disabled={!strategyId || running}
        >
          {running ? (
            <ActivityIndicator color={C.surface} />
          ) : (
            <Text style={s.runBtnText}>Run backtest</Text>
          )}
        </Pressable>

        {/* Error */}
        {!!error && (
          <View style={s.errorBox}>
            <Ionicons name="alert-circle-outline" size={16} color={C.negative} />
            <Text style={s.errorText}>{error}</Text>
          </View>
        )}

        {/* Results */}
        {run && <RunResult run={run} />}
      </ScrollView>

      <PickerModal
        visible={pickerOpen}
        title="Select strategy"
        items={strats}
        selected={strategyId}
        onSelect={setStrategyId}
        onClose={() => setPickerOpen(false)}
      />
    </SafeAreaView>
  );
}

// ── Results panel ─────────────────────────────────────────────────────────────

function RunResult({ run }: { run: BacktestRun }) {
  if (run.status === "pending" || run.status === "running") {
    return (
      <View style={s.resultCard}>
        <ActivityIndicator color={C.muted} />
        <Text style={s.runningText}>Running…</Text>
      </View>
    );
  }

  if (run.status === "failed") {
    return (
      <View style={s.resultCard}>
        <Text style={s.resultHeading}>Failed</Text>
        <Text style={s.errorText}>{run.error_message ?? "Unknown error"}</Text>
        {run.log_output ? (
          <ScrollView style={s.logBox}>
            <Text style={s.logText}>{run.log_output}</Text>
          </ScrollView>
        ) : null}
      </View>
    );
  }

  const m = run.metrics;
  if (!m) return null;

  return (
    <View style={s.resultCard}>
      <Text style={s.resultHeading}>Results</Text>

      {m.final_value != null && (
        <MetricRow
          label="Final value"
          value={fmtCurrency(m.final_value)}
          color={m.final_value >= 100_000 ? C.positive : C.negative}
        />
      )}
      {m.sharpe_ratio != null && (
        <MetricRow label="Sharpe ratio" value={m.sharpe_ratio.toFixed(2)} />
      )}
      {m.sortino_ratio != null && (
        <MetricRow label="Sortino ratio" value={m.sortino_ratio.toFixed(2)} />
      )}
      {m.cagr != null && (
        <MetricRow
          label="CAGR"
          value={fmtPct(m.cagr)}
          color={m.cagr >= 0 ? C.positive : C.negative}
        />
      )}
      {m.max_drawdown != null && (
        <MetricRow label="Max drawdown" value={fmtPct(m.max_drawdown)} color={C.negative} />
      )}
      {m.win_rate != null && (
        <MetricRow label="Win rate" value={fmtPct(m.win_rate)} />
      )}
      {m.total_trades != null && (
        <MetricRow label="Total trades" value={String(m.total_trades)} />
      )}
      {m.profit_factor != null && (
        <MetricRow label="Profit factor" value={m.profit_factor.toFixed(2)} />
      )}

      {run.log_output ? (
        <>
          <Text style={[s.fieldLabel, { marginTop: 16 }]}>Log</Text>
          <ScrollView style={s.logBox} nestedScrollEnabled>
            <Text style={s.logText}>{run.log_output}</Text>
          </ScrollView>
        </>
      ) : null}
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.bg },
  scroll: { padding: 20, paddingBottom: 40 },

  heading: { fontSize: 28, ...FONT.serif, color: C.ink, marginBottom: 24 },

  fieldLabel: {
    fontSize: 12,
    fontWeight: "500",
    color: C.muted,
    marginBottom: 6,
    marginTop: 16,
  },
  input: {
    backgroundColor: C.surface,
    borderRadius: RADIUS.input,
    borderWidth: 1,
    borderColor: C.border,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    color: C.ink,
  },
  selectBox: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: C.surface,
    borderRadius: RADIUS.input,
    borderWidth: 1,
    borderColor: C.border,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  selectText: { flex: 1, fontSize: 15, color: C.ink },
  selectPlaceholder: { flex: 1, fontSize: 15, color: C.muted },

  chipScroll: { marginVertical: 2 },
  chip: {
    borderRadius: RADIUS.tag,
    borderWidth: 1,
    borderColor: C.border,
    backgroundColor: C.surface,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginRight: 8,
  },
  chipActive: { backgroundColor: C.ink, borderColor: C.ink },
  chipText: { fontSize: 13, color: C.body },
  chipTextActive: { color: C.surface },

  dateRow: { flexDirection: "row", gap: 12 },
  dateField: { flex: 1 },

  runBtn: {
    marginTop: 28,
    backgroundColor: C.ink,
    borderRadius: RADIUS.input,
    paddingVertical: 14,
    alignItems: "center",
  },
  runBtnDisabled: { backgroundColor: C.muted },
  runBtnPressed: { opacity: 0.8 },
  runBtnText: { fontSize: 15, fontWeight: "600", color: C.surface },

  errorBox: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
    marginTop: 16,
    backgroundColor: "#FEF2F2",
    borderRadius: RADIUS.card,
    padding: 14,
  },
  errorText: { flex: 1, fontSize: 14, color: C.negative, lineHeight: 20 },

  resultCard: {
    marginTop: 24,
    backgroundColor: C.surface,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: C.border,
    padding: 16,
  },
  resultHeading: { fontSize: 16, fontWeight: "600", color: C.ink, marginBottom: 12 },
  runningText: { fontSize: 14, color: C.muted, textAlign: "center", marginTop: 8 },

  metricRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
  },
  metricLabel: { fontSize: 14, color: C.muted },
  metricValue: { fontSize: 14, fontWeight: "500", color: C.ink },

  logBox: {
    backgroundColor: C.bg,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: C.border,
    maxHeight: 160,
    padding: 12,
    marginTop: 6,
  },
  logText: { ...FONT.mono, fontSize: 12, color: C.body, lineHeight: 18 },
});

const pm = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.bg },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
    backgroundColor: C.surface,
  },
  title: { flex: 1, fontSize: 17, fontWeight: "600", color: C.ink },
  list: { padding: 20, paddingBottom: 40 },
  item: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: C.surface,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: C.border,
    paddingHorizontal: 16,
    paddingVertical: 14,
    marginBottom: 10,
  },
  itemActive: { borderColor: C.ink },
  itemText: { flex: 1, fontSize: 15, color: C.ink },
  empty: { fontSize: 14, color: C.muted, textAlign: "center", marginTop: 40 },
});
