import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { backtests, BacktestRun, Trade } from "@/lib/api";
import { C, FONT, RADIUS } from "@/lib/theme";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtCurrency(n: number) {
  return "$" + n.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function fmtPct(n: number) {
  const sign = n >= 0 ? "+" : "";
  return sign + (n * 100).toFixed(2) + "%";
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// ── Trade row ─────────────────────────────────────────────────────────────────

function TradeRow({ trade, index }: { trade: Trade; index: number }) {
  return (
    <View style={[t.row, index % 2 === 0 && t.rowAlt]}>
      <Text style={t.cell}>{trade.entry_price.toFixed(2)}</Text>
      <Text style={t.cell}>{trade.exit_price.toFixed(2)}</Text>
      <Text style={[t.cell, t.pnl, { color: trade.pnl >= 0 ? C.positive : C.negative }]}>
        {trade.pnl >= 0 ? "+" : ""}
        {fmtCurrency(trade.pnl)}
      </Text>
      <Text style={[t.cell, t.side]}>{trade.side}</Text>
    </View>
  );
}

function TradeTable({ trades }: { trades: Trade[] }) {
  return (
    <View style={t.table}>
      {/* Header */}
      <View style={[t.row, t.header]}>
        <Text style={t.headerCell}>Entry</Text>
        <Text style={t.headerCell}>Exit</Text>
        <Text style={t.headerCell}>P&amp;L</Text>
        <Text style={t.headerCell}>Side</Text>
      </View>
      {trades.map((trade, i) => (
        <TradeRow key={i} trade={trade} index={i} />
      ))}
    </View>
  );
}

// ── Metrics grid ──────────────────────────────────────────────────────────────

type Metric = { label: string; value: string; color?: string };

function MetricsGrid({ metrics }: { metrics: NonNullable<BacktestRun["metrics"]> }) {
  const items: Metric[] = [
    {
      label: "Final value",
      value: metrics.final_value != null ? fmtCurrency(metrics.final_value) : "—",
      color: metrics.final_value != null && metrics.final_value >= 100_000 ? C.positive : C.negative,
    },
    {
      label: "Sharpe",
      value: metrics.sharpe_ratio != null ? metrics.sharpe_ratio.toFixed(2) : "—",
    },
    {
      label: "Sortino",
      value: metrics.sortino_ratio != null ? metrics.sortino_ratio.toFixed(2) : "—",
    },
    {
      label: "CAGR",
      value: metrics.cagr != null ? fmtPct(metrics.cagr) : "—",
      color: metrics.cagr != null ? (metrics.cagr >= 0 ? C.positive : C.negative) : undefined,
    },
    {
      label: "Max DD",
      value: metrics.max_drawdown != null ? fmtPct(metrics.max_drawdown) : "—",
      color: C.negative,
    },
    {
      label: "Win rate",
      value: metrics.win_rate != null ? fmtPct(metrics.win_rate) : "—",
    },
    {
      label: "Trades",
      value: metrics.total_trades != null ? String(metrics.total_trades) : "—",
    },
    {
      label: "Profit factor",
      value: metrics.profit_factor != null ? metrics.profit_factor.toFixed(2) : "—",
    },
  ];

  return (
    <View style={g.grid}>
      {items.map((item) => (
        <View key={item.label} style={g.cell}>
          <Text style={g.value} numberOfLines={1} style={[g.value, item.color ? { color: item.color } : {}]}>
            {item.value}
          </Text>
          <Text style={g.label}>{item.label}</Text>
        </View>
      ))}
    </View>
  );
}

// ── Run detail ────────────────────────────────────────────────────────────────

type Tab = "metrics" | "trades" | "log";

function RunDetail({ run }: { run: BacktestRun }) {
  const [tab, setTab] = useState<Tab>("metrics");

  const tabs: { key: Tab; label: string }[] = [
    { key: "metrics", label: "Metrics" },
    { key: "trades", label: `Trades${run.trades ? ` (${run.trades.length})` : ""}` },
    { key: "log", label: "Log" },
  ];

  return (
    <View style={d.container}>
      {/* Tab bar */}
      <View style={d.tabBar}>
        {tabs.map(({ key, label }) => (
          <Pressable
            key={key}
            style={[d.tab, tab === key && d.tabActive]}
            onPress={() => setTab(key)}
          >
            <Text style={[d.tabText, tab === key && d.tabTextActive]}>{label}</Text>
          </Pressable>
        ))}
      </View>

      {/* Content */}
      {tab === "metrics" && run.metrics && (
        <MetricsGrid metrics={run.metrics} />
      )}

      {tab === "trades" && (
        <>
          {run.trades && run.trades.length > 0 ? (
            <TradeTable trades={run.trades} />
          ) : (
            <Text style={d.empty}>No trades recorded.</Text>
          )}
        </>
      )}

      {tab === "log" && (
        <ScrollView style={d.logBox} nestedScrollEnabled>
          <Text style={d.logText}>{run.log_output ?? "No log output."}</Text>
        </ScrollView>
      )}
    </View>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function ResultsScreen() {
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  async function load() {
    try {
      const data = await backtests.list();
      setRuns(data.filter((r) => r.status === "completed" || r.status === "failed"));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, []);

  function toggleExpand(id: string) {
    setExpandedId((prev) => (prev === id ? null : id));
  }

  return (
    <SafeAreaView style={s.safe} edges={["bottom"]}>
      <FlatList
        data={runs}
        keyExtractor={(item) => item.id}
        contentContainerStyle={s.list}
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.muted} />}
        ListHeaderComponent={<Text style={s.heading}>Results</Text>}
        ListEmptyComponent={
          loading ? (
            <ActivityIndicator color={C.muted} style={{ marginTop: 32 }} />
          ) : error ? (
            <Text style={s.errorText}>{error}</Text>
          ) : (
            <View style={s.emptyState}>
              <Text style={s.emptyTitle}>No completed runs</Text>
              <Text style={s.emptyBody}>Finished backtests appear here.</Text>
            </View>
          )
        }
        renderItem={({ item }) => {
          const isExpanded = expandedId === item.id;
          const succeeded = item.status === "completed";

          return (
            <View style={s.card}>
              <Pressable
                style={({ pressed }) => [s.cardHeader, pressed && s.cardHeaderPressed]}
                onPress={() => toggleExpand(item.id)}
              >
                <View style={s.cardLeft}>
                  <View style={s.runNameRow}>
                    <Text style={s.runName} numberOfLines={1}>
                      {item.strategy_name}
                    </Text>
                    {!succeeded && (
                      <View style={s.failPill}>
                        <Text style={s.failPillText}>failed</Text>
                      </View>
                    )}
                  </View>
                  <Text style={s.runMeta}>
                    {item.data_config.symbol} · {item.data_config.timeframe} · {fmtDate(item.created_at)}
                  </Text>
                  {succeeded && item.metrics && (
                    <View style={s.inlineMetrics}>
                      {item.metrics.sharpe_ratio != null && (
                        <Text style={s.inlineStat}>
                          Sharpe {item.metrics.sharpe_ratio.toFixed(2)}
                        </Text>
                      )}
                      {item.metrics.final_value != null && (
                        <Text style={[s.inlineStat, { color: C.positive }]}>
                          {fmtCurrency(item.metrics.final_value)}
                        </Text>
                      )}
                    </View>
                  )}
                </View>
                <Ionicons
                  name={isExpanded ? "chevron-up" : "chevron-down"}
                  size={18}
                  color={C.muted}
                />
              </Pressable>

              {isExpanded && <RunDetail run={item} />}
            </View>
          );
        }}
      />
    </SafeAreaView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.bg },
  list: { padding: 20, paddingBottom: 40 },

  heading: {
    fontSize: 28,
    ...FONT.serif,
    color: C.ink,
    marginBottom: 20,
  },
  errorText: { fontSize: 14, color: C.negative },
  emptyState: { alignItems: "center", paddingTop: 40 },
  emptyTitle: { fontSize: 17, fontWeight: "500", color: C.ink, marginBottom: 8 },
  emptyBody: { fontSize: 14, color: C.muted },

  card: {
    backgroundColor: C.surface,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: C.border,
    marginBottom: 10,
    overflow: "hidden",
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    padding: 16,
  },
  cardHeaderPressed: { backgroundColor: C.bg },
  cardLeft: { flex: 1, marginRight: 8 },
  runNameRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 4 },
  runName: { flex: 1, fontSize: 15, fontWeight: "500", color: C.ink },
  failPill: {
    backgroundColor: "#FEF2F2",
    borderRadius: RADIUS.tag,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  failPillText: { fontSize: 11, color: C.negative, fontWeight: "500" },
  runMeta: { fontSize: 12, color: C.muted, marginBottom: 6 },
  inlineMetrics: { flexDirection: "row", gap: 12 },
  inlineStat: { fontSize: 12, color: C.body },
});

// Metrics grid
const g = StyleSheet.create({
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    padding: 12,
    borderTopWidth: 1,
    borderTopColor: C.border,
  },
  cell: {
    width: "25%",
    padding: 8,
    alignItems: "center",
  },
  value: { fontSize: 16, fontWeight: "600", color: C.ink, marginBottom: 2 },
  label: { fontSize: 10, color: C.muted, textAlign: "center" },
});

// Trade table
const t = StyleSheet.create({
  table: { borderTopWidth: 1, borderTopColor: C.border },
  header: { backgroundColor: C.bg },
  headerCell: {
    flex: 1,
    fontSize: 11,
    fontWeight: "600",
    color: C.muted,
    textAlign: "right",
    paddingVertical: 8,
    paddingHorizontal: 6,
  },
  row: {
    flexDirection: "row",
    paddingHorizontal: 6,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
  },
  rowAlt: { backgroundColor: C.bg },
  cell: {
    flex: 1,
    fontSize: 12,
    color: C.body,
    textAlign: "right",
    paddingHorizontal: 6,
  },
  pnl: { fontWeight: "500" },
  side: { textTransform: "uppercase" },
});

// Detail panel
const d = StyleSheet.create({
  container: { borderTopWidth: 1, borderTopColor: C.border },
  tabBar: {
    flexDirection: "row",
    backgroundColor: C.bg,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    alignItems: "center",
    borderBottomWidth: 2,
    borderBottomColor: "transparent",
  },
  tabActive: { borderBottomColor: C.ink },
  tabText: { fontSize: 13, color: C.muted },
  tabTextActive: { color: C.ink, fontWeight: "500" },
  empty: { fontSize: 14, color: C.muted, padding: 20, textAlign: "center" },
  logBox: {
    backgroundColor: C.bg,
    maxHeight: 200,
    padding: 12,
    margin: 12,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: C.border,
  },
  logText: { ...FONT.mono, fontSize: 12, color: C.body, lineHeight: 18 },
});
