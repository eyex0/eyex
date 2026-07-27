import { createFileRoute } from "@tanstack/react-router";
import { IntegrationsPage } from "@/pages/Integrations";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/integrations")({
  head: () => ({
    meta: [
      { title: "Integrations | πX Technologies" },
      {
        name: "description",
        content: "Connect and manage third-party integrations for your business platform.",
      },
      { property: "og:title", content: "Integrations | πX Technologies" },
      {
        property: "og:description",
        content: "Connect and manage third-party integrations for your business platform.",
      },
      { property: "og:type", content: "website" },
    ],
  }),
  component: () => (
    <ProtectedRoute>
      <IntegrationsPage />
    </ProtectedRoute>
  ),
});
