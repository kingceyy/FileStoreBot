import { createFileRoute } from "@tanstack/react-router";
import { MasterPage } from "@/pages/MasterPage";

export const Route = createFileRoute("/master")({
  component: MasterPage,
  head: () => ({ meta: [{ title: "FileStore — Espace Maître" }] }),
});
