import { createFileRoute } from "@tanstack/react-router";
import { BillingPage } from "@/pages/Billing";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/billing")({
  head: () => ({
    meta: [
      { title: "Billing | πX Technologies" },
      { name: "description", content: "Manage subscription and invoices" },
    ],
  }),
  component: () => (
    <ProtectedRoute>
      <BillingPage />
    </ProtectedRoute>
  ),
});
