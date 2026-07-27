import { createFileRoute } from "@tanstack/react-router";
import { ObservabilityPage } from "@/pages/Observability";
import { ProtectedRoute } from "@/components/auth/protected-route";

export const Route = createFileRoute("/observability")({
    component: () => (
        <ProtectedRoute>
            <ObservabilityPage />
        </ProtectedRoute>
    ),
});
