import { motion } from "framer-motion";
import { CheckCircle2 } from "lucide-react";
import { Button } from "@/components/fs/Button";
import { Badge } from "@/components/fs/Badge";
import { formatPrice, type Plan } from "@/lib/plans";

interface Props {
  plan: Plan;
  currency: "fcfa" | "cdf" | "usd";
  onSelect: (p: Plan) => void;
  selected?: boolean;
}

export function PlanCard({ plan, currency, onSelect, selected }: Props) {
  const others = (["fcfa", "cdf", "usd"] as const).filter((c) => c !== currency);
  return (
    <motion.div
      whileHover={{ y: -4 }}
      whileTap={{ scale: 0.97 }}
      className="glass p-5 flex flex-col items-center text-center relative overflow-hidden cursor-pointer transition-all"
      style={{
        boxShadow: selected
          ? `0 16px 40px -16px ${plan.glow}, 0 0 0 2px ${plan.color}60`
          : `0 16px 40px -16px ${plan.glow}`,
        borderColor: selected ? plan.color : `${plan.color}30`,
        borderWidth: selected ? "2px" : "1px",
      }}
      onClick={() => onSelect(plan)}
    >
      <div
        className="absolute inset-0 opacity-30 pointer-events-none"
        style={{ background: `radial-gradient(circle at 50% 0%, ${plan.glow}, transparent 60%)` }}
      />

      {plan.popular && !selected && (
        <div className="absolute top-3 right-3">
          <Badge color="#FFB200">Populaire</Badge>
        </div>
      )}

      {selected && (
        <div className="absolute top-3 right-3">
          <CheckCircle2 size={18} color={plan.color} />
        </div>
      )}

      <div
        className="w-20 h-20 rounded-2xl flex items-center justify-center mb-3 relative z-10"
        style={{ background: `radial-gradient(circle at 50% 50%, ${plan.glow}, transparent 70%)` }}
      >
        <img
          src={`/assets/plans/${plan.asset}`}
          alt={plan.name}
          className="w-16 h-16 object-contain"
          style={{ filter: `drop-shadow(0 8px 16px ${plan.glow})` }}
          onError={(e) => {
            (e.currentTarget as HTMLImageElement).style.display = "none";
          }}
        />
      </div>

      <h3 className="font-display text-2xl mb-1 relative z-10" style={{ color: plan.color }}>
        {plan.name}
      </h3>
      <Badge color={plan.color} className="mb-3">{plan.duration}</Badge>

      <div className="font-display text-2xl text-[#FFFFF0] mb-1 relative z-10">
        {formatPrice(plan, currency)}
      </div>
      <div className="text-xs text-[#FFFFF0]/40 mb-5 space-x-2 relative z-10">
        {others.map((c) => (
          <span key={c}>{formatPrice(plan, c)}</span>
        ))}
      </div>

      <Button
        onClick={() => onSelect(plan)}
        fullWidth
        className="relative z-10"
        style={{
          background: selected ? plan.color : `${plan.color}22`,
          color: selected ? "#0A0A0A" : plan.color,
          border: `1px solid ${plan.color}60`,
        }}
      >
        {selected ? <CheckCircle2 size={15} /> : null}
        {selected ? "Sélectionné" : "Choisir ce plan"}
      </Button>
    </motion.div>
  );
}
