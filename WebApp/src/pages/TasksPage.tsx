/**
 * TasksPage — Tâches & Gains KGC-Sphères
 * - AdsGram Native Task via web component <adsgram-task> (blockId task-33568)
 * - Monetag Rewarded Popup (zone 11019878)
 */
import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import {
  CheckCircle2, Loader2, ArrowLeft, ExternalLink,
  Zap, AlertCircle, Trophy, Sparkles, Coins, ChevronRight,
} from "lucide-react";
import { Link } from "@tanstack/react-router";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Button } from "@/components/fs/Button";
import { Card } from "@/components/fs/Card";
import { Badge } from "@/components/fs/Badge";
import { ToastProvider, useToast } from "@/components/fs/Toast";
import { fadeUp, staggerContainer } from "@/lib/animations";
import { getTasks, claimTask, getUserProfile } from "@/lib/api";
import { getTelegramUser, expandWebApp, hapticSuccess, hapticError } from "@/lib/telegram";

const KGC_SPHERE_SRC = "/assets/kgc-sphere.png";
const USDT_LOGO_SRC  = "/assets/plans/usdt.png";

interface Task {
  id: string;
  title: string;
  description: string;
  reward_kgc: number;
  type: "adsgram" | "monetag" | "manual";
  url?: string;
  completed: boolean;
}

// --- Types pour le web component AdsGram Task ---
declare global {
  interface Window {
    show_11019878?: () => Promise<void>;
  }
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace JSX {
    interface IntrinsicElements {
      "adsgram-task": React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        "data-block-id"?: string;
        "data-debug"?: string;
        "data-debug-console"?: string;
      };
    }
  }
}

// --- Monetag Rewarded Popup ---
async function showMonetagTask(): Promise<boolean> {
  return new Promise((resolve) => {
    if (typeof window.show_11019878 === "function") {
      window.show_11019878().then(() => resolve(true)).catch(() => resolve(false));
      return;
    }
    const deadline = Date.now() + 2000;
    const poll = () => {
      if (typeof window.show_11019878 === "function") {
        window.show_11019878().then(() => resolve(true)).catch(() => resolve(false));
      } else if (Date.now() < deadline) {
        setTimeout(poll, 200);
      } else {
        resolve(false);
      }
    };
    poll();
  });
}

export function TasksPage() {
  return <ToastProvider><TasksInner /></ToastProvider>;
}

