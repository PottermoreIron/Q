import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { backtests, strategies, BacktestRun, Strategy } from "@/lib/api";
import { C, FONT, RADIUS } from "@/lib/theme";

function fmtCurrency(n: number) {
  return "$" + n.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function fmtPct(n: number) {
  return (n * 100).toFixed(2) + "%";
}

function statusColor(status: BacktestRun["status"]) {
  if (status === "completed") return C.positive;
  if (status === "failed") return C.negative;
  if (status === "running") return C.warning;
  return C.muted;
}

type StatCardProps = { label: string; value: string };

function StatCard({ label, value }: StatCardProps) {
  return (
    <View style={s.statCard}>
      <Text style={s.statValue}>{value}</Text>
      <Text style={s.statLabel}>{label}</Text>
    </View>
  );
}

export default function DashboardScreen() {
  const router = useRouter();
  const [strats, setStrats] = useState<Strategy[]>([]);
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([strategies.list(), backtests.list()])
      .then(([s, r]) => {
        setStrats(s);
        setRuns(r);
      })
      .catch((e) => setError(String(e.message)))
      .finally(() => setLoading(false));
  }, []);

  const completed = runs.filter((r) => r.status === "completed");
  const bestSharpe = completed.reduce<BacktestRun | null>(
    (best, r) =>
      r.metrics?.sharpe_ratio != null &&
      (best === null || (r.metrics.sharpe_ratio > (best.metrics?.sharpe_ratio ?? -Infinity)))
        ? r
        : best,
    null,
  );
  const recent = [...runs].sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 5);

  return (
    <SafeAreaView style={s.safe} edges={["bottom"]}>
      <ScrollView contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>
        {/* Hero heading */}
        <Text style={s.heading}>Dashboard</Text>

        {loading && <ActivityIndicator color={C.muted} style={{ marginTop: 32 }} />}
        {!!error && <Text style={s.errorText}>{error}</Text>}

        {!loading && !error && (
          <>
            {/* Stat row */}
            <View style={s.statRow}>
              <StatCard label="Strategies" value={String(strats.length)} />
              <StatCard label="Completed" value={String(completed.length)} />
              <StatCard
                label="Best Sharpe"
                value={
                  bestSharpe?.metrics?.sharpe_ratio != null
                    ? bestSharpe.metrics.sharpe_ratio.toFixed(2)
                    : "—"
                }
              />
            </View>

            {/* Recent runs */}
            <Text style={s.sectionLabel}>Recent runs</Text>

            {recent.length === 0 && (
              <Text style={s.emptyText}>No runs yet. Go to Run to start one.</Text>
            )}

            {recent.map((run) => (
              <View key={run.id} style={s.runCard}>
                <View style={s.runHeader}>
                  <Text style={s.runName} numberOfLines={1}>
                    {run.strategy_name}
                  </Text>
                  <View style={[s.pill, { backgroundColor: statusColor(run.status) + "22" }]}>
                    <Text style={[s.pillText, { color: statusColor(run.status) }]}>
                      {run.status}
                    </Text>
                  </View>
                </View>
                <Text style={s.runSub}>
                  {run.data_config.symbol} · {run.data_config.timeframe}
                </Text>
                {run.metrics && (
                  <View style={s.metaRow}>
                    {run.metrics.sharpe_ratio != null && (
                      <Text style={s.metaItem}>
                        Sharpe {run.metrics.sharpe_ratio.toFixed(2)}
                      </Text>
                    )}
                    {run.metrics.max_drawdown != null && (
                      <Text style={[s.metaItem, { color: C.negative }]}>
                        DD {fmtPct(run.metrics.max_drawdown)}
                      </Text>
                    )}
                    {run.metrics.final_value != null && (
                      <Text style={[s.metaItem, { color: C.positive }]}>
                        {fmtCurrency(run.metrics.final_value)}
                      </Text>
                    )}
                  </View>
                )}
              </View>
            ))}

            {/* CTA */}
            <Pressable
              style={({ pressed }) => [s.cta, pressed && s.ctaPressed]}
              onPress={() => router.push("/run")}
            >
              <Text style={s.ctaText}>Run a backtest</Text>
            </Pressable>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.bg },
  scroll: { padding: 20, paddingBottom: 40 },

  heading: {
    fontSize: 28,
    ...FONT.serif,
    color: C.ink,
    marginBottom: 24,
  },

  statRow: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 28,
  },
  statCard: {
    flex: 1,
    backgroundColor: C.surface,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: C.border,
    padding: 14,
    alignItems: "center",
  },
  statValue: { fontSize: 22, fontWeight: "600", color: C.ink, marginBottom: 2 },
  statLabel: { fontSize: 11, color: C.muted },

  sectionLabel: {
    fontSize: 11,
    fontWeight: "600",
    color: C.muted,
    letterSpacing: 0.8,
    textTransform: "uppercase",
    marginBottom: 10,
  },
  emptyText: { fontSize: 14, color: C.muted, marginBottom: 20 },

  runCard: {
    backgroundColor: C.surface,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: C.border,
    padding: 14,
    marginBottom: 10,
  },
  runHeader: { flexDirection: "row", alignItems: "center", marginBottom: 4 },
  runName: { flex: 1, fontSize: 15, fontWeight: "500", color: C.ink },
  pill: {
    borderRadius: RADIUS.tag,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  pillText: { fontSize: 11, fontWeight: "500" },
  runSub: { fontSize: 12, color: C.muted, marginBottom: 6 },
  metaRow: { flexDirection: "row", gap: 12 },
  metaItem: { fontSize: 12, color: C.body },

  errorText: { fontSize: 14, color: C.negative, marginTop: 16 },

  cta: {
    marginTop: 28,
    backgroundColor: C.ink,
    borderRadius: RADIUS.input,
    paddingVertical: 14,
    alignItems: "center",
  },
  ctaPressed: { opacity: 0.75 },
  ctaText: { fontSize: 15, fontWeight: "600", color: C.surface },
});
