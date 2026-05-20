/**
 * ProfilePage — Profil utilisateur (JessiKaPay only).
 * - Photo de profil Telegram via initData
 * - Logo KGC-Sphère en PNG
 * - Sections réordonnables (Identité, Stats, Solde, Paiements)
 * - Retrait des gains uniquement via JessiKaPay (compte JP-XXXXXX)
 * - Aucun emoji, icônes Lucide (SVG) + assets PNG
 * - Aucune modification des appels API existants
 */
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft, Wallet, Clock, CheckCircle2, AlertCircle, Loader2,
  Copy, ChevronRight, Shield, Trash2, Plus, Crown, TrendingUp,
  ListChecks, History, BadgeCheck, Award, Settings2, ArrowUp, ArrowDown,
  Check, ExternalLink, Sparkles,
} from "lucide-react";
import { Link } from "@tanstack/react-router";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Button } from "@/components/fs/Button";
import { BottomSheet } from "@/components/fs/BottomSheet";
import { ToastProvider, useToast } from "@/components/fs/Toast";
import { ConfirmDialog } from "@/components/fs/ConfirmDialog";
import { fadeUp, staggerContainer } from "@/lib/animations";
import { getUserProfile, requestUserWithdrawal } from "@/lib/api";
import {
  getTelegramUser, expandWebApp, hapticSuccess, hapticError, hapticImpact,
} from "@/lib/telegram";
import {
  loadPaymentMethods, savePaymentMethod, deletePaymentMethod,
  isValidJpNumber, normalizeJpNumber,
  type SavedPaymentMethod,
} from "@/lib/paymentMethods";

const KGC_TO_USDT  = 0.001;
const USDT_TO_XOF  = 500;
const MIN_WITHDRAW = 3; // USDT

const KGC_SPHERE_SRC = "/assets/kgc-sphere.png";
const USDT_LOGO_SRC  = "/assets/plans/usdt.png";
const JKP_LOGO_SRC   = "/assets/plans/wallet-color.png";
const JKP_URL        = "https://jkpay.vercel.app";
const JKP_BOT        = "https://t.me/JessiKaPayBot";

interface Withdrawal {
  id: string;
  amount_usdt: number;
  method: string;
  address: string;
  status: "pending" | "approved" | "rejected";
  requested_at: string;
}

interface Profile {
  user_id: number;
  first_name: string;
  username?: string;
  balance_kgc: number;
  total_earned_kgc: number;
  tasks_completed: number;
  withdrawals: Withdrawal[];
}

// ─── Rangs ─────────────────────────────────────────────────────────────────
interface Rank {
  key: string; label: string; color: string; icon: string; min: number;
}
const RANKS: Rank[] = [
  { key: "initie",     label: "Initié",     color: "#9CA3AF", icon: "/assets/plans/bronze.png",     min: 0 },
  { key: "bronze",     label: "Bronze",     color: "#CD7F32", icon: "/assets/plans/bronze.png",     min: 1_000 },
  { key: "argent",     label: "Argent",     color: "#C0C0C0", icon: "/assets/plans/argent.png",     min: 10_000 },
  { key: "or",         label: "Or",         color: "#FFB200", icon: "/assets/plans/or.png",         min: 50_000 },
  { key: "platine",    label: "Platine",    color: "#E5E4E2", icon: "/assets/plans/platine.png",    min: 200_000 },
  { key: "diamant",    label: "Diamant",    color: "#5BC0EB", icon: "/assets/plans/diamant.png",    min: 1_000_000 },
  { key: "adamantide", label: "Adamantide", color: "#A78BFA", icon: "/assets/plans/adamantide.png", min: 5_000_000 },
];
function computeRank(totalKgc: number) {
  let current = RANKS[0];
  let next: Rank | null = null;
  for (let i = 0; i < RANKS.length; i++) {
    if (totalKgc >= RANKS[i].min) current = RANKS[i];
    if (totalKgc < RANKS[i].min) { next = RANKS[i]; break; }
  }
  const progress =
    next ? Math.min(1, (totalKgc - current.min) / (next.min - current.min)) : 1;
  return { current, next, progress };
}

// ─── Avatar : photo Telegram + anneau animé + halo ─────────────────────────
function ProfileAvatar({
  photoUrl, name, size = 64,
}: { photoUrl?: string; name: string; size?: number }) {
  const [errored, setErrored] = useState(false);
  const initials = useMemo(() => {
    const parts = (name || "U").trim().split(/\s+/).slice(0, 2);
    return parts.map((p) => p[0]?.toUpperCase() ?? "").join("") || "U";
  }, [name]);
  const ringSize = size + 12;

  return (
    <div className="relative shrink-0" style={{ width: ringSize, height: ringSize }}>
      <motion.div
        aria-hidden
        className="absolute inset-0 rounded-full"
        style={{
          background:
            "radial-gradient(circle, rgba(0,136,204,0.4), rgba(255,178,0,0.10) 55%, transparent 75%)",
          filter: "blur(10px)",
        }}
        animate={{ opacity: [0.5, 0.95, 0.5], scale: [0.95, 1.06, 0.95] }}
        transition={{ duration: 2.8, ease: "easeInOut", repeat: Infinity }}
      />
      <motion.div
        aria-hidden
        className="absolute inset-0 rounded-full"
        style={{
          padding: 2,
          background: "conic-gradient(from 0deg, #0088CC, #FFB200, #A78BFA, #0088CC)",
          WebkitMask: "radial-gradient(circle, transparent calc(50% - 3px), #000 calc(50% - 2px))",
          mask:       "radial-gradient(circle, transparent calc(50% - 3px), #000 calc(50% - 2px))",
        }}
        animate={{ rotate: 360 }}
        transition={{ duration: 14, ease: "linear", repeat: Infinity }}
      />
      <motion.div
        whileTap={{ scale: 0.94 }}
        className="absolute rounded-full overflow-hidden"
        style={{
          width: size, height: size,
          top: (ringSize - size) / 2, left: (ringSize - size) / 2,
          background: "linear-gradient(135deg, rgba(0,136,204,0.30), rgba(255,178,0,0.18))",
          border: "1px solid rgba(255,255,255,0.14)",
          boxShadow:
            "0 6px 22px -8px rgba(0,136,204,0.55), inset 0 0 0 1px rgba(255,255,240,0.06)",
        }}
      >
        {photoUrl && !errored ? (
          <img
            src={photoUrl} alt="" width={size} height={size} loading="lazy"
            onError={() => setErrored(true)}
            className="w-full h-full object-cover"
            style={{ pointerEvents: "none" }}
          />
        ) : (
          <div
            className="w-full h-full flex items-center justify-center font-display"
            style={{ color: "#FFFFF0", fontSize: size * 0.40, fontWeight: 900 }}
          >
            {initials}
          </div>
        )}
        <div
          aria-hidden
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              "linear-gradient(160deg, rgba(255,255,255,0.20), transparent 45%)",
          }}
        />
      </motion.div>
    </div>
  );
}