function TasksInner() {
  const [tasks, setTasks]       = useState<Task[]>([]);
  const [profile, setProfile]   = useState<{ balance_kgc: number; balance_usdt: number } | null>(null);
  const [loading, setLoading]   = useState(true);
  const [claiming, setClaiming] = useState<string | null>(null);
  const { toast } = useToast();

  const user = getTelegramUser();
  const userId = user?.id ?? 0;

  useEffect(() => {
    expandWebApp();
    if (!userId) { setLoading(false); return; }
    Promise.all([getTasks(userId), getUserProfile(userId)]).then(([t, p]) => {
      setTasks(t?.tasks ?? []);
      setProfile(p?.profile ?? null);
      setLoading(false);
    });
  }, [userId]);

  const handleTask = async (task: Task) => {
    if (task.completed || claiming) return;
    setClaiming(task.id);

    let adWatched = false;

    if (task.type === "monetag") {
      adWatched = await showMonetagTask();
    } else if (task.type === "manual" && task.url) {
      window.open(task.url, "_blank");
      adWatched = true;
    } else if (task.type === "adsgram") {
      // Pour adsgram, le TaskCard gère le web component directement.
      // On laisse TaskCard signaler via onAdsgramReward ci-dessous.
      // (Voir AdsgramTaskCard)
      setClaiming(null);
      return;
    }

    if (!adWatched) {
      hapticError();
      toast("Tâche non complétée. Réessayez.", "error");
      setClaiming(null);
      return;
    }

    await completeClaim(task);
    setClaiming(null);
  };

  const completeClaim = async (task: Task) => {
    const res = await claimTask(userId, task.id);
    if (res?.success) {
      hapticSuccess();
      toast(`+${task.reward_kgc} KGC-Sphères gagnés !`, "success");
      setTasks((prev) => prev.map((t) => t.id === task.id ? { ...t, completed: true } : t));
      if (profile) {
        setProfile((p) => p ? {
          ...p,
          balance_kgc: p.balance_kgc + task.reward_kgc,
          balance_usdt: (p.balance_kgc + task.reward_kgc) * 0.001,
        } : p);
      }
    } else {
      hapticError();
      toast(res?.error || "Erreur lors de la validation.", "error");
    }
  };

  const KGC_TO_USDT = 0.001;
  const balanceKgc  = profile?.balance_kgc ?? 0;
  const balanceUsdt = (balanceKgc * KGC_TO_USDT).toFixed(3);
  const minWithdraw = 3;
  const progress    = Math.min(parseFloat(balanceUsdt) / minWithdraw, 1);
  const activeCount = tasks.filter((t) => !t.completed).length;

  return (
    <PageWrapper subtitle="Tâches & Gains">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible">

        <motion.div variants={fadeUp} className="mb-5">
          <Link to="/">
            <button className="flex items-center gap-2 text-sm font-bold text-[#FFFFF0]/55 hover:text-[#FFFFF0] transition-colors">
              <ArrowLeft size={16} /> Retour
            </button>
          </Link>
        </motion.div>

        {/* Header solde */}
        <motion.div
          variants={fadeUp}
          className="mb-5 rounded-2xl p-5 text-center relative overflow-hidden"
          style={{
            background: "linear-gradient(135deg, rgba(255,178,0,0.14), rgba(255,178,0,0.04))",
            border: "1px solid rgba(255,178,0,0.28)",
          }}
        >
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: "radial-gradient(circle at 50% 0%, rgba(255,178,0,0.20), transparent 60%)",
            }}
          />

          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="relative w-20 h-20 mx-auto mb-3"
          >
            <div
              className="absolute inset-0 rounded-full"
              style={{
                background: "radial-gradient(circle, rgba(255,178,0,0.35), transparent 65%)",
                filter: "blur(10px)",
                animation: "glow-pulse 2.4s ease-in-out infinite",
              }}
            />
            <img
              src={KGC_SPHERE_SRC}
              alt="KGC-Sphère"
              width={80}
              height={80}
              className="relative w-20 h-20 object-contain drop-shadow-[0_8px_24px_rgba(255,178,0,0.4)]"
              style={{ pointerEvents: "none" }}
            />
          </motion.div>

          <div className="text-[10px] font-extrabold text-[#FFFFF0]/55 uppercase tracking-[0.22em] mb-1">
            Solde KGC
          </div>
          <div className="font-display text-4xl text-[#FFB200] leading-none" style={{ fontWeight: 900 }}>
            {balanceKgc.toLocaleString("fr-FR")}
            <span className="text-lg ml-1.5 text-[#FFB200]/70">KGC</span>
          </div>
          <div className="flex items-center justify-center gap-2 text-sm font-bold text-[#FFFFF0]/65 mt-2">
            <img src={USDT_LOGO_SRC} alt="" width={14} height={14}
                 className="object-contain" style={{ pointerEvents: "none" }} />
            <span>{balanceUsdt} USDT</span>
            <span className="text-[#FFFFF0]/25">•</span>
            <span className="text-[#FFFFF0]/45 font-extrabold">1 KGC = 0.001 USDT</span>
          </div>

          {/* Progress */}
          <div className="mt-4">
            <div className="flex justify-between text-[11px] font-extrabold text-[#FFFFF0]/55 mb-1.5 uppercase tracking-wider">
              <span>Vers retrait min.</span>
              <span>{balanceUsdt} / {minWithdraw} USDT</span>
            </div>
            <div className="h-2 rounded-full bg-white/10 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${progress * 100}%` }}
                transition={{ duration: 1, ease: "easeOut" }}
                className="h-full rounded-full"
                style={{ background: "linear-gradient(90deg, #FFB200, #FF8C00)" }}
              />
            </div>
          </div>

          <Link to="/profile">
            <button className="mt-4 inline-flex items-center gap-1 text-xs font-extrabold text-[#FFB200] underline underline-offset-2 uppercase tracking-wider">
              Voir mon profil & retirer <ChevronRight size={12} />
            </button>
          </Link>
        </motion.div>

        {/* Info */}
        <motion.div
          variants={fadeUp}
          className="mb-5 rounded-xl px-4 py-3 flex gap-3 items-start"
          style={{ background: "rgba(0,136,204,0.07)", border: "1px solid rgba(0,136,204,0.18)" }}
        >
          <AlertCircle size={16} color="#0088CC" className="shrink-0 mt-0.5" />
          <p className="text-xs font-semibold text-[#FFFFF0]/70 leading-relaxed">
            Accomplis les tâches pour gagner des KGC-Sphères. Retraits traités <strong className="text-[#FFFFF0] font-extrabold">mardi & samedi</strong>. Min. <strong className="text-[#FFFFF0] font-extrabold">3 USDT</strong> via JessiKaPay.
          </p>
        </motion.div>

        {/* Liste */}
        <motion.div variants={fadeUp} className="mb-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-display text-lg text-[#FFFFF0] flex items-center gap-2" style={{ fontWeight: 900 }}>
              <Sparkles size={16} color="#FFB200" />
              Tâches disponibles
            </h2>
            <Badge color="#0088CC">{activeCount} actives</Badge>
          </div>
        </motion.div>

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="animate-spin" size={28} color="#0088CC" />
          </div>
        ) : tasks.length === 0 ? (
          <motion.div variants={fadeUp} className="text-center py-12 text-[#FFFFF0]/50">
            <Trophy size={36} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm font-extrabold">Aucune tâche disponible pour l'instant.</p>
            <p className="text-xs font-semibold mt-1 text-[#FFFFF0]/40">Reviens plus tard !</p>
          </motion.div>
        ) : (
          <div className="flex flex-col gap-3">
            {tasks.map((task) => (
              <motion.div key={task.id} variants={fadeUp}>
                {task.type === "adsgram" ? (
                  // ✅ AdsGram Task → web component natif <adsgram-task>
                  <AdsgramTaskCard
                    task={task}
                    onReward={() => completeClaim(task)}
                  />
                ) : (
                  // Monetag & Manual → bouton classique
                  <TaskCard
                    task={task}
                    onClaim={() => handleTask(task)}
                    claiming={claiming === task.id}
                  />
                )}
              </motion.div>
            ))}
          </div>
        )}

        {parseFloat(balanceUsdt) >= minWithdraw && (
          <motion.div variants={fadeUp} className="mt-6">
            <Link to="/profile">
              <Button variant="gold" fullWidth size="lg">
                <Coins size={18} />
                Retirer mes gains ({balanceUsdt} USDT)
              </Button>
            </Link>
          </motion.div>
        )}

      </motion.div>
    </PageWrapper>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// AdsgramTaskCard — intègre le vrai web component <adsgram-task>
