import { createFileRoute } from "@tanstack/react-router";
import { ProjectsPage } from "@/pages/Projects";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/projects")({
  head: () => ({
    meta: [
      { title: "Projects | πX Technologies" },
      {
        name: "description",
        content: "Project and task management with intelligent scheduling and resource allocation.",
      },
      { property: "og:title", content: "Projects | πX Technologies" },
      {
        property: "og:description",
        content: "Project and task management with intelligent scheduling and resource allocation.",
      },
      { property: "og:type", content: "website" },
    ],
  }),
  component: () => (
    <ProtectedRoute>
      <ProjectsPage />
    </ProtectedRoute>
  ),
});
