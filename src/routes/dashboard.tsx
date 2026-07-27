import { createFileRoute } from "@tanstack/react-router";
import { DashboardPage } from "@/pages/Dashboard";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — πX Technologies" },
      {
        name: "description",
        content:
          "Real-time business intelligence dashboard. Monitor revenue, customers, growth, and AI-powered insights.",
      },
      { property: "og:title", content: "Dashboard — πX Technologies" },
      { property: "og:description", content: "Real-time business intelligence dashboard." },
      { property: "og:type", content: "website" },
    ],
  }),
  component: () => (
    <ProtectedRoute>
      <DashboardPage />
    </ProtectedRoute>
  ),
});
