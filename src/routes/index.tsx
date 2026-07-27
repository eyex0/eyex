import { createFileRoute } from "@tanstack/react-router";
import { HomePage } from "@/pages/Home";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "πX Technologies — Intelligence, Architected" },
      {
        name: "description",
        content:
          "Foundational intelligence infrastructure for the next generation of global enterprise. Secured by design, engineered for scale.",
      },
      { property: "og:title", content: "πX Technologies — Intelligence, Architected" },
      {
        property: "og:description",
        content:
          "Foundational intelligence infrastructure for the next generation of global enterprise. Secured by design, engineered for scale.",
      },
      { property: "og:type", content: "website" },
    ],
  }),
  component: HomePage,
});
