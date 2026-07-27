import { createFileRoute } from "@tanstack/react-router";
import { SalesPage } from "@/pages/Sales";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/sales")({
  head: () => ({
    meta: [
      { title: "Sales | πX Technologies" },
      {
        name: "description",
        content: "Sales pipeline and order management with predictive analytics.",
      },
      { property: "og:title", content: "Sales | πX Technologies" },
      {
        property: "og:description",
        content: "Sales pipeline and order management with predictive analytics.",
      },
      { property: "og:type", content: "website" },
    ],
  }),
  component: () => (
    <ProtectedRoute>
      <SalesPage />
    </ProtectedRoute>
  ),
});
