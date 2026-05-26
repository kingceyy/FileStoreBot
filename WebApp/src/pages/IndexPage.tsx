import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Lock, CheckCircle2, Loader2, Circle, Crown, Star, ChevronRight } from "lucide-react";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Button } from "@/components/fs/Button";
import { Badge } from "@/components/fs/Badge";
import { Card } from "@/components/fs/Card";
import { SessionStatus } from "@/components/shared/SessionStatus";
import { fadeUp, staggerContainer, scaleIn } from "@/lib/animations";
import { checkSession, watchAd } from "@/lib/api";
import { expandWebApp, getQueryParams, getTelegramUser, hapticSuccess, hapticError } from "@/lib/telegram";

type StepState = "idle" | "running" | "done" | "error";

// --- Types AdsGram ---
declare global {
  interface Window {
    Adsgram?: {
      init(params: { blockId: string; debug?: boolean }): {
        show(): Promise<{ done: boolean; error: boolean; description?: string }>;
        destroy(): void;
      };
    };
    show_11019878?: () => Promise<void>;
  }
}

// --- Monetag silencieux (caché UI mais fonctionnel) ---
async function showMonetagAdSilent(): Promise<void> {
  return new Promise((resolve) => {
    const attempt = () => {
      if (typeof window.show_11019878 === "function") {
        window.show_11019878()
          .then(() => resolve())
          .catch(() => resolve()); // Ignore erreur, on continue quand même
        return;
      }
      resolve(); // Pas de SDK, on continue
    };

    if (typeof window.show_11019878 === "function") {
      attempt();
    } else {
      // Attendre max 3s le SDK puis continuer
      const deadline = Date.now() + 3000;
      const poll = () => {
        if (typeof window.show_11019878 === "function") {
          attempt();
        } else if (Date.now() < deadline) {
          setTimeout(poll, 200);
        } else {
          resolve(); // Timeout, on continue sans Monetag
        }
      };
      poll();
    }
  });
}

// --- AdsGram Rewarded Video ---
async function showAdsgramRewardedVideo(): Promise<void> {
  return new Promise((resolve, reject) => {
    const attempt = () => {
      if (!window.Adsgram) {
        reject(new Error("AdsGram SDK non disponible"));
        return;
      }
      try {
        const controller = window.Adsgram.init({ blockId: "30344", debug: false });
        controller
          .show()
          .then((result) => {
            if (result.error) {
              reject(new Error(result.description || "AdsGram erreur"));
            } else {
              resolve();
            }
          })
          .catch(reject);
      } catch (e) {
        reject(e);
      }
    };

    if (window.Adsgram) {
      attempt();
    } else {
      const deadline = Date.now() + 3000;
      const poll = () => {
        if (window.Adsgram) {
          attempt();
        } else if (Date.now() < deadline) {
          setTimeout(poll, 200);
        } else {
          reject(new Error("AdsGram SDK non disponible"));
        }
      };
      poll();
    }
  });
}

