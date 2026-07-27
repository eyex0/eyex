import { createFileRoute } from "@tanstack/react-router";
import { FinancePage } from "@/pages/Finance";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/finance")({
  head: () => ({
    meta: [
      { title: "Finance | πX Technologies" },
      {
        name: "description",
        content: "Financial tracking, reporting, and AI-powered fiscal insights.",
      },
      { property: "og:title", content: "Finance | πX Technologies" },
      {
        property: "og:description",
        content: "Financial tracking, reporting, and AI-powered fiscal insights.",
      },
      { property: "og:type", content: "website" },
    ],
  }),
  component: () => (
    <ProtectedRoute>
      <FinancePage />
    </ProtectedRoute>
  ),
});
