import { createFileRoute } from "@tanstack/react-router";
import { ContactPage } from "@/pages/Contact";

export const Route = createFileRoute("/contact")({
  head: () => ({
    meta: [
      { title: "Contact πX Technologies" },
      {
        name: "description",
        content:
          "Get in touch with πX Technologies. Reach out for partnerships, support, or general inquiries.",
      },
      { property: "og:title", content: "Contact πX Technologies" },
      {
        property: "og:description",
        content:
          "Get in touch with πX Technologies. Reach out for partnerships, support, or general inquiries.",
      },
    ],
  }),
  component: ContactPage,
});