export function IndexPage() {
  const [loading, setLoading] = useState(true);
  const [session, setSession] = useState<{ expiresAt: number; type: "free" | "premium" } | null>(null);
  const [step1, setStep1] = useState<StepState>("idle");
  const [success, setSuccess] = useState(false);
  const [running, setRunning] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const user = getTelegramUser();
  const userId = user?.id ?? 0;

  const { cloneId, idPubs } = getQueryParams();

  useEffect(() => {
    expandWebApp();
    if (!userId) { setLoading(false); return; }
    checkSession(userId, cloneId, idPubs).then((res) => {
      if (res?.active && res?.expires_at) {
        setSession({ expiresAt: Number(res.expires_at) * 1000, type: res.type ?? "free" });
      }
      setLoading(false);
    });
  }, [userId]);

  const runFlow = async () => {
    if (!userId) {
      setErrorMsg("Impossible d'identifier votre compte Telegram. Ouvrez ce lien depuis Telegram.");
      return;
    }

    setRunning(true);
    setErrorMsg(null);

    // Étape cachée : Monetag en arrière-plan (silencieux)
    await showMonetagAdSilent();

    // Étape visible : AdsGram
    setStep1("running");
    try {
      await showAdsgramRewardedVideo();
      setStep1("done");
    } catch (err) {
      console.error("[AdsGram]", err);
      setStep1("error");
      hapticError();
      setErrorMsg("La publicite est indisponible. Reessayez dans quelques secondes.");
      setRunning(false);
      return;
    }

    const res = await watchAd(userId, cloneId, idPubs);

    if (res?.success === false && 
        res?.message !== "Session already active" && 
        res?.message !== "Session deja active pour ce bot") {
      setErrorMsg(res?.error || "Erreur lors de l'activation de la session.");
      hapticError();
      setRunning(false);
      return;
    }

    const freshSession = await checkSession(userId, cloneId, idPubs);
    if (freshSession?.active && freshSession?.expires_at) {
      setSession({ 
        expiresAt: Number(freshSession.expires_at) * 1000, 
        type: freshSession.type ?? "free" 
      });
    }

    hapticSuccess();
    setSuccess(true);
    setRunning(false);
  };

  if (loading) return (
    <PageWrapper subtitle="Acces Securise">
      <div className="flex justify-center pt-20">
        <Loader2 className="animate-spin" size={32} color="#0088CC" />
      </div>
    </PageWrapper>
  );

  if (session) return (
    <PageWrapper subtitle="Acces Securise" title="Session active">
      <SessionStatus expiresAt={session.expiresAt} type={session.type} />

      <motion.div
        variants={fadeUp} initial="hidden" animate="visible"
        className="mt-6 rounded-2xl p-4 flex items-center gap-3"
        style={{ background: "rgba(255,178,0,0.08)", border: "1px solid rgba(255,178,0,0.20)" }}
      >
        <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
          style={{ background: "rgba(255,178,0,0.15)" }}>
          <Star size={20} color="#FFB200" fill="#FFB200" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-bold text-[#FFB200]">Gagnez des KGC-Spheres</div>
          <div className="text-xs text-[#FFFFF0]/55 leading-snug mt-0.5">
            Accomplissez des taches et retirez en USDT ou Mobile Money
          </div>
        </div>
        <Link to="/tasks">
          <ChevronRight size={18} color="#FFB200" />
        </Link>
      </motion.div>

      <div className="mt-4 flex flex-col gap-3">
        <Link to="/prime">
          <Button variant="ghost" fullWidth>
            <Crown size={18} /> Voir les plans Premium
          </Button>
        </Link>
      </div>
    </PageWrapper>
  );

  const btnLabel = !running
    ? (errorMsg ? "Reessayer" : "Commencer — Regarder la publicite")
    : "Publicite en cours...";

  return (
    <PageWrapper subtitle="Acces Securise">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible"
        className="flex flex-col items-center text-center">

        <motion.div variants={fadeUp} className="relative mb-5">
          <div className="absolute inset-0 rounded-full blur-2xl animate-glow-pulse"
            style={{ background: "radial-gradient(circle, rgba(0,136,204,0.35), transparent 70%)" }} />
          <div className="relative w-20 h-20 rounded-3xl flex items-center justify-center glass-blue">
            <Lock size={36} color="#0088CC" strokeWidth={2.2} />
          </div>
        </motion.div>

        <motion.h1 variants={fadeUp} className="font-bold text-3xl text-[#FFFFF0] mb-2 tracking-tight">
          Debloquer l'acces
        </motion.h1>
        <motion.p variants={fadeUp} className="text-[#FFFFF0]/55 max-w-xs mb-3 text-sm leading-relaxed">
          Regardez une publicite courte pour obtenir un acces gratuit aux fichiers
        </motion.p>
        <motion.div variants={fadeUp} className="mb-6">
          <Badge color="#22C55E">100% Gratuit</Badge>
        </motion.div>

        <motion.div variants={fadeUp} className="w-full mb-6 rounded-2xl p-3.5 flex items-center gap-3 text-left"
          style={{ background: "rgba(255,178,0,0.07)", border: "1px solid rgba(255,178,0,0.18)" }}>
          <Star size={18} color="#FFB200" fill="#FFB200" className="shrink-0" />
          <div className="flex-1 text-xs text-[#FFFFF0]/65 leading-relaxed">
            <span className="text-[#FFB200] font-semibold">Nouveau — </span>
            Gagnez des KGC-Spheres en accomplissant des taches et retirez en USDT ou Mobile Money.
          </div>
          <Link to="/tasks" className="shrink-0">
            <span className="text-xs text-[#FFB200] font-bold whitespace-nowrap">Voir les taches</span>
          </Link>
        </motion.div>

        <motion.div variants={fadeUp} className="w-full mb-6">
          <Card>
            {/* 1 seule étape visible : AdsGram */}
            <StepRow index={1} label="Publicite AdsGram" sublabel="Video recompensee" state={step1} />
          </Card>
        </motion.div>

        {errorMsg && (
          <motion.div variants={scaleIn} initial="hidden" animate="visible"
            className="w-full mb-4 px-4 py-3 rounded-xl text-sm text-[#EF4444] text-left"
            style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.20)" }}>
            {errorMsg}
          </motion.div>
        )}

        {success ? (
          <motion.div variants={scaleIn} initial="hidden" animate="visible" className="w-full flex flex-col gap-3">
            <Button variant="success" fullWidth size="lg">
              <CheckCircle2 size={20} />
              Acces debloque avec succes
            </Button>
            <p className="text-xs text-[#FFFFF0]/45 text-center leading-relaxed">
              Retournez au bot Telegram et cliquez sur le lien de votre fichier.
            </p>
          </motion.div>
        ) : (
          <motion.div variants={fadeUp} className="w-full">
            <Button fullWidth size="lg" loading={running} onClick={runFlow} disabled={running}>
              {btnLabel}
            </Button>
          </motion.div>
        )}

        <motion.div variants={fadeUp} className="w-full mt-8 flex items-center gap-3">
          <div className="flex-1 h-px bg-white/10" />
          <span className="text-xs text-[#FFFFF0]/40 tracking-widest font-semibold">OU</span>
          <div className="flex-1 h-px bg-white/10" />
        </motion.div>

        <motion.div variants={fadeUp} className="w-full mt-4">
          <Link to="/prime">
            <Button variant="ghost" fullWidth size="lg">
              <Crown size={18} /> Voir les plans Premium
            </Button>
          </Link>
        </motion.div>

      </motion.div>
    </PageWrapper>
  );
}

