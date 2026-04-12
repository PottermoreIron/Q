import { Ionicons } from "@expo/vector-icons";
import { Tabs } from "expo-router";
import { C } from "@/lib/theme";

type IoniconsName = React.ComponentProps<typeof Ionicons>["name"];

const TAB_ICON: Record<string, { active: IoniconsName; inactive: IoniconsName }> = {
  index:      { active: "grid",          inactive: "grid-outline" },
  strategies: { active: "code-slash",    inactive: "code-slash-outline" },
  run:        { active: "play-circle",   inactive: "play-circle-outline" },
  results:    { active: "bar-chart",     inactive: "bar-chart-outline" },
};

function tabIcon(name: string) {
  return ({ focused, color }: { focused: boolean; color: string }) => {
    const icons = TAB_ICON[name] ?? { active: "ellipse", inactive: "ellipse-outline" };
    return <Ionicons name={focused ? icons.active : icons.inactive} size={22} color={color} />;
  };
}

export default function RootLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: C.ink,
        tabBarInactiveTintColor: C.muted,
        tabBarStyle: {
          backgroundColor: C.surface,
          borderTopColor: C.border,
          borderTopWidth: 1,
        },
        tabBarLabelStyle: { fontSize: 11 },
        headerStyle: { backgroundColor: C.surface },
        headerTintColor: C.ink,
        headerShadowVisible: false,
        headerTitleStyle: { fontSize: 16, fontWeight: "500" },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ title: "Dashboard", tabBarIcon: tabIcon("index") }}
      />
      <Tabs.Screen
        name="strategies"
        options={{ title: "Strategies", tabBarIcon: tabIcon("strategies") }}
      />
      <Tabs.Screen
        name="run"
        options={{ title: "Run", tabBarIcon: tabIcon("run") }}
      />
      <Tabs.Screen
        name="results"
        options={{ title: "Results", tabBarIcon: tabIcon("results") }}
      />
    </Tabs>
  );
}
