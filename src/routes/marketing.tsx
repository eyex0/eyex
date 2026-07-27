import { createFileRoute } from "@tanstack/react-router";
import { MarketingPage } from "@/pages/Marketing";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/marketing")({
  head: () => ({
    meta: [
      { title: "Marketing | πX Technologies" },
      {
        name: "description",
        content: "Marketing campaign management with AI-driven audience targeting.",
      },
      { property: "og:title", content: "Marketing | πX Technologies" },
      {
        property: "og:description",
        content: "Marketing campaign management with AI-driven audience targeting.",
      },
      { property: "og:type", content: "website" },
    ],
  }),
  component: () => (
    <ProtectedRoute>
      <MarketingPage />
    </ProtectedRoute>
  ),
});