function StepRow({ index, label, sublabel, state }: {
  index: number; label: string; sublabel: string; state: StepState;
}) {
  const bg = state === "done" ? "#22C55E"
    : state === "running" ? "#0088CC"
    : state === "error" ? "#EF4444"
    : "rgba(255,255,255,0.05)";

  const stateLabel = { idle: "En attente", running: "En cours...", done: "Terminee", error: "Erreur" }[state];
  const stateColor = { idle: "rgba(255,255,240,0.35)", running: "#0088CC", done: "#22C55E", error: "#EF4444" }[state];

  return (
    <div className="flex items-center gap-3 py-1.5">
      <div className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 transition-all duration-300"
        style={{
          background: bg,
          border: state === "idle" ? "1px solid rgba(255,255,255,0.12)" : "none",
          boxShadow: state === "running" ? "0 0 12px rgba(0,136,204,0.5)"
            : state === "done" ? "0 0 12px rgba(34,197,94,0.4)" : "none",
        }}>
        {state === "done" ? <CheckCircle2 size={17} color="#fff" />
        : state === "running" ? <Loader2 size={16} className="animate-spin" color="#fff" />
        : state === "error" ? <span style={{ color: "#fff", fontSize: 15, fontWeight: 800 }}>!</span>
        : <Circle size={14} color="#FFFFF0" opacity={0.25} />}
      </div>
      <div className="flex-1 text-left">
        <div className="text-[11px] text-[#FFFFF0]/40 uppercase tracking-wider mb-0.5">Etape {index}</div>
        <div className="text-sm font-semibold text-[#FFFFF0]">{label}</div>
        <div className="text-xs text-[#FFFFF0]/40">{sublabel}</div>
      </div>
      <div className="text-xs font-semibold" style={{ color: stateColor }}>{stateLabel}</div>
    </div>
  );
}