// ─── Page ───────────────────────────────────────────────────────────────────
export function ProfilePage() {
  return <ToastProvider><ProfileInner /></ToastProvider>;
}

type SectionKey = "identity" | "stats" | "balance" | "payments";
const DEFAULT_ORDER: SectionKey[] = ["identity", "stats", "balance", "payments"];
const SECTION_LABELS: Record<SectionKey, string> = {
  identity: "Identité & Rang",
  stats:    "Statistiques",
  balance:  "Solde KGC",
  payments: "Comptes JessiKaPay",
};

function ProfileInner() {
  const [profile, setProfile]       = useState<Profile | null>(null);
  const [loading, setLoading]       = useState(true);

  // Sheet retrait
  const [sheetOpen, setSheetOpen]   = useState(false);
  const [sheetStep, setSheetStep]   = useState<"saved" | "jkpay_info" | "form">("saved");
  const [address, setAddress]       = useState("");
  const [amount, setAmount]         = useState("");
  const [label, setLabel]           = useState("");
  const [saveMethod, setSaveMethod] = useState(true);
  const [jpAccepted, setJpAccepted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Ajout moyen de paiement
  const [methods, setMethods]       = useState<SavedPaymentMethod[]>([]);
  const [pmSheetOpen, setPmSheetOpen] = useState(false);
  const [pmLabel, setPmLabel]       = useState("");
  const [pmAddress, setPmAddress]   = useState("");

  // Confirmations
  const [confirmDelete, setConfirmDelete] = useState<SavedPaymentMethod | null>(null);
  const [confirmSave, setConfirmSave] = useState(false);

  // Réordonnement
  const [order, setOrder] = useState<SectionKey[]>(DEFAULT_ORDER);
  const [reorderMode, setReorderMode] = useState(false);

  const { toast } = useToast();
  const user   = getTelegramUser();
  const userId = user?.id ?? 0;
  const photoUrl = user?.photo_url;

  useEffect(() => {
    expandWebApp();
    if (!userId) { setLoading(false); return; }
    getUserProfile(userId).then((res) => {
      setProfile(res?.profile ?? null);
      setLoading(false);
    });
    setMethods(loadPaymentMethods(userId));
    try {
      const raw = localStorage.getItem(`kgc:profile_order:${userId}`);
      if (raw) {
        const parsed = JSON.parse(raw) as SectionKey[];
        const valid = parsed.filter((k) => DEFAULT_ORDER.includes(k));
        const missing = DEFAULT_ORDER.filter((k) => !valid.includes(k));
        setOrder([...valid, ...missing]);
      }
    } catch { /* ignore */ }
  }, [userId]);

  const persistOrder = (next: SectionKey[]) => {
    setOrder(next);
    try { localStorage.setItem(`kgc:profile_order:${userId}`, JSON.stringify(next)); } catch { /* ignore */ }
  };
  const moveSection = (key: SectionKey, dir: -1 | 1) => {
    const idx = order.indexOf(key);
    const target = idx + dir;
    if (idx < 0 || target < 0 || target >= order.length) return;
    const next = [...order];
    [next[idx], next[target]] = [next[target], next[idx]];
    hapticImpact("light");
    persistOrder(next);
  };
  const resetOrder = () => { persistOrder(DEFAULT_ORDER); hapticImpact("light"); };

  const balanceKgc  = profile?.balance_kgc ?? 0;
  const totalKgc    = profile?.total_earned_kgc ?? 0;
  const balanceUsdt = balanceKgc * KGC_TO_USDT;
  const balanceXof  = balanceUsdt * USDT_TO_XOF;
  const canWithdraw = balanceUsdt >= MIN_WITHDRAW;
  const rank = computeRank(totalKgc);
  const displayName =
    profile?.first_name ?? user?.first_name ?? user?.username ?? "Utilisateur";

  const openWithdraw = () => {
    if (!canWithdraw) {
      toast(
        `Minimum de retrait : ${MIN_WITHDRAW} USDT. Solde : ${balanceUsdt.toFixed(3)} USDT.`,
        "error",
      );
      return;
    }
    hapticImpact("light");
    setAddress("");
    setLabel("");
    setSaveMethod(true);
    setAmount(balanceUsdt.toFixed(3));
    setJpAccepted(false);
    setSheetStep(methods.length > 0 ? "saved" : "jkpay_info");
    setSheetOpen(true);
  };

  const useSavedForWithdraw = (m: SavedPaymentMethod) => {
    setAddress(m.address);
    setLabel(m.label);
    setSaveMethod(false);
    setSheetStep("form");
  };

  const submitWithdrawal = async () => {
    const addr = normalizeJpNumber(address);
    if (!addr || !userId) return;
    if (!isValidJpNumber(addr)) {
      toast("Numéro JessiKaPay invalide. Format attendu : JP-XXXXXX.", "error");
      return;
    }
    const amountNum = parseFloat(amount);
    if (isNaN(amountNum) || amountNum < MIN_WITHDRAW) {
      toast(`Montant minimum : ${MIN_WITHDRAW} USDT`, "error"); return;
    }
    if (amountNum > balanceUsdt) {
      toast("Solde insuffisant.", "error"); return;
    }

    setSubmitting(true);
    // API inchangée : on conserve "mobile_money" comme method côté backend
    const res = await requestUserWithdrawal(userId, amountNum, "mobile_money", addr);
    setSubmitting(false);

    if (res?.success) {
      hapticSuccess();
      if (saveMethod) {
        const exists = methods.some((m) => m.address === addr);
        if (!exists) {
          const entry = savePaymentMethod(userId, {
            type: "jkpay",
            label: label.trim() || "Mon compte JessiKaPay",
            address: addr,
          });
          setMethods((prev) => [entry, ...prev]);
        }
      }
      toast("Demande envoyée. Traitement le prochain mardi ou samedi.", "success");
      setSheetOpen(false);
      getUserProfile(userId).then((r) => setProfile(r?.profile ?? null));
    } else {
      hapticError();
      toast(res?.error || "Erreur lors de la demande. Réessayez.", "error");
    }
  };

  const requestAddPaymentMethod = () => {
    const addr = normalizeJpNumber(pmAddress);
    if (!userId) return;
    if (!isValidJpNumber(addr)) {
      toast("Numéro JessiKaPay invalide. Format : JP-XXXXXX.", "error"); return;
    }
    if (methods.some((m) => m.address === addr)) {
      toast("Ce compte JessiKaPay est déjà enregistré.", "error"); return;
    }
    setConfirmSave(true);
  };

  const confirmAddPaymentMethod = () => {
    const addr = normalizeJpNumber(pmAddress);
    if (!isValidJpNumber(addr) || !userId) return;
    const entry = savePaymentMethod(userId, {
      type: "jkpay",
      label: pmLabel.trim() || "Mon compte JessiKaPay",
      address: addr,
    });
    setMethods((prev) => [entry, ...prev]);
    setPmLabel(""); setPmAddress("");
    setConfirmSave(false);
    setPmSheetOpen(false);
    hapticSuccess();
    toast("Compte JessiKaPay enregistré.", "success");
  };

  const requestRemoveMethod = (m: SavedPaymentMethod) => setConfirmDelete(m);
  const confirmRemoveMethod = () => {
    if (!userId || !confirmDelete) return;
    setMethods(deletePaymentMethod(userId, confirmDelete.id));
    setConfirmDelete(null);
    hapticImpact("light");
    toast("Compte supprimé.", "success");
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
      .then(() => toast("Copié !", "success"))
      .catch(() => { /* ignore */ });
  };

  if (loading) return (
    <PageWrapper subtitle="Mon Profil">
      <div className="flex justify-center pt-20">
        <Loader2 className="animate-spin" size={28} color="#0088CC" />
      </div>
    </PageWrapper>
  );

  return (
    <PageWrapper subtitle="Mon Profil">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible">

        <motion.div variants={fadeUp} className="mb-5">
          <Link to="/">
            <button className="flex items-center gap-2 text-sm font-bold text-[#FFFFF0]/55 hover:text-[#FFFFF0] transition-colors">
              <ArrowLeft size={16} />
              Retour
            </button>
          </Link>
        </motion.div>

        {/* Toolbar Personnalisation */}
        <motion.div variants={fadeUp} className="mb-4 flex items-center justify-between">
          <h1 className="font-display text-2xl text-[#FFFFF0]" style={{ fontWeight: 900 }}>
            Mon Profil
          </h1>
          <div className="flex items-center gap-1.5">
            {reorderMode && (
              <button
                onClick={resetOrder}
                className="text-[11px] font-extrabold text-[#FFFFF0]/55 hover:text-[#FFFFF0] px-2.5 py-1.5 rounded-lg transition-colors uppercase tracking-wide"
              >
                Réinitialiser
              </button>
            )}
            <button
              onClick={() => { hapticImpact("light"); setReorderMode(!reorderMode); }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-extrabold uppercase tracking-wider transition-all active:scale-95"
              style={{
                background: reorderMode ? "#0088CC" : "rgba(0,136,204,0.12)",
                color: reorderMode ? "#FFFFF0" : "#0088CC",
                border: `1px solid ${reorderMode ? "transparent" : "rgba(0,136,204,0.30)"}`,
              }}
            >
              {reorderMode ? <Check size={13} /> : <Settings2 size={13} />}
              {reorderMode ? "Terminé" : "Personnaliser"}
            </button>
          </div>
        </motion.div>

        {/* Sections réordonnables */}
        <AnimatePresence initial={false}>
          {order.map((key, idx) => (
            <motion.div
              key={key}
              layout
              variants={fadeUp}
              transition={{ layout: { type: "spring", damping: 26, stiffness: 280 } }}
              className="relative"
            >
              {reorderMode && (
                <ReorderControls
                  label={SECTION_LABELS[key]}
                  canUp={idx > 0}
                  canDown={idx < order.length - 1}
                  onUp={() => moveSection(key, -1)}
                  onDown={() => moveSection(key, 1)}
                />
              )}
              <div className={reorderMode ? "rounded-2xl ring-1 ring-[#0088CC]/30" : ""}>
                {key === "identity" && (
                  <motion.div
                    variants={fadeUp}
                    className="mb-5 rounded-2xl p-5 relative overflow-hidden"
                    style={{
                      background:
                        "linear-gradient(135deg, rgba(0,136,204,0.10) 0%, rgba(17,17,17,0.6) 100%)",
                      border: "1px solid rgba(255,255,255,0.08)",
                    }}
                  >
                    <div
                      className="absolute -top-16 -right-16 w-48 h-48 rounded-full"
                      style={{ background: "radial-gradient(circle, rgba(0,136,204,0.18), transparent 70%)" }}
                    />
                    <div className="flex items-start gap-4 relative">
                      <ProfileAvatar photoUrl={photoUrl} name={displayName} size={68} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <div className="font-display text-lg text-[#FFFFF0] truncate" style={{ fontWeight: 900 }}>
                            {displayName}
                          </div>
                          {user?.is_premium && (
                            <BadgeCheck size={16} color="#0088CC" className="shrink-0" />
                          )}
                        </div>
                        {(profile?.username || user?.username) && (
                          <div className="text-sm font-semibold text-[#FFFFF0]/55 truncate">
                            @{profile?.username ?? user?.username}
                          </div>
                        )}
                        <button
                          onClick={() => copyToClipboard(String(userId))}
                          className="mt-1.5 inline-flex items-center gap-1.5 text-[11px] text-[#FFFFF0]/40 font-mono font-bold hover:text-[#FFFFF0]/70 transition-colors"
                        >
                          ID : {userId}
                          <Copy size={11} />
                        </button>
                      </div>
                    </div>

                    {/* Rang */}
                    <div className="mt-5 pt-4 border-t border-white/[0.06]">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
                          style={{
                            background: `${rank.current.color}1A`,
                            border: `1px solid ${rank.current.color}40`,
                          }}
                        >
                          <img
                            src={rank.current.icon} alt="" width={28} height={28} loading="lazy"
                            className="object-contain" style={{ pointerEvents: "none" }}
                          />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-1.5">
                              <Crown size={13} color={rank.current.color} />
                              <span
                                className="font-display text-sm"
                                style={{ color: rank.current.color, fontWeight: 900 }}
                              >
                                {rank.current.label}
                              </span>
                            </div>
                            {rank.next && (
                              <span className="text-[10px] text-[#FFFFF0]/40 font-mono font-bold">
                                {totalKgc.toLocaleString("fr-FR")} / {rank.next.min.toLocaleString("fr-FR")}
                              </span>
                            )}
                          </div>
                          <div className="mt-1.5 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${rank.progress * 100}%` }}
                              transition={{ duration: 0.8, ease: "easeOut" }}
                              className="h-full rounded-full"
                              style={{
                                background: `linear-gradient(90deg, ${rank.current.color}, ${rank.next?.color ?? rank.current.color})`,
                              }}
                            />
                          </div>
                          <div className="mt-1 text-[10px] font-bold text-[#FFFFF0]/40">
                            {rank.next ? `Prochain rang : ${rank.next.label}` : "Rang maximal atteint"}
                          </div>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}

                {key === "stats" && (
                  <motion.div variants={fadeUp} className="mb-5 grid grid-cols-3 gap-2">
                    <StatCard
                      icon={<ListChecks size={16} color="#0088CC" />}
                      label="Tâches"
                      value={(profile?.tasks_completed ?? 0).toLocaleString("fr-FR")}
                      tint="#0088CC"
                    />
                    <StatCard
                      icon={<TrendingUp size={16} color="#FFB200" />}
                      label="Total gagné"
                      value={totalKgc >= 1000 ? `${(totalKgc / 1000).toFixed(1)}k` : `${totalKgc}`}
                      sub="KGC"
                      tint="#FFB200"
                    />
                    <StatCard
                      icon={<History size={16} color="#A78BFA" />}
                      label="Retraits"
                      value={(profile?.withdrawals?.length ?? 0).toLocaleString("fr-FR")}
                      tint="#A78BFA"
                    />
                  </motion.div>
                )}

                {key === "balance" && (
                  <motion.div
                    variants={fadeUp}
                    className="mb-5 rounded-2xl p-5 text-center relative overflow-hidden"
                    style={{
                      background:
                        "linear-gradient(135deg, rgba(255,178,0,0.14), rgba(255,178,0,0.04))",
                      border: "1px solid rgba(255,178,0,0.25)",
                    }}
                  >
                    <div
                      className="absolute inset-0 pointer-events-none"
                      style={{
                        background:
                          "radial-gradient(circle at 50% 0%, rgba(255,178,0,0.18), transparent 60%)",
                      }}
                    />
                    <motion.div
                      initial={{ scale: 0.8, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ duration: 0.5, ease: "easeOut" }}
                      className="relative w-20 h-20 mx-auto mb-3"
                    >
                      <div
                        className="absolute inset-0 rounded-full"
                        style={{
                          background: "radial-gradient(circle, rgba(255,178,0,0.35), transparent 65%)",
                          filter: "blur(8px)",
                          animation: "glow-pulse 2.4s ease-in-out infinite",
                        }}
                      />
                      <img
                        src={KGC_SPHERE_SRC} alt="KGC-Sphère" width={80} height={80}
                        className="relative w-20 h-20 object-contain drop-shadow-[0_8px_24px_rgba(255,178,0,0.35)]"
                        style={{ pointerEvents: "none" }}
                      />
                    </motion.div>

                    <div className="text-[10px] font-extrabold text-[#FFFFF0]/55 uppercase tracking-[0.22em] mb-1.5">
                      Solde disponible
                    </div>
                    <div className="font-display text-4xl text-[#FFB200] mb-1 leading-none" style={{ fontWeight: 900 }}>
                      {balanceKgc.toLocaleString("fr-FR")}
                      <span className="text-lg ml-1.5 text-[#FFB200]/70">KGC</span>
                    </div>
                    <div className="flex items-center justify-center gap-2 text-sm font-bold text-[#FFFFF0]/65 mt-2">
                      <img src={USDT_LOGO_SRC} alt="" width={14} height={14}
                           className="object-contain" style={{ pointerEvents: "none" }} />
                      <span>{balanceUsdt.toFixed(3)} USDT</span>
                      <span className="text-[#FFFFF0]/25">•</span>
                      <span className="text-[#FFFFF0]/45">
                        {Math.floor(balanceXof).toLocaleString("fr-FR")} XOF
                      </span>
                    </div>

                    <div className="my-4 h-px bg-white/[0.08]" />

                    <Button variant="gold" fullWidth onClick={openWithdraw} disabled={!canWithdraw || reorderMode}>
                      <Wallet size={18} />
                      {canWithdraw ? "Retirer mes gains" : `Minimum ${MIN_WITHDRAW} USDT requis`}
                    </Button>

                    {!canWithdraw && (
                      <p className="mt-2 text-xs font-semibold text-[#FFFFF0]/45">
                        Il te manque {(MIN_WITHDRAW - balanceUsdt).toFixed(3)} USDT
                      </p>
                    )}
                  </motion.div>
                )}

                {key === "payments" && (
                  <motion.div variants={fadeUp} className="mb-5">
                    <div className="flex items-center justify-between mb-3">
                      <h2 className="font-display text-base text-[#FFFFF0] flex items-center gap-2" style={{ fontWeight: 800 }}>
                        <img src={JKP_LOGO_SRC} alt="" width={18} height={18}
                             className="object-contain" style={{ pointerEvents: "none" }} />
                        Comptes JessiKaPay
                      </h2>
                      <button
                        disabled={reorderMode}
                        onClick={() => {
                          setPmLabel(""); setPmAddress("");
                          setPmSheetOpen(true); hapticImpact("light");
                        }}
                        className="flex items-center gap-1 text-xs text-[#0088CC] hover:text-[#0099e0] font-extrabold uppercase tracking-wider transition-colors disabled:opacity-40"
                      >
                        <Plus size={13} />
                        Ajouter
                      </button>
                    </div>

                    {methods.length === 0 ? (
                      <div
                        className="rounded-xl px-4 py-5 text-center"
                        style={{
                          background: "rgba(255,255,255,0.03)",
                          border: "1px dashed rgba(255,255,255,0.10)",
                        }}
                      >
                        <Wallet size={20} color="rgba(255,255,240,0.30)" className="mx-auto mb-1.5" />
                        <p className="text-xs font-semibold text-[#FFFFF0]/60 leading-relaxed">
                          Aucun compte JessiKaPay enregistré.<br />
                          Collez votre numéro <span className="text-[#FFB200] font-extrabold">JP-XXXXXX</span> à l'avance pour des retraits express.
                        </p>
                      </div>
                    ) : (
                      <div className="flex flex-col gap-2">
                        {methods.map((m) => (
                          <SavedMethodRow
                            key={m.id}
                            m={m}
                            onDelete={() => requestRemoveMethod(m)}
                            onCopy={() => copyToClipboard(m.address)}
                          />
                        ))}
                      </div>
                    )}
                  </motion.div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Info traitement */}
        <motion.div
          variants={fadeUp}
          className="mb-5 rounded-xl px-4 py-3 flex gap-3 items-start"
          style={{
            background: "rgba(0,136,204,0.07)",
            border: "1px solid rgba(0,136,204,0.15)",
          }}
        >
          <Clock size={15} color="#0088CC" className="shrink-0 mt-0.5" />
          <p className="text-xs font-semibold text-[#FFFFF0]/70 leading-relaxed">
            Les retraits sont traités les <strong className="text-[#FFFFF0] font-extrabold">mardi et samedi</strong>.
            Après validation, JessiKaPay envoie le paiement sous 24h.
          </p>
        </motion.div>

        {/* Tâches */}
        <motion.div variants={fadeUp} className="mb-5">
          <Link to="/tasks">
            <div
              className="rounded-2xl p-4 flex items-center gap-3 transition-all active:scale-[0.98]"
              style={{
                background: "linear-gradient(135deg, rgba(255,178,0,0.10), rgba(255,178,0,0.02))",
                border: "1px solid rgba(255,178,0,0.22)",
              }}
            >
              <div
                className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
                style={{ background: "rgba(255,178,0,0.16)" }}
              >
                <Award size={20} color="#FFB200" />
              </div>
              <div className="flex-1">
                <div className="font-display text-sm text-[#FFFFF0]" style={{ fontWeight: 800 }}>
                  Tâches disponibles
                </div>
                <div className="text-xs font-semibold text-[#FFFFF0]/55">Gagne plus de KGC-Sphères</div>
              </div>
              <ChevronRight size={18} color="rgba(255,255,240,0.35)" />
            </div>
          </Link>
        </motion.div>

        {/* Historique */}
        {(profile?.withdrawals?.length ?? 0) > 0 && (
          <motion.div variants={fadeUp} className="mb-4">
            <h2 className="font-display text-base text-[#FFFFF0] mb-3 flex items-center gap-2" style={{ fontWeight: 800 }}>
              <History size={15} color="#A78BFA" />
              Historique des retraits
            </h2>
            <div className="flex flex-col gap-2">
              {(profile?.withdrawals ?? []).map((w) => (
                <WithdrawalRow key={w.id} w={w} />
              ))}
            </div>
          </motion.div>
        )}

      </motion.div>

      {/* ─── Bottom Sheet : Retrait ─────────────────────────────────── */}
      <BottomSheet
        isOpen={sheetOpen}
        onClose={() => setSheetOpen(false)}
        title="Retirer mes gains"
      >
        {sheetStep === "saved" && (
          <div className="flex flex-col gap-3 pb-4">
            <p className="text-sm font-semibold text-[#FFFFF0]/65">
              Sélectionnez un compte JessiKaPay enregistré.
            </p>
            <div className="flex flex-col gap-2">
              {methods.map((m) => (
                <button
                  key={m.id}
                  onClick={() => useSavedForWithdraw(m)}
                  className="w-full rounded-2xl p-3.5 flex items-center gap-3 text-left transition-all active:scale-[0.98]"
                  style={{
                    background: "rgba(255,255,255,0.04)",
                    border: "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  <MethodIcon />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-extrabold text-[#FFFFF0] truncate">{m.label}</div>
                    <div className="text-[11px] text-[#FFFFF0]/55 font-mono font-bold truncate">{m.address}</div>
                  </div>
                  <ChevronRight size={16} color="rgba(255,255,240,0.40)" />
                </button>
              ))}
            </div>
            <Button variant="ghost" fullWidth onClick={() => setSheetStep("jkpay_info")}>
              <Plus size={16} />
              Nouveau compte JessiKaPay
            </Button>
          </div>
        )}

        {sheetStep === "jkpay_info" && (
          <div className="flex flex-col gap-4 pb-4">
            <div className="rounded-2xl p-4"
                 style={{ background: "rgba(255,178,0,0.07)", border: "1px solid rgba(255,178,0,0.22)" }}>
              <div className="flex items-center gap-2 mb-2">
                <img src={JKP_LOGO_SRC} alt="" width={22} height={22}
                     className="object-contain" style={{ pointerEvents: "none" }} />
                <span className="font-display text-sm text-[#FFB200]" style={{ fontWeight: 900 }}>
                  Retrait via JessiKaPay
                </span>
              </div>
              <p className="text-xs font-semibold text-[#FFFFF0]/70 leading-relaxed">
                Les gains KGC-Sphères sont versés sur votre compte <strong className="text-[#FFB200] font-extrabold">JessiKaPay</strong>,
                le wallet Telegram Mobile Money couvrant 11+ pays d'Afrique francophone.
              </p>
              <p className="text-xs font-semibold text-[#FFFFF0]/70 leading-relaxed mt-2">
                Taux appliqué : <strong className="text-[#FFFFF0] font-extrabold">1 USDT = 500 XOF</strong>.
                Vous recevez ensuite votre paiement Orange / MTN / Wave / Moov directement dans JessiKaPay.
              </p>
              <div className="mt-3 pt-3 border-t border-white/10 flex items-center gap-4">
                <a href={JKP_URL} target="_blank" rel="noopener noreferrer"
                   className="text-xs text-[#FFB200] underline underline-offset-2 font-extrabold flex items-center gap-1">
                  En savoir plus <ExternalLink size={11} />
                </a>
                <a href={JKP_BOT} target="_blank" rel="noopener noreferrer"
                   className="text-xs text-[#0088CC] underline underline-offset-2 font-extrabold flex items-center gap-1">
                  @JessiKaPayBot <ExternalLink size={11} />
                </a>
              </div>
            </div>

            <label className="flex items-start gap-2 cursor-pointer">
              <button
                type="button"
                onClick={() => setJpAccepted(!jpAccepted)}
                className="w-5 h-5 rounded-md shrink-0 mt-0.5 flex items-center justify-center transition-all"
                style={{
                  background: jpAccepted ? "#FFB200" : "rgba(255,255,255,0.08)",
                  border: jpAccepted ? "none" : "1px solid rgba(255,255,255,0.20)",
                }}
              >
                {jpAccepted && <Check size={12} color="#0A0A0A" strokeWidth={3} />}
              </button>
              <span className="text-xs font-semibold text-[#FFFFF0]/70 leading-snug">
                J'ai un compte JessiKaPay actif et j'accepte les conditions du partenariat.
              </span>
            </label>

            <div className="flex gap-2">
              {methods.length > 0 && (
                <Button variant="ghost" fullWidth onClick={() => setSheetStep("saved")}>
                  Retour
                </Button>
              )}
              <Button
                fullWidth
                disabled={!jpAccepted}
                onClick={() => setSheetStep("form")}
                variant="gold"
              >
                Continuer
              </Button>
            </div>
          </div>
        )}

        {sheetStep === "form" && (
          <WithdrawForm
            label={label} setLabel={setLabel}
            address={address} setAddress={setAddress}
            amount={amount} setAmount={setAmount}
            balanceUsdt={balanceUsdt}
            saveMethod={saveMethod} setSaveMethod={setSaveMethod}
            submitting={submitting}
            onBack={() => setSheetStep(methods.length > 0 ? "saved" : "jkpay_info")}
            onSubmit={submitWithdrawal}
          />
        )}
      </BottomSheet>

      {/* ─── Bottom Sheet : Ajout compte JessiKaPay ───────────────── */}
      <BottomSheet
        isOpen={pmSheetOpen}
        onClose={() => setPmSheetOpen(false)}
        title="Nouveau compte JessiKaPay"
      >
        <div className="flex flex-col gap-4 pb-4">
          <div className="rounded-xl p-3 flex items-center gap-3"
               style={{ background: "rgba(255,178,0,0.07)", border: "1px solid rgba(255,178,0,0.20)" }}>
            <img src={JKP_LOGO_SRC} alt="" width={32} height={32}
                 className="object-contain shrink-0" style={{ pointerEvents: "none" }} />
            <div className="text-xs font-semibold text-[#FFFFF0]/70 leading-snug">
              Collez votre numéro JessiKaPay au format <strong className="text-[#FFB200] font-extrabold">JP-XXXXXX</strong>.
              Vous le trouvez dans <a href={JKP_BOT} target="_blank" rel="noopener noreferrer" className="text-[#0088CC] underline underline-offset-2 font-extrabold">@JessiKaPayBot</a>.
            </div>
          </div>

          <Field label="Nom du compte (optionnel)">
            <input
              type="text"
              value={pmLabel}
              onChange={(e) => setPmLabel(e.target.value)}
              placeholder="Mon JessiKaPay principal"
              className="w-full h-12 rounded-xl px-4 text-sm font-semibold text-[#FFFFF0] outline-none"
              style={{
                background: "rgba(255,255,255,0.06)",
                border: "1px solid rgba(255,255,255,0.15)",
              }}
            />
          </Field>

          <Field label="Numéro JessiKaPay">
            <input
              type="text"
              value={pmAddress}
              onChange={(e) => setPmAddress(e.target.value.toUpperCase())}
              placeholder="JP-XXXXXX"
              className="w-full h-12 rounded-xl px-4 text-sm text-[#FFFFF0] font-mono font-bold outline-none tracking-wider"
              style={{
                background: "rgba(255,255,255,0.06)",
                border: "1px solid rgba(255,255,255,0.15)",
              }}
            />
            <p className="mt-1.5 text-xs font-semibold text-[#FFFFF0]/45">
              Format : JP- suivi de votre identifiant (lettres / chiffres).
            </p>
          </Field>

          <div className="flex gap-2">
            <Button variant="ghost" fullWidth onClick={() => setPmSheetOpen(false)}>
              Annuler
            </Button>
            <Button
              fullWidth
              variant="gold"
              disabled={!pmAddress.trim()}
              onClick={requestAddPaymentMethod}
            >
              Enregistrer
            </Button>
          </div>
        </div>
      </BottomSheet>

      {/* Confirmations */}
      <ConfirmDialog
        isOpen={confirmSave}
        onClose={() => setConfirmSave(false)}
        onConfirm={confirmAddPaymentMethod}
        title="Enregistrer ce compte JessiKaPay ?"
        description={
          <>
            <strong className="text-[#FFFFF0] font-extrabold">JessiKaPay</strong>
            {" "}—{" "}
            <span className="font-mono font-bold text-[#FFFFF0]/85 break-all">
              {normalizeJpNumber(pmAddress)}
            </span>
            <br />
            Vérifiez que le numéro est correct. Il sera utilisé pour vos prochains retraits.
          </>
        }
        confirmLabel="Enregistrer"
        cancelLabel="Modifier"
        tone="primary"
      />

      <ConfirmDialog
        isOpen={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        onConfirm={confirmRemoveMethod}
        title="Supprimer ce compte JessiKaPay ?"
        description={
          confirmDelete && (
            <>
              <strong className="text-[#FFFFF0] font-extrabold">{confirmDelete.label}</strong>
              <br />
              <span className="font-mono font-bold text-[#FFFFF0]/85 break-all">{confirmDelete.address}</span>
              <br />
              Cette action est irréversible. Vous devrez le réenregistrer pour l'utiliser à nouveau.
            </>
          )
        }
        confirmLabel="Supprimer"
        cancelLabel="Annuler"
        tone="danger"
      />
    </PageWrapper>
  );
}

/* ─── Sous-composants ──────────────────────────────────────────────────── */

function ReorderControls({
  label, canUp, canDown, onUp, onDown,
}: { label: string; canUp: boolean; canDown: boolean; onUp: () => void; onDown: () => void }) {
  return (
    <div
      className="mb-2 flex items-center justify-between rounded-xl px-3 py-2"
      style={{
        background: "rgba(0,136,204,0.08)",
        border: "1px solid rgba(0,136,204,0.25)",
      }}
    >
      <span className="text-[11px] font-extrabold uppercase tracking-wider text-[#0088CC]">
        {label}
      </span>
      <div className="flex items-center gap-1">
        <button
          onClick={onUp} disabled={!canUp} aria-label="Monter"
          className="w-7 h-7 rounded-lg flex items-center justify-center text-[#FFFFF0] transition-all active:scale-90 disabled:opacity-30 disabled:cursor-not-allowed"
          style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.10)" }}
        >
          <ArrowUp size={13} />
        </button>
        <button
          onClick={onDown} disabled={!canDown} aria-label="Descendre"
          className="w-7 h-7 rounded-lg flex items-center justify-center text-[#FFFFF0] transition-all active:scale-90 disabled:opacity-30 disabled:cursor-not-allowed"
          style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.10)" }}
        >
          <ArrowDown size={13} />
        </button>
      </div>
    </div>
  );
}

function StatCard({
  icon, label, value, sub, tint,
}: { icon: React.ReactNode; label: string; value: string; sub?: string; tint: string }) {
  return (
    <div
      className="rounded-2xl px-3 py-3 flex flex-col"
      style={{
        background: `linear-gradient(135deg, ${tint}10, rgba(255,255,255,0.02))`,
        border: `1px solid ${tint}1F`,
      }}
    >
      <div className="flex items-center gap-1.5 mb-2">
        {icon}
        <span className="text-[10px] font-extrabold text-[#FFFFF0]/55 uppercase tracking-wider">{label}</span>
      </div>
      <div className="font-display text-base text-[#FFFFF0] leading-none" style={{ fontWeight: 900 }}>
        {value}
        {sub && <span className="text-[10px] ml-1 font-bold text-[#FFFFF0]/45">{sub}</span>}
      </div>
    </div>
  );
}

function MethodIcon() {
  const tint = "#FFB200";
  return (
    <div
      className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
      style={{ background: `${tint}1F`, border: `1px solid ${tint}33` }}
    >
      <img src={JKP_LOGO_SRC} alt="" width={24} height={24}
           className="object-contain" style={{ pointerEvents: "none" }} />
    </div>
  );
}

function SavedMethodRow({
  m, onDelete, onCopy,
}: { m: SavedPaymentMethod; onDelete: () => void; onCopy: () => void }) {
  return (
    <div
      className="rounded-xl px-3 py-3 flex items-center gap-3"
      style={{
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      <MethodIcon />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-extrabold text-[#FFFFF0] truncate">{m.label}</div>
        <div className="text-[11px] text-[#FFB200]/80 font-mono font-bold truncate">{m.address}</div>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        <button
          onClick={onCopy}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-[#FFFFF0]/50 hover:text-[#FFFFF0] hover:bg-white/[0.06] transition-all active:scale-90"
          aria-label="Copier"
        >
          <Copy size={14} />
        </button>
        <button
          onClick={onDelete}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-[#FFFFF0]/50 hover:text-[#EF4444] hover:bg-[#EF4444]/10 transition-all active:scale-90"
          aria-label="Supprimer"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-extrabold text-[#FFFFF0]/65 mb-2 uppercase tracking-wider">
        {label}
      </label>
      {children}
    </div>
  );
}

interface WithdrawFormProps {
  label: string; setLabel: (v: string) => void;
  address: string; setAddress: (v: string) => void;
  amount: string; setAmount: (v: string) => void;
  balanceUsdt: number;
  saveMethod: boolean; setSaveMethod: (v: boolean) => void;
  submitting: boolean;
  onBack: () => void; onSubmit: () => void;
}
function WithdrawForm(p: WithdrawFormProps) {
  const amountNum = parseFloat(p.amount) || 0;
  const xofAmount = amountNum * USDT_TO_XOF;

  return (
    <div className="flex flex-col gap-4 pb-4">
      <div className="rounded-xl px-4 py-3 flex gap-2 items-start"
           style={{ background: "rgba(0,136,204,0.07)", border: "1px solid rgba(0,136,204,0.18)" }}>
        <Sparkles size={14} color="#0088CC" className="shrink-0 mt-0.5" />
        <p className="text-xs font-semibold text-[#FFFFF0]/75 leading-snug">
          Le montant sera envoyé sur votre compte JessiKaPay puis converti en Mobile Money à <strong className="text-[#FFFFF0] font-extrabold">{xofAmount.toLocaleString("fr-FR")} XOF</strong>.
        </p>
      </div>

      <Field label="Libellé (optionnel)">
        <input
          type="text"
          value={p.label}
          onChange={(e) => p.setLabel(e.target.value)}
          placeholder="Mon JessiKaPay"
          className="w-full h-12 rounded-xl px-4 text-sm font-semibold text-[#FFFFF0] outline-none"
          style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.15)" }}
        />
      </Field>

      <Field label="Numéro JessiKaPay (JP-XXXXXX)">
        <input
          type="text"
          value={p.address}
          onChange={(e) => p.setAddress(e.target.value.toUpperCase())}
          placeholder="JP-XXXXXX"
          className="w-full h-12 rounded-xl px-4 text-sm text-[#FFFFF0] font-mono font-bold outline-none tracking-wider"
          style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.15)" }}
        />
        <p className="mt-1.5 text-xs font-semibold text-[#FFFFF0]/45">
          Trouvable dans <a href={JKP_BOT} target="_blank" rel="noopener noreferrer" className="text-[#0088CC] underline underline-offset-2 font-extrabold">@JessiKaPayBot</a>.
        </p>
      </Field>

      <Field label="Montant USDT à retirer">
        <input
          type="number"
          value={p.amount}
          onChange={(e) => p.setAmount(e.target.value)}
          step="0.001"
          min={MIN_WITHDRAW}
          max={p.balanceUsdt}
          className="w-full h-12 rounded-xl px-4 text-sm text-[#FFFFF0] font-mono font-bold outline-none"
          style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.15)" }}
        />
        <p className="mt-1.5 text-xs font-semibold text-[#FFFFF0]/45">
          Solde disponible : <span className="text-[#FFB200] font-extrabold">{p.balanceUsdt.toFixed(3)} USDT</span>
        </p>
      </Field>

      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={p.saveMethod}
          onChange={(e) => p.setSaveMethod(e.target.checked)}
          className="w-4 h-4 accent-[#0088CC]"
        />
        <span className="text-xs font-semibold text-[#FFFFF0]/70">
          Enregistrer ce compte pour les prochains retraits
        </span>
      </label>

      <div className="flex gap-2">
        <Button variant="ghost" fullWidth onClick={p.onBack} disabled={p.submitting}>
          Retour
        </Button>
        <Button
          fullWidth
          variant="gold"
          onClick={p.onSubmit}
          disabled={p.submitting || !p.address.trim()}
          loading={p.submitting}
        >
          <CheckCircle2 size={16} />
          Valider le retrait
        </Button>
      </div>
    </div>
  );
}

function WithdrawalRow({ w }: { w: Withdrawal }) {
  const status = {
    pending:  { label: "En attente", color: "#F59E0B", icon: Clock },
    approved: { label: "Approuvé",   color: "#22C55E", icon: CheckCircle2 },
    rejected: { label: "Rejeté",     color: "#EF4444", icon: AlertCircle },
  }[w.status];
  const Icon = status.icon;
  const date = new Date(w.requested_at).toLocaleDateString("fr-FR", {
    day: "2-digit", month: "short", year: "numeric",
  });

  return (
    <div
      className="rounded-xl px-3 py-3 flex items-center gap-3"
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      <div
        className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
        style={{ background: `${status.color}1A`, border: `1px solid ${status.color}40` }}
      >
        <Icon size={15} color={status.color} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <div className="text-sm font-extrabold text-[#FFFFF0]">
            {w.amount_usdt.toFixed(3)} USDT
          </div>
          <div className="text-[10px] font-extrabold uppercase tracking-wider"
               style={{ color: status.color }}>
            {status.label}
          </div>
        </div>
        <div className="text-[11px] text-[#FFFFF0]/45 font-mono font-bold truncate mt-0.5">
          {w.address}
        </div>
        <div className="text-[10px] font-semibold text-[#FFFFF0]/35 mt-0.5">{date}</div>
      </div>
    </div>
  );
}
