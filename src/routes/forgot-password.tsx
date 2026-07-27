import { createFileRoute } from "@tanstack/react-router";
import ForgotPasswordPage from "@/pages/ForgotPassword";

export const Route = createFileRoute("/forgot-password")({
  head: () => ({
    meta: [
      { title: "Forgot Password — πX Technologies" },
      { name: "description", content: "Reset your πX Technologies password." },
    ],
  }),
  component: ForgotPasswordPage,
});
