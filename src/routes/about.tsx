import { createFileRoute } from "@tanstack/react-router";
import { AboutPage } from "@/pages/About";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [
      { title: "About πX Technologies — Origin" },
      {
        name: "description",
        content: "The people, principles and origin story behind πX Technologies.",
      },
      { property: "og:title", content: "About πX Technologies — Origin" },
      {
        property: "og:description",
        content: "The people, principles and origin story behind πX Technologies.",
      },
      { property: "og:type", content: "website" },
    ],
  }),
  component: AboutPage,
});
