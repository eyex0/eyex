import { createFileRoute } from "@tanstack/react-router";
import { InventoryPage } from "@/pages/Inventory";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/inventory")({
  head: () => ({
    meta: [
      { title: "Inventory | πX Technologies" },
      {
        name: "description",
        content: "Inventory and warehouse management with real-time stock tracking.",
      },
      { property: "og:title", content: "Inventory | πX Technologies" },
      {
        property: "og:description",
        content: "Inventory and warehouse management with real-time stock tracking.",
      },
      { property: "og:type", content: "website" },
    ],
  }),
  component: () => (
    <ProtectedRoute>
      <InventoryPage />
    </ProtectedRoute>
  ),
});
