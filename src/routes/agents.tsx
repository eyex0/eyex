import { createFileRoute } from "@tanstack/react-router";
import { AgentsPage } from "@/pages/Agents";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/agents")({
  head: () => ({
    meta: [
      { title: "Agent Management | πX Technologies" },
      { name: "description", content: "Configure and monitor AI agents" },
    ],
  }),
  component: () => (
    <ProtectedRoute>
      <AgentsPage />
    </ProtectedRoute>
  ),
});
