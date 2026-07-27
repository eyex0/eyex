import { createFileRoute } from "@tanstack/react-router";
import { SettingsPage } from "@/pages/Settings";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings | πX Technologies" },
      {
        name: "description",
        content: "Manage your account settings, preferences, and security configuration.",
      },
      { property: "og:title", content: "Settings | πX Technologies" },
      {
        property: "og:description",
        content: "Manage your account settings, preferences, and security configuration.",
      },
      { property: "og:type", content: "website" },
    ],
  }),
  component: () => (
    <ProtectedRoute>
      <SettingsPage />
    </ProtectedRoute>
  ),
});
