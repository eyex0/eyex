import { createFileRoute } from "@tanstack/react-router";
import { ReportsPage } from "@/pages/Reports";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/reports")({
  head: () => ({
    meta: [
      { title: "Reports | πX Technologies" },
      {
        name: "description",
        content: "Generate and view comprehensive business reports with AI-powered insights.",
      },
      { property: "og:title", content: "Reports | πX Technologies" },
      {
        property: "og:description",
        content: "Generate and view comprehensive business reports with AI-powered insights.",
      },
      { property: "og:type", content: "website" },
    ],
  }),
  component: () => (
    <ProtectedRoute>
      <ReportsPage />
    </ProtectedRoute>
  ),
});
