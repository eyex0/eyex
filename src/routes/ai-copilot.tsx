import { createFileRoute } from "@tanstack/react-router";
import { AiCopilotPage } from "@/pages/AiCopilot";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/ai-copilot")({
  head: () => ({
    meta: [
      { title: "AI Copilot | πX Technologies" },
      {
        name: "description",
        content:
          "Command your AI business copilot for intelligent automation and decision support.",
      },
      { property: "og:title", content: "AI Copilot | πX Technologies" },
      {
        property: "og:description",
        content:
          "Command your AI business copilot for intelligent automation and decision support.",
      },
      { property: "og:type", content: "website" },
    ],
  }),
  component: () => (
    <ProtectedRoute>
      <AiCopilotPage />
    </ProtectedRoute>
  ),
});
