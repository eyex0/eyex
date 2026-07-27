import { createFileRoute } from "@tanstack/react-router";
import { TasksPage } from "@/pages/Tasks";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/tasks")({
  head: () => ({
    meta: [
      { title: "Task History | πX Technologies" },
      { name: "description", content: "Browse past agent task executions" },
    ],
  }),
  component: () => (
    <ProtectedRoute>
      <TasksPage />
    </ProtectedRoute>
  ),
});
