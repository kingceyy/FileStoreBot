import { createFileRoute } from "@tanstack/react-router";
import { IndexPage } from "@/pages/IndexPage";

export const Route = createFileRoute("/")({
  component: IndexPage,
  head: () => ({
    meta: [
      { title: "FileStore — Accès Sécurisé" },
      { name: "description", content: "Débloquez l'accès aux fichiers en regardant 2 publicités, ou passez en Premium." },
    ],
  }),
});
