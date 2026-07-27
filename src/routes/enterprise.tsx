import { createFileRoute } from "@tanstack/react-router";
import { EnterpriseDashboardPage } from "@/pages/EnterpriseDashboard";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/enterprise")({
  head: () => ({
    meta: [
      { title: "Enterprise Console | πX Technologies" },
      { name: "description", content: "Multi-company AI intelligence platform console" },
    ],
  }),
  component: () => (
    <ProtectedRoute>
      <EnterpriseDashboardPage />
    </ProtectedRoute>
  ),
});
