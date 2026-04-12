import { Tabs } from "expo-router";

export default function RootLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: "#191919",
        tabBarInactiveTintColor: "#9B9A97",
        tabBarStyle: {
          backgroundColor: "#FFFFFF",
          borderTopColor: "#E9E9E7",
          borderTopWidth: 1,
        },
        headerStyle: { backgroundColor: "#FFFFFF" },
        headerTintColor: "#191919",
        headerShadowVisible: false,
      }}
    >
      <Tabs.Screen name="index" options={{ title: "Dashboard" }} />
      <Tabs.Screen name="strategies" options={{ title: "Strategies" }} />
      <Tabs.Screen name="run" options={{ title: "Run" }} />
      <Tabs.Screen name="results" options={{ title: "Results" }} />
    </Tabs>
  );
}
