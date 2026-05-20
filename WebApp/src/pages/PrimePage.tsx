/**
 * PrimePage — Plans Premium
 * Ameliorations : affichage taux TON en live, USDT adresse copiable,
 * design renforce, section avantages enrichie
 */
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { TonConnectButton, useTonConnectUI, useTonWallet } from "@tonconnect/ui-react";
import {
  CheckCircle2, MessageCircle, Star, Crown,
  Zap, Shield, ChevronRight, Copy, Check, Clock
} from "lucide-react";
import { Link } from "@tanstack/react-router";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { BottomSheet } from "@/components/fs/BottomSheet";
import { Button } from "@/components/fs/Button";
import { Card } from "@/components/fs/Card";
import { Badge } from "@/components/fs/Badge";
import { PlanCard } from "@/components/shared/PlanCard";
import { fadeUp, staggerContainer } from "@/lib/animations";
import { PLANS, type Plan } from "@/lib/plans";

type Currency  = "fcfa" | "cdf" | "usd";
type PayMethod = "mobile" | "ton" | "usdt";

const TON_RECEIVER  = "UQBXWGv8ni_K5RdVt8pkBjdxAuq4hHSMWVocLs-JDYSbpuv6";
const USDT_ADDRESS  = "TXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"; // remplacer par ta vraie adresse TRC-20
const KINGCEY_TG    = "https://t.me/kingcey";

const BENEFITS = [
  "Acces illimite a tous les fichiers partages",
  "Telechargement sans publicite obligatoire",
  "Acces instantane sans attente",
  "Support prioritaire via Telegram",
  "Valide sur tous vos bots clones",
  "Renouvellement simple depuis la mini-app",
];

