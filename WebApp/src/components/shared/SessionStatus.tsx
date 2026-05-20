import { Card } from "@/components/fs/Card";
import { Badge } from "@/components/fs/Badge";
import { Clock } from "lucide-react";
import { useEffect, useState } from "react";

interface Props {
  expiresAt: number; // ms epoch
  type: "free" | "premium";
}

export function SessionStatus({ expiresAt, type }: Props) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const remaining = Math.max(0, expiresAt - now);
  const totalSec = Math.floor(remaining / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  const isPrem = type === "premium";
  const color = isPrem ? "#FFB200" : "#22C55E";

  return (
    <Card glowColor={`${color}30`} style={{ borderColor: `${color}40` }}>
      <div className="flex items-center justify-between mb-3">
        <Badge color={color}>{isPrem ? "Premium" : "Gratuit"}</Badge>
        <div className="flex items-center gap-1.5 text-[#FFFFF0]/70 text-sm">
          <Clock size={14} /> {m}:{s.toString().padStart(2, "0")}
        </div>
      </div>
      <div className="font-display text-xl text-[#FFFFF0]">Accès actif</div>
      <div className="text-sm text-[#FFFFF0]/55 mt-1">Profitez de vos fichiers en illimité</div>
    </Card>
  );
}