// Conformément à la doc : https://docs.adsgram.ai/publisher/task-integration-example
// ─────────────────────────────────────────────────────────────────────────────
function AdsgramTaskCard({ task, onReward }: { task: Task; onReward: () => void }) {
  const taskRef = useRef<HTMLElement>(null);
  const [claimed, setClaimed] = useState(task.completed);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    const el = taskRef.current;
    if (!el) return;

    // ✅ Événement "reward" : utilisateur a complété la tâche
    const handleReward = () => {
      setClaimed(true);
      onReward();
    };

    // ✅ Événement "onError" : erreur de chargement
    const handleError = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      console.error("[AdsGram Task] onError", detail);
      setError("Erreur AdsGram. Réessayez.");
    };

    // ✅ Événement "onBannerNotFound" : pas de tâche disponible
    const handleNotFound = () => {
      setError("Aucune tâche AdsGram disponible pour l'instant.");
    };

    // ✅ Événement "onTooLongSession" : session trop longue
    const handleTooLong = () => {
      setError("Session trop longue. Relancez l'application.");
    };

    el.addEventListener("reward", handleReward);
    el.addEventListener("onError", handleError);
    el.addEventListener("onBannerNotFound", handleNotFound);
    el.addEventListener("onTooLongSession", handleTooLong);

    return () => {
      el.removeEventListener("reward", handleReward);
      el.removeEventListener("onError", handleError);
      el.removeEventListener("onBannerNotFound", handleNotFound);
      el.removeEventListener("onTooLongSession", handleTooLong);
    };
  }, [onReward]);

  // ⚠️ Si le custom element n'est pas encore enregistré (SDK pas chargé),
  // on ne rend rien pour éviter un crash React
  if (typeof window !== "undefined" && !customElements.get("adsgram-task")) {
    return (
      <Card className="p-4">
        <div className="flex items-center gap-3">
          <Loader2 size={18} className="animate-spin" color="#0088CC" />
          <p className="text-xs text-[#FFFFF0]/55">Chargement AdsGram SDK...</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-4">
      <div className="flex flex-col gap-3">
        {/* En-tête tâche */}
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
               style={{ background: "rgba(0,136,204,0.12)", border: "1px solid rgba(0,136,204,0.25)" }}>
            {claimed
              ? <CheckCircle2 size={20} color="#22C55E" />
              : <Zap size={20} color="#0088CC" />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5 flex-wrap">
              <span className="font-extrabold text-sm text-[#FFFFF0] truncate">{task.title}</span>
              <Badge color="#0088CC" className="text-[10px] shrink-0">AdsGram</Badge>
            </div>
            <p className="text-xs font-semibold text-[#FFFFF0]/55 leading-snug mb-1">{task.description}</p>
            <div className="flex items-center gap-1.5">
              <img src={KGC_SPHERE_SRC} alt="" width={14} height={14}
                   className="object-contain" style={{ pointerEvents: "none" }} />
              <span className="text-xs font-extrabold text-[#FFB200]">+{task.reward_kgc} KGC</span>
              <span className="text-[10px] font-bold text-[#FFFFF0]/35">
                ≈ ${(task.reward_kgc * 0.001).toFixed(3)}
              </span>
            </div>
          </div>
          {claimed && (
            <div className="text-xs font-extrabold text-[#22C55E] flex items-center gap-1 shrink-0">
              <CheckCircle2 size={14} /> Fait
            </div>
          )}
        </div>

        {/* Message d'erreur */}
        {error && (
          <div className="rounded-lg px-3 py-2 text-xs font-semibold text-[#EF4444]"
               style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.20)" }}>
            {error}
          </div>
        )}

        {/* ✅ Web component AdsGram Task — intégration correcte selon la doc */}
        {!claimed && (
          <adsgram-task
            ref={taskRef as React.RefObject<HTMLElement>}
            data-block-id="task-33568"
            data-debug="false"
            data-debug-console="false"
            style={{
              display: "block",
              width: "100%",
              borderRadius: "12px",
              background: "rgba(0,136,204,0.06)",
              border: "1px solid rgba(0,136,204,0.18)",
              padding: "8px 12px 8px 8px",
              "--adsgram-task-font-size": "14px",
              "--adsgram-task-icon-size": "40px",
              "--adsgram-task-icon-title-gap": "12px",
              "--adsgram-task-button-width": "70px",
              "--adsgram-task-icon-border-radius": "8px",
            } as React.CSSProperties}
          >
            {/* Slot reward — récompense affichée */}
            <span slot="reward" style={{ fontSize: 12, color: "#FFB200", fontWeight: 800 }}>
              +{task.reward_kgc} KGC
            </span>
            {/* Slot button — bouton initial */}
            <div slot="button" style={{
              background: "#0088CC", color: "#fff", borderRadius: 8,
              padding: "6px 14px", fontSize: 12, fontWeight: 800,
            }}>
              Commencer
            </div>
            {/* Slot claim — après avoir fait la tâche, avant de claim */}
            <div slot="claim" style={{
              background: "#F59E0B", color: "#0A0A0A", borderRadius: 8,
              padding: "6px 14px", fontSize: 12, fontWeight: 800,
            }}>
              Réclamer
            </div>
            {/* Slot done — après avoir reçu la récompense */}
            <div slot="done" style={{
              background: "#22C55E", color: "#fff", borderRadius: 8,
              padding: "6px 14px", fontSize: 12, fontWeight: 800,
            }}>
              Fait ✓
            </div>
          </adsgram-task>
        )}
      </div>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TaskCard classique (Monetag & Manual)
// ─────────────────────────────────────────────────────────────────────────────
function TaskCard({ task, onClaim, claiming }: {
  task: Task; onClaim: () => void; claiming: boolean;
}) {
  const typeLabel: Record<string, string> = {
    monetag: "Monetag",
    manual:  "Manuelle",
  };
  const typeColor: Record<string, string> = {
    monetag: "#9333EA",
    manual:  "#22C55E",
  };
  const color = typeColor[task.type] ?? "#FFB200";

  return (
    <Card className="p-4">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
             style={{ background: `${color}18`, border: `1px solid ${color}30` }}>
          {task.completed
            ? <CheckCircle2 size={20} color="#22C55E" />
            : <Zap size={20} color={color} />}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5 flex-wrap">
            <span className="font-extrabold text-sm text-[#FFFFF0] truncate">{task.title}</span>
            <Badge color={color} className="text-[10px] shrink-0">{typeLabel[task.type]}</Badge>
          </div>
          <p className="text-xs font-semibold text-[#FFFFF0]/55 leading-snug mb-2">{task.description}</p>

          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <img src={KGC_SPHERE_SRC} alt="" width={14} height={14}
                   className="object-contain" style={{ pointerEvents: "none" }} />
              <span className="text-xs font-extrabold text-[#FFB200]">+{task.reward_kgc} KGC</span>
              <span className="text-[10px] font-bold text-[#FFFFF0]/35">
                ≈ ${(task.reward_kgc * 0.001).toFixed(3)}
              </span>
            </div>
            {task.url && !task.completed && (
              <a href={task.url} target="_blank" rel="noopener noreferrer"
                 className="flex items-center gap-1 text-xs text-[#0088CC] opacity-60 hover:opacity-100">
                <ExternalLink size={12} />
              </a>
            )}
          </div>
        </div>

        <div className="shrink-0">
          {task.completed ? (
            <div className="text-xs font-extrabold text-[#22C55E] flex items-center gap-1">
              <CheckCircle2 size={14} /> Fait
            </div>
          ) : (
            <button
              onClick={onClaim}
              disabled={claiming}
              className="h-9 px-3.5 rounded-lg text-xs font-extrabold uppercase tracking-wider transition-all active:scale-95 disabled:opacity-50"
              style={{ background: color, color: "#0A0A0A" }}
            >
              {claiming ? <Loader2 size={14} className="animate-spin" /> : "Commencer"}
            </button>
          )}
        </div>
      </div>
    </Card>
  );
}
