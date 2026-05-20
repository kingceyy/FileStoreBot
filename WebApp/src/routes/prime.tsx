import { createFileRoute } from "@tanstack/react-router";
import { PrimePage } from "@/pages/PrimePage";

export const Route = createFileRoute("/prime")({
  component: PrimePage,
  head: () => ({
    meta: [
      { title: "FileStore — Plans Premium" },
      { name: "description", content: "6 plans Premium, paiement Mobile Money, TON Connect ou USDT." },
    ],
  }),
});
