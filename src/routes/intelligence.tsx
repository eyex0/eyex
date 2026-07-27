import { createFileRoute } from "@tanstack/react-router";
import { IntelligenceHubPage } from "@/pages/IntelligenceHub";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/intelligence")({
  head: () => ({
    meta: [
      { title: "Intelligence Hub | πX Technologies" },
      { name: "description", content: "AI-powered business decision intelligence platform" },
    ],
  }),
  component: () => (
    <ProtectedRoute>
      <IntelligenceHubPage />
    </ProtectedRoute>
  ),
});
