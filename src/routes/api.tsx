import { createFileRoute } from "@tanstack/react-router";
import { ApiPage } from "@/pages/Api";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/api")({
  head: () => ({
    meta: [
      { title: "API Platform — πX Technologies" },
      {
        name: "description",
        content:
          "Programmatic access to QORX. Typed endpoints, deterministic outputs, enterprise-grade rate limits.",
      },
      { property: "og:title", content: "API Platform — πX Technologies" },
      {
        property: "og:description",
        content:
          "Programmatic access to QORX. Typed endpoints, deterministic outputs, enterprise-grade rate limits.",
      },
      { property: "og:type", content: "website" },
    ],
  }),
  component: () => (
    <ProtectedRoute>
      <ApiPage />
    </ProtectedRoute>
  ),
});
