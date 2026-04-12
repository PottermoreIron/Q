import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { strategies as api, Strategy } from "@/lib/api";
import { C, FONT, RADIUS } from "@/lib/theme";

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

type CodeModalProps = {
  strategy: Strategy | null;
  onClose: () => void;
};

function CodeModal({ strategy, onClose }: CodeModalProps) {
  if (!strategy) return null;

  const code = strategy.python_code ?? "# No Python code — strategy uses blocks only.";
  const blockCount = strategy.blocks.length;

  return (
    <Modal visible animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <SafeAreaView style={m.safe} edges={["top", "bottom"]}>
        <View style={m.header}>
          <Text style={m.title} numberOfLines={1}>
            {strategy.name}
          </Text>
          <Pressable onPress={onClose} hitSlop={16}>
            <Ionicons name="close" size={22} color={C.body} />
          </Pressable>
        </View>

        {blockCount > 0 && (
          <View style={m.blocksRow}>
            <Ionicons name="layers-outline" size={14} color={C.muted} />
            <Text style={m.blocksMeta}>{blockCount} block{blockCount !== 1 ? "s" : ""}</Text>
          </View>
        )}

        {strategy.description ? (
          <Text style={m.description}>{strategy.description}</Text>
        ) : null}

        <Text style={m.codeLabel}>Python code</Text>
        <ScrollView
          style={m.codeScroll}
          contentContainerStyle={m.codePad}
          horizontal={false}
          showsVerticalScrollIndicator
        >
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <Text style={m.code} selectable>
              {code}
            </Text>
          </ScrollView>
        </ScrollView>

        <View style={m.footer}>
          <Text style={m.footerMeta}>Updated {fmtDate(strategy.updated_at)}</Text>
        </View>
      </SafeAreaView>
    </Modal>
  );
}

export default function StrategiesScreen() {
  const [strats, setStrats] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Strategy | null>(null);

  useEffect(() => {
    api
      .list()
      .then(setStrats)
      .catch((e) => setError(String(e.message)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <SafeAreaView style={s.safe} edges={["bottom"]}>
      <Text style={s.heading}>Strategies</Text>

      {loading && <ActivityIndicator color={C.muted} style={{ marginTop: 32 }} />}
      {!!error && <Text style={s.errorText}>{error}</Text>}

      {!loading && !error && strats.length === 0 && (
        <View style={s.emptyState}>
          <Text style={s.emptyTitle}>No strategies yet</Text>
          <Text style={s.emptyBody}>
            Create strategies in the web app, then view and run them here.
          </Text>
        </View>
      )}

      <FlatList
        data={strats}
        keyExtractor={(item) => item.id}
        contentContainerStyle={s.list}
        showsVerticalScrollIndicator={false}
        renderItem={({ item }) => (
          <Pressable
            style={({ pressed }) => [s.card, pressed && s.cardPressed]}
            onPress={() => setSelected(item)}
          >
            <View style={s.cardTop}>
              <Text style={s.cardName} numberOfLines={1}>
                {item.name}
              </Text>
              <Ionicons name="chevron-forward" size={16} color={C.muted} />
            </View>

            <View style={s.cardMeta}>
              {item.python_code ? (
                <View style={s.tag}>
                  <Text style={s.tagText}>Python</Text>
                </View>
              ) : null}
              {item.blocks.length > 0 ? (
                <View style={s.tag}>
                  <Text style={s.tagText}>{item.blocks.length} blocks</Text>
                </View>
              ) : null}
              <Text style={s.cardDate}>Updated {fmtDate(item.updated_at)}</Text>
            </View>

            {item.description ? (
              <Text style={s.cardDesc} numberOfLines={2}>
                {item.description}
              </Text>
            ) : null}
          </Pressable>
        )}
      />

      <CodeModal strategy={selected} onClose={() => setSelected(null)} />
    </SafeAreaView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.bg },
  heading: {
    fontSize: 28,
    ...FONT.serif,
    color: C.ink,
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 16,
  },
  list: { padding: 20, paddingTop: 0, paddingBottom: 40 },
  errorText: { fontSize: 14, color: C.negative, padding: 20 },

  emptyState: { flex: 1, alignItems: "center", justifyContent: "center", padding: 40 },
  emptyTitle: { fontSize: 17, fontWeight: "500", color: C.ink, marginBottom: 8 },
  emptyBody: { fontSize: 14, color: C.muted, textAlign: "center", lineHeight: 20 },

  card: {
    backgroundColor: C.surface,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: C.border,
    padding: 16,
    marginBottom: 10,
  },
  cardPressed: { opacity: 0.7 },
  cardTop: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },
  cardName: { flex: 1, fontSize: 16, fontWeight: "500", color: C.ink },
  cardMeta: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 4 },
  tag: {
    backgroundColor: C.bg,
    borderRadius: RADIUS.tag,
    borderWidth: 1,
    borderColor: C.border,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  tagText: { fontSize: 11, color: C.muted },
  cardDate: { fontSize: 11, color: C.muted },
  cardDesc: { fontSize: 13, color: C.muted, lineHeight: 18, marginTop: 4 },
});

const m = StyleSheet.create({
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
  title: {
    flex: 1,
    fontSize: 17,
    fontWeight: "600",
    color: C.ink,
    marginRight: 12,
  },
  blocksRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 20,
    paddingTop: 14,
  },
  blocksMeta: { fontSize: 13, color: C.muted },
  description: {
    fontSize: 14,
    color: C.body,
    lineHeight: 20,
    paddingHorizontal: 20,
    paddingTop: 10,
  },
  codeLabel: {
    fontSize: 11,
    fontWeight: "600",
    color: C.muted,
    letterSpacing: 0.8,
    textTransform: "uppercase",
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 10,
  },
  codeScroll: {
    flex: 1,
    backgroundColor: C.bg,
    marginHorizontal: 20,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: C.border,
  },
  codePad: { padding: 14 },
  code: {
    ...FONT.mono,
    fontSize: 13,
    color: C.body,
    lineHeight: 20,
  },
  footer: {
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderTopWidth: 1,
    borderTopColor: C.border,
  },
  footerMeta: { fontSize: 12, color: C.muted },
});