export function PrimePage() {
  const [currency,     setCurrency]     = useState<Currency>("fcfa");
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
  const [payMethod,    setPayMethod]    = useState<PayMethod | null>(null);
  const [tonPrice,     setTonPrice]     = useState<number | null>(null);
  const [tonConnectUI]                  = useTonConnectUI();
  const wallet                          = useTonWallet();
  const [copied,       setCopied]       = useState<"ton" | "usdt" | null>(null);

  useEffect(() => {
    fetch("https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd")
      .then((r) => r.json())
      .then((d) => setTonPrice(d?.["the-open-network"]?.usd ?? null))
      .catch(() => setTonPrice(null));
  }, []);

  const getTonAmount = (plan: Plan) => {
    if (!tonPrice || tonPrice === 0) return null;
    return (plan.priceUSD / tonPrice).toFixed(3);
  };

  const priceDisplay = (plan: Plan) => {
    if (currency === "fcfa") return `${plan.priceFCFA.toLocaleString("fr-FR")} FCFA`;
    if (currency === "cdf")  return `${plan.priceCDF.toLocaleString("fr-FR")} CDF`;
    return `$${plan.priceUSD.toFixed(2)}`;
  };

  const copyText = (text: string, key: "ton" | "usdt") => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(key);
      setTimeout(() => setCopied(null), 2000);
    }).catch(() => {});
  };

  const handleTonPay = async () => {
    if (!selectedPlan) return;
    const tonAmount = getTonAmount(selectedPlan);
    if (!tonAmount) return;
    if (!wallet) {
      await tonConnectUI.openModal();
      return;
    }
    const nanotons = BigInt(Math.round(Number(tonAmount) * 1e9)).toString();
    try {
      await tonConnectUI.sendTransaction({
        validUntil: Math.floor(Date.now() / 1000) + 300,
        messages:   [{ address: TON_RECEIVER, amount: nanotons }],
      });
    } catch (e) {
      console.error("[TON] Transaction annulee ou refusee", e);
    }
  };

  const openPlan = (plan: Plan) => {
    setSelectedPlan(plan);
    setPayMethod(null);
  };

  return (
    <PageWrapper subtitle="Plans & Tarifs">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible">

        {/* Header */}
        <motion.div variants={fadeUp} className="mb-6 text-center">
          <div className="relative inline-flex mb-4">
            <div className="absolute inset-0 rounded-full blur-2xl animate-glow-pulse"
              style={{ background: "radial-gradient(circle, rgba(255,178,0,0.4), transparent 70%)" }} />
            <div className="relative w-20 h-20 rounded-3xl flex items-center justify-center"
              style={{ background: "linear-gradient(135deg, rgba(255,178,0,0.20), rgba(255,178,0,0.06))", border: "1px solid rgba(255,178,0,0.35)" }}>
              <Crown size={36} color="#FFB200" />
            </div>
          </div>
          <h1 className="font-bold text-2xl text-[#FFFFF0] tracking-tight mb-1">Plans Premium</h1>
          <p className="text-[#FFFFF0]/55 text-sm">Acces illimite, sans interruption, sans publicite</p>
        </motion.div>

        {/* Banniere KGC */}
        <motion.div variants={fadeUp} className="mb-5">
          <Link to="/tasks">
            <div className="rounded-2xl p-4 flex items-center gap-3 transition-all active:scale-[0.98]"
              style={{ background: "rgba(255,178,0,0.07)", border: "1px solid rgba(255,178,0,0.22)" }}>
              <div className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
                style={{ background: "rgba(255,178,0,0.15)" }}>
                <Star size={22} color="#FFB200" fill="#FFB200" />
              </div>
              <div className="flex-1">
                <div className="text-sm font-bold text-[#FFB200]">Gagnez des KGC-Spheres</div>
                <div className="text-xs text-[#FFFFF0]/50 mt-0.5 leading-snug">
                  Accomplissez des taches et retirez en USDT ou Mobile Money
                </div>
              </div>
              <ChevronRight size={18} color="#FFB200" />
            </div>
          </Link>
        </motion.div>

        {/* Selecteur devise */}
        <motion.div variants={fadeUp} className="flex gap-1.5 mb-6 p-1 rounded-xl"
          style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
          {(["fcfa", "cdf", "usd"] as Currency[]).map((c) => (
            <button key={c} onClick={() => setCurrency(c)}
              className="flex-1 py-2 rounded-lg text-xs font-bold tracking-wider uppercase transition-all active:scale-95"
              style={{
                background: currency === c ? "#0088CC" : "transparent",
                color:      currency === c ? "#fff"     : "rgba(255,255,240,0.50)",
              }}>
              {c === "fcfa" ? "XOF" : c === "cdf" ? "XAF/CDF" : "USD"}
            </button>
          ))}
        </motion.div>

        {/* Plans — scroll horizontal */}
        <motion.div variants={fadeUp} className="mb-6 -mx-5 px-5">
          <div className="flex gap-3 overflow-x-auto pb-3 snap-x snap-mandatory"
            style={{ scrollbarWidth: "none", WebkitOverflowScrolling: "touch" }}>
            {PLANS.map((plan) => (
              <div key={plan.id} className="snap-start shrink-0 w-[200px]">
                <PlanCard
                  plan={plan}
                  currency={currency}
                  onSelect={() => openPlan(plan)}
                  selected={selectedPlan?.id === plan.id}
                />
              </div>
            ))}
          </div>
        </motion.div>

        {/* Avantages */}
        <motion.div variants={fadeUp} className="mb-5">
          <Card>
            <div className="flex items-center gap-2 mb-4">
              <Shield size={16} color="#0088CC" />
              <h3 className="font-bold text-sm text-[#FFFFF0] uppercase tracking-wider">
                Inclus dans tous les plans
              </h3>
            </div>
            <div className="flex flex-col gap-3">
              {BENEFITS.map((b) => (
                <div key={b} className="flex items-start gap-2.5">
                  <CheckCircle2 size={16} color="#0088CC" strokeWidth={2.5} className="shrink-0 mt-0.5" />
                  <span className="text-sm text-[#FFFFF0]/75 leading-snug">{b}</span>
                </div>
              ))}
            </div>
          </Card>
        </motion.div>

        {/* TON taux live */}
        {tonPrice && (
          <motion.div variants={fadeUp} className="mb-5 px-4 py-3 rounded-2xl flex items-center gap-3"
            style={{ background: "rgba(0,136,204,0.07)", border: "1px solid rgba(0,136,204,0.18)" }}>
            <img src="/assets/plans/ton.png" draggable="false" className="w-8 h-8 rounded-lg object-cover shrink-0" />
            <div className="flex-1 text-xs text-[#FFFFF0]/60">
              Taux TON en direct
            </div>
            <span className="text-sm font-bold text-[#0088CC]">1 TON = ${tonPrice.toFixed(2)}</span>
          </motion.div>
        )}

        {/* CTA Taches */}
        <motion.div variants={fadeUp} className="mb-24">
          <Link to="/tasks">
            <Button variant="ghost" fullWidth>
              <Star size={16} />
              Voir les taches KGC-Spheres
            </Button>
          </Link>
        </motion.div>

      </motion.div>

      {/* BottomSheet : Choix de methode */}
      <BottomSheet
        isOpen={!!selectedPlan && !payMethod}
        onClose={() => setSelectedPlan(null)}
        title="Choisir le mode de paiement">
        {selectedPlan && (
          <div>
            {/* Recap plan */}
            <div className="flex items-center gap-3 mb-5 p-3 rounded-xl"
              style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.10)" }}>
              <img src={`/assets/plans/${selectedPlan.asset}`} alt={selectedPlan.name}
                draggable="false"
                className="w-12 h-12 object-contain shrink-0"
                style={{ filter: `drop-shadow(0 4px 8px ${selectedPlan.glow})` }} />
              <div className="flex-1 min-w-0">
                <div className="font-bold text-base" style={{ color: selectedPlan.color }}>{selectedPlan.name}</div>
                <div className="text-xs text-[#FFFFF0]/50 flex items-center gap-1">
                  <Clock size={11} /> {selectedPlan.duration}
                </div>
                <div className="font-bold text-lg text-[#FFFFF0]">{priceDisplay(selectedPlan)}</div>
              </div>
              <Badge color={selectedPlan.color}>{selectedPlan.duration}</Badge>
            </div>

            <p className="text-xs text-[#FFFFF0]/40 uppercase tracking-wider mb-3 font-semibold">
              Methode de paiement
            </p>

            {/* Mobile Money */}
            <button onClick={() => setPayMethod("mobile")}
              className="w-full flex items-center gap-3 p-4 rounded-xl mb-3 text-left transition-all active:scale-[0.98]"
              style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.10)" }}>
              <div className="w-12 h-12 rounded-xl overflow-hidden shrink-0 flex items-center justify-center"
                style={{ background: "rgba(255,178,0,0.12)" }}>
                <img src="/assets/plans/money-bills.png" alt="Mobile Money"
                  draggable="false" className="w-10 h-10 object-contain" />
              </div>
              <div className="flex-1">
                <div className="font-bold text-[#FFFFF0] text-sm">Mobile Money</div>
                <div className="text-xs text-[#FFFFF0]/45">Orange · MTN · Wave · Moov · T-Money</div>
                <div className="text-xs text-[#FFB200] mt-0.5 font-semibold">Paiement manuel via Telegram</div>
              </div>
              <ChevronRight size={16} color="rgba(255,255,240,0.35)" />
            </button>

            {/* TON Connect */}
            <button onClick={() => setPayMethod("ton")}
              className="w-full flex items-center gap-3 p-4 rounded-xl mb-3 text-left transition-all active:scale-[0.98]"
              style={{ background: "rgba(0,136,204,0.08)", border: "1px solid rgba(0,136,204,0.22)" }}>
              <div className="w-12 h-12 rounded-xl overflow-hidden shrink-0">
                <img src="/assets/plans/ton.png" alt="TON"
                  draggable="false" className="w-12 h-12 object-cover rounded-xl" />
              </div>
              <div className="flex-1">
                <div className="font-bold text-[#FFFFF0] text-sm">TON Connect</div>
                <div className="text-xs text-[#FFFFF0]/45">
                  {tonPrice && selectedPlan
                    ? `≈ ${getTonAmount(selectedPlan)} TON (1 TON = $${tonPrice.toFixed(2)})`
                    : "Chargement du taux..."}
                </div>
                <div className="text-xs text-[#0088CC] mt-0.5 font-semibold">Paiement automatique via wallet</div>
              </div>
              <ChevronRight size={16} color="rgba(255,255,240,0.35)" />
            </button>

            {/* USDT */}
            <button onClick={() => setPayMethod("usdt")}
              className="w-full flex items-center gap-3 p-4 rounded-xl text-left transition-all active:scale-[0.98]"
              style={{ background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.18)" }}>
              <div className="w-12 h-12 rounded-xl overflow-hidden shrink-0 flex items-center justify-center"
                style={{ background: "rgba(34,197,94,0.10)" }}>
                <img src="/assets/plans/usdt.png" alt="USDT"
                  draggable="false" className="w-10 h-10 object-contain rounded-full" />
              </div>
              <div className="flex-1">
                <div className="font-bold text-[#FFFFF0] text-sm">USDT TRC-20</div>
                <div className="text-xs text-[#FFFFF0]/45">${selectedPlan.priceUSD.toFixed(2)} USD</div>
                <div className="text-xs text-[#22C55E] mt-0.5 font-semibold">Stablecoin · Reseau TRON</div>
              </div>
              <ChevronRight size={16} color="rgba(255,255,240,0.35)" />
            </button>
          </div>
        )}
      </BottomSheet>

      {/* BottomSheet : Mobile Money */}
      <BottomSheet
        isOpen={payMethod === "mobile"}
        onClose={() => setPayMethod(null)}
        title="Paiement Mobile Money">
        {selectedPlan && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3 p-4 rounded-2xl"
              style={{ background: "rgba(255,178,0,0.08)", border: "1px solid rgba(255,178,0,0.22)" }}>
              <img src="/assets/plans/money-wallet.png" alt=""
                draggable="false" className="w-14 h-14 object-contain shrink-0" />
              <div>
                <div className="text-xs text-[#FFFFF0]/40 mb-0.5">Montant a payer</div>
                <div className="font-bold text-2xl text-[#FFFFF0]">{priceDisplay(selectedPlan)}</div>
                <div className="text-xs text-[#FFFFF0]/55 mt-0.5">Plan {selectedPlan.name} — {selectedPlan.duration}</div>
              </div>
            </div>

            <Card>
              <div className="flex items-start gap-2.5">
                <Zap size={16} color="#FFB200" className="shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-[#FFFFF0]/80 leading-relaxed mb-2">
                    Contactez-nous sur Telegram pour payer via Mobile Money
                    (Orange Money, MTN, Wave, Moov, T-Money...).
                  </p>
                  <p className="text-sm text-[#FFFFF0]/80 leading-relaxed">
                    Votre acces Premium sera active dans les{" "}
                    <span className="text-[#FFB200] font-bold">5 minutes</span>{" "}
                    suivant la confirmation du paiement.
                  </p>
                </div>
              </div>
            </Card>

            <a href={`${KINGCEY_TG}?text=Bonjour, je souhaite souscrire au plan ${selectedPlan.name} (${priceDisplay(selectedPlan)})`}
              target="_blank" rel="noopener noreferrer">
              <Button fullWidth size="lg">
                <MessageCircle size={18} /> Contacter @kingcey
              </Button>
            </a>

            <button onClick={() => setPayMethod(null)}
              className="text-xs text-[#FFFFF0]/35 text-center py-2 active:opacity-70 transition-opacity">
              Changer de methode
            </button>
          </div>
        )}
      </BottomSheet>

      {/* BottomSheet : TON Connect */}
      <BottomSheet
        isOpen={payMethod === "ton"}
        onClose={() => setPayMethod(null)}
        title="Paiement TON Connect">
        {selectedPlan && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3 p-4 rounded-2xl"
              style={{ background: "rgba(0,136,204,0.08)", border: "1px solid rgba(0,136,204,0.25)" }}>
              <img src="/assets/plans/ton.png" alt="TON"
                draggable="false" className="w-14 h-14 object-contain rounded-xl shrink-0" />
              <div>
                <div className="text-xs text-[#FFFFF0]/40 mb-0.5">Montant</div>
                <div className="font-bold text-2xl text-[#FFFFF0]">
                  {getTonAmount(selectedPlan) ?? "..."} TON
                </div>
                <div className="text-xs text-[#FFFFF0]/55 mt-0.5">
                  ≈ ${selectedPlan.priceUSD.toFixed(2)} USD
                  {tonPrice ? ` · 1 TON = $${tonPrice.toFixed(2)}` : ""}
                </div>
              </div>
            </div>

            {/* Adresse TON copiable */}
            <div className="rounded-xl p-3 flex items-center gap-2"
              style={{ background: "rgba(0,136,204,0.06)", border: "1px solid rgba(0,136,204,0.15)" }}>
              <div className="flex-1 text-[10px] text-[#FFFFF0]/45 font-mono truncate">{TON_RECEIVER}</div>
              <button onClick={() => copyText(TON_RECEIVER, "ton")}
                className="shrink-0 p-1.5 rounded-lg transition-all active:scale-90"
                style={{ background: "rgba(0,136,204,0.15)" }}>
                {copied === "ton" ? <Check size={14} color="#22C55E" /> : <Copy size={14} color="#0088CC" />}
              </button>
            </div>

            <div className="flex justify-center py-1">
              <TonConnectButton />
            </div>

            <Card>
              <p className="text-sm text-[#FFFFF0]/70 leading-relaxed">
                {wallet
                  ? "Votre wallet est connecte. Cliquez sur Payer pour envoyer les TON automatiquement."
                  : "Connectez votre wallet TON (Tonkeeper, MyTonWallet...) pour continuer."}
              </p>
            </Card>

            <Button fullWidth size="lg" onClick={handleTonPay}>
              {wallet
                ? `Payer ${getTonAmount(selectedPlan) ?? "..."} TON`
                : "Connecter mon wallet TON"}
            </Button>

            <button onClick={() => setPayMethod(null)}
              className="text-xs text-[#FFFFF0]/35 text-center py-2 active:opacity-70 transition-opacity">
              Changer de methode
            </button>
          </div>
        )}
      </BottomSheet>

      {/* BottomSheet : USDT */}
      <BottomSheet
        isOpen={payMethod === "usdt"}
        onClose={() => setPayMethod(null)}
        title="Paiement USDT TRC-20">
        {selectedPlan && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3 p-4 rounded-2xl"
              style={{ background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.20)" }}>
              <img src="/assets/plans/usdt.png" alt="USDT"
                draggable="false" className="w-14 h-14 object-contain rounded-full shrink-0" />
              <div>
                <div className="text-xs text-[#FFFFF0]/40 mb-0.5">Montant</div>
                <div className="font-bold text-2xl text-[#FFFFF0]">${selectedPlan.priceUSD.toFixed(2)}</div>
                <div className="text-xs text-[#22C55E] mt-0.5 font-semibold">Reseau TRC-20 uniquement</div>
              </div>
            </div>

            {/* Adresse USDT copiable */}
            <div>
              <p className="text-xs text-[#FFFFF0]/40 mb-2 uppercase tracking-wider font-semibold">
                Adresse de reception USDT TRC-20
              </p>
              <div className="rounded-xl p-3 flex items-center gap-2"
                style={{ background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.18)" }}>
                <div className="flex-1 text-[10px] text-[#FFFFF0]/55 font-mono break-all">{USDT_ADDRESS}</div>
                <button onClick={() => copyText(USDT_ADDRESS, "usdt")}
                  className="shrink-0 p-1.5 rounded-lg transition-all active:scale-90"
                  style={{ background: "rgba(34,197,94,0.15)" }}>
                  {copied === "usdt" ? <Check size={14} color="#22C55E" /> : <Copy size={14} color="#22C55E" />}
                </button>
              </div>
            </div>

            <Card>
              <p className="text-sm text-[#FFFFF0]/80 leading-relaxed">
                Envoyez{" "}
                <span className="text-[#22C55E] font-bold">${selectedPlan.priceUSD.toFixed(2)} USDT</span>{" "}
                sur le reseau TRC-20 a l'adresse ci-dessus, puis contactez-nous sur Telegram avec votre preuve de transfert.
                Votre acces sera active apres verification.
              </p>
            </Card>

            <a href={`${KINGCEY_TG}?text=Bonjour, j'ai effectue un paiement USDT de $${selectedPlan.priceUSD.toFixed(2)} pour le plan ${selectedPlan.name}`}
              target="_blank" rel="noopener noreferrer">
              <Button fullWidth size="lg">
                <MessageCircle size={18} /> Contacter @kingcey
              </Button>
            </a>

            <button onClick={() => setPayMethod(null)}
              className="text-xs text-[#FFFFF0]/35 text-center py-2 active:opacity-70 transition-opacity">
              Changer de methode
            </button>
          </div>
        )}
      </BottomSheet>
    </PageWrapper>
  );
}
