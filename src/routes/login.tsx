import { createFileRoute } from "@tanstack/react-router";
import LoginPage from "@/pages/Login";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign In — πX Technologies" },
      { name: "description", content: "Sign in to your πX Technologies account." },
    ],
  }),
  component: LoginPage,
});
