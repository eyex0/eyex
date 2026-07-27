import { createFileRoute } from "@tanstack/react-router";
import { CrmPage } from "@/pages/Crm";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/crm")({
  head: () => ({
    meta: [
      { title: "CRM | πX Technologies" },
      {
        name: "description",
        content: "Customer relationship management with AI-powered insights and pipeline tracking.",
      },
      { property: "og:title", content: "CRM | πX Technologies" },
      {
        property: "og:description",
        content: "Customer relationship management with AI-powered insights and pipeline tracking.",
      },
      { property: "og:type", content: "website" },
    ],
  }),
  component: () => (
    <ProtectedRoute>
      <CrmPage />
    </ProtectedRoute>
  ),
});
