import { createFileRoute } from "@tanstack/react-router";
import SignupPage from "@/pages/Signup";

export const Route = createFileRoute("/signup")({
  head: () => ({
    meta: [
      { title: "Sign Up — πX Technologies" },
      { name: "description", content: "Create your πX Technologies account." },
    ],
  }),
  component: SignupPage,
});
