/**
 * MasterPage — Dashboard des maîtres de bots clonés
 * Corrections : verify-code fix, retraits clarifiés, broadcast amélioré
 */
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import {
  Key, Eye, Wallet, Zap, TrendingUp, Send, Settings,
  RefreshCw, LogOut, AlertTriangle, ToggleLeft, ToggleRight, Clock,
  Copy, CheckCircle2, AlertCircle, ChevronDown, ChevronUp
} from "lucide-react";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Button } from "@/components/fs/Button";
import { Card } from "@/components/fs/Card";
import { Badge } from "@/components/fs/Badge";
import { BottomSheet } from "@/components/fs/BottomSheet";
import { ToastProvider, useToast } from "@/components/fs/Toast";
import { fadeUp, staggerContainer } from "@/lib/animations";
import { getMasterStats, requestWithdrawal, verifyCode } from "@/lib/api";

const BASE_URL = (import.meta.env.VITE_API_URL as string) || "https://waramugi.vercel.app";
const STORAGE_KEY = "fs_master_code";

async function masterConfig(idCode: string, payload: { ads_enabled?: boolean; session_duration?: number }) {
  try {
    const res = await fetch(`${BASE_URL}/api/master-config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id_code: idCode, ...payload }),
    });
    return await res.json();
  } catch (e) {
    return { success: false, error: String(e) };
  }
}

async function masterBroadcast(idCode: string, msg: string) {
  try {
    const res = await fetch(`${BASE_URL}/api/master-broadcast`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id_code: idCode, message: msg }),
    });
    return await res.json();
  } catch (e) {
    return { success: false, error: String(e) };
  }
}

async function regenerateIds(idCode: string) {
  try {
    const res = await fetch(`${BASE_URL}/api/regenerate-ids`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id_code: idCode }),
    });
    return await res.json();
  } catch (e) {
    return { success: false, error: String(e) };
  }
}

function durationLabel(minutes: number): string {
  if (minutes >= 1440) {
    const d = Math.floor(minutes / 1440);
    const h = Math.floor((minutes % 1440) / 60);
    return h ? `${d}j ${h}h` : `${d} jour${d > 1 ? "s" : ""}`;
  }
  if (minutes >= 60) {
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return m ? `${h}h ${m}min` : `${h}h`;
  }
  return `${minutes} min`;
}

export function MasterPage() {
  return (
    <ToastProvider>
      <MasterInner />
    </ToastProvider>
  );
}

function MasterInner() {
  const [code,    setCode]    = useState<string | null>(null);
  const [input,   setInput]   = useState("");
  const [error,   setError]   = useState(false);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    const saved = sessionStorage.getItem(STORAGE_KEY);
    if (saved) setCode(saved);
  }, []);

  const submit = async () => {
    const val = input.trim().toUpperCase();
    if (val.length !== 8) {
      setError(true);
      setTimeout(() => setError(false), 500);
      return;
    }
    setLoading(true);
    const res = await verifyCode(val);
    setLoading(false);
    // verifyCode retourne { valid: true, ... } en cas de succès
    if (res?.valid === true) {
      sessionStorage.setItem(STORAGE_KEY, val);
      setCode(val);
    } else {
      setError(true);
      setTimeout(() => setError(false), 500);
      const errMsg = res?.error === "ID_CODE introuvable"
        ? "ID_CODE introuvable. Vérifiez la casse et les caractères."
        : "ID_CODE invalide. Vérifiez votre code dans /gestion.";
      toast(errMsg, "error");
    }
  };

  if (code) return (
    <MasterDashboard
      code={code}
      onLogout={() => { sessionStorage.removeItem(STORAGE_KEY); setCode(null); setInput(""); }}
    />
  );

  return (
    <PageWrapper subtitle="Espace Maître">
      <motion.div initial="hidden" animate="visible" variants={staggerContainer}
        className="flex flex-col items-center text-center pt-8">

        <motion.div variants={fadeUp} className="relative mb-5">
          <div className="absolute inset-0 rounded-full blur-2xl animate-glow-pulse"
            style={{ background: "radial-gradient(circle,rgba(0,136,204,0.35),transparent 70%)" }} />
          <div className="relative w-16 h-16 rounded-2xl glass-blue flex items-center justify-center">
            <Key size={28} color="#0088CC" />
          </div>
        </motion.div>

        <motion.h1 variants={fadeUp} className="font-bold text-3xl text-[#FFFFF0] mb-2 tracking-tight">
          Espace Maître
        </motion.h1>
        <motion.p variants={fadeUp} className="text-sm text-[#FFFFF0]/55 mb-2 max-w-xs leading-relaxed">
          Entrez votre <b>ID_CODE</b> à 8 caractères pour accéder à votre dashboard.
        </motion.p>
        <motion.p variants={fadeUp} className="text-xs text-[#FFFFF0]/35 mb-8 max-w-xs">
          Retrouvez votre ID_CODE en tapant <code className="text-[#0088CC]">/gestion</code> dans votre bot.
        </motion.p>

        <motion.div variants={fadeUp} className={`w-full ${error ? "animate-shake" : ""}`}>
          <input
            type="text"
            maxLength={8}
            value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""))}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            placeholder="XXXXXXXX"
            className="w-full h-14 text-center text-2xl font-bold tracking-[0.5em] bg-[#111111] border border-white/10 rounded-xl text-[#FFFFF0] focus:border-[#0088CC] outline-none mb-2 transition-colors"
          />
          {error && (
            <div className="text-[#EF4444] text-xs mb-3 flex items-center justify-center gap-1">
              <AlertCircle size={13} /> Code introuvable. Vérifiez et réessayez.
            </div>
          )}
        </motion.div>

        <motion.div variants={fadeUp} className="w-full mt-2">
          <Button onClick={submit} loading={loading} fullWidth size="lg">Accéder</Button>
        </motion.div>
      </motion.div>
    </PageWrapper>
  );
}

function MasterDashboard({ code, onLogout }: { code: string; onLogout: () => void }) {
  const [stats,       setStats]       = useState<any>(null);
  const [amount,      setAmount]      = useState("");
  const [method,      setMethod]      = useState<"usdt_ton" | "stars">("usdt_ton");
  const [account,     setAccount]     = useState("");
  const [broadcast,   setBroadcast]   = useState("");
  const [adsEnabled,  setAdsEnabled]  = useState(true);
  const [sessionDur,  setSessionDur]  = useState(30);
  const [customDur,   setCustomDur]   = useState("");
  const [durSheet,    setDurSheet]    = useState(false);
  const [regenSheet,  setRegenSheet]  = useState(false);
  const [withdrawSheet, setWithdrawSheet] = useState(false);
  const [newIds,      setNewIds]      = useState<{ id_pubs: string; id_code: string } | null>(null);
  const [loading,     setLoading]     = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [copied,      setCopied]      = useState<string | null>(null);
  const { toast } = useToast();

  const reload = () => {
    getMasterStats(code).then((d) => {
      if (d?.success || d?.id_pubs || d?.bot_username) {
        setStats(d);
        setAdsEnabled(d?.ads_enabled ?? true);
        setSessionDur(d?.session_duration ?? 30);
      }
    });
  };

  useEffect(() => { reload(); }, [code]);

  const copy = (text: string, key: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(key);
      setTimeout(() => setCopied(null), 2000);
      toast("Copié dans le presse-papiers", "success");
    }).catch(() => {});
  };

  const toggleAds = async () => {
    const next = !adsEnabled;
    setAdsEnabled(next);
    const res = await masterConfig(code, { ads_enabled: next });
    if (res?.success) {
      toast(`Publicités ${next ? "activées" : "désactivées"}`, "success");
    } else {
      setAdsEnabled(!next);
      toast("Erreur de mise à jour. Réessayez.", "error");
    }
  };

  const saveDuration = async (minutes: number) => {
    if (minutes < 1) { toast("Minimum : 1 minute", "error"); return; }
    const res = await masterConfig(code, { session_duration: minutes });
    if (res?.success) {
      setSessionDur(minutes);
      setDurSheet(false);
      toast(`Durée mise à jour : ${durationLabel(minutes)}`, "success");
    } else {
      toast("Erreur de mise à jour. Réessayez.", "error");
    }
  };

  const submitWithdraw = async () => {
    const amt = parseFloat(amount);
    if (!amt || amt < (stats?.min_withdrawal ?? 7)) {
      toast(`Montant minimum : $${stats?.min_withdrawal ?? 7}`, "error");
      return;
    }
    if (amt > (stats?.balance ?? 0)) {
      toast("Montant supérieur à votre solde.", "error");
      return;
    }
    if (method === "usdt_ton" && !account.trim()) {
      toast("Renseignez votre adresse TON.", "error");
      return;
    }
    setLoading("withdraw");
    const res = await requestWithdrawal(code, amt, method, method === "usdt_ton" ? account.trim() : "");
    setLoading(null);
    if (res?.success) {
      toast("Demande de retrait envoyée. Traitement sous 24-48h.", "success");
      setAmount("");
      setAccount("");
      setWithdrawSheet(false);
      reload();
    } else {
      toast(res?.error || "Erreur lors de la demande. Réessayez.", "error");
    }
  };

  const sendBroadcast = async () => {
    if (!broadcast.trim()) { toast("Écrivez un message avant d'envoyer.", "error"); return; }
    setLoading("broadcast");
    const res = await masterBroadcast(code, broadcast.trim());
    setLoading(null);
    if (res?.success) {
      toast("Broadcast mis en file d'attente. Envoi en cours...", "success");
      setBroadcast("");
    } else {
      toast(res?.error || "Erreur lors du broadcast.", "error");
    }
  };

  const doRegen = async () => {
    setLoading("regen");
    const res = await regenerateIds(code);
    setLoading(null);
    if (res?.success) {
      setNewIds({ id_pubs: res.new_id_pubs, id_code: res.new_id_code });
      setRegenSheet(false);
      toast("IDs régénérés. Notez vos nouveaux identifiants !", "success");
      sessionStorage.removeItem(STORAGE_KEY);
    } else {
      toast(res?.error || "Erreur lors de la régénération.", "error");
    }
  };

  const PRESETS = [5, 10, 15, 30, 60, 120, 180, 360, 720, 1440];
  const balance = stats?.balance ?? 0;
  const minW    = stats?.min_withdrawal ?? 7;

  return (
    <PageWrapper subtitle="Dashboard Maître">

      {/* Nouveaux IDs après régénération */}
      {newIds && (
        <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }}
          className="mb-4 rounded-2xl p-4"
          style={{ background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.25)" }}>
          <div className="text-sm font-bold text-[#22C55E] mb-2 flex items-center gap-2">
            <CheckCircle2 size={16} /> Nouveaux identifiants générés
          </div>
          <div className="text-xs text-[#FFFFF0]/70 mb-1 font-mono">
            ID_PUBS : <span className="text-[#0088CC] font-bold">{newIds.id_pubs}</span>
            <button onClick={() => copy(newIds.id_pubs, "pubs")} className="ml-2 opacity-60 hover:opacity-100">
              <Copy size={12} color={copied === "pubs" ? "#22C55E" : "#FFFFF0"} />
            </button>
          </div>
          <div className="text-xs text-[#FFFFF0]/70 font-mono">
            ID_CODE : <span className="text-[#FFB200] font-bold">{newIds.id_code}</span>
            <button onClick={() => copy(newIds.id_code, "code")} className="ml-2 opacity-60 hover:opacity-100">
              <Copy size={12} color={copied === "code" ? "#22C55E" : "#FFFFF0"} />
            </button>
          </div>
          <p className="text-[10px] text-[#FFFFF0]/40 mt-2">
            Connectez-vous avec votre nouveau ID_CODE.
          </p>
        </motion.div>
      )}

      {/* Identité bot */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <Card className="mb-4">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <div className="text-xs text-[#FFFFF0]/40 uppercase tracking-wider mb-1">Bot cloné</div>
              <div className="font-bold text-lg text-[#FFFFF0] truncate">@{stats?.bot_username ?? "—"}</div>
            </div>
            <Badge color="#22C55E">Actif</Badge>
          </div>
          <div className="flex flex-wrap gap-2 mt-3">
            <button
              onClick={() => copy(stats?.id_pubs ?? "", "idpubs")}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition-all active:scale-95"
              style={{ background: "rgba(0,136,204,0.12)", border: "1px solid rgba(0,136,204,0.25)", color: "#0088CC" }}>
              {copied === "idpubs" ? <CheckCircle2 size={11} /> : <Copy size={11} />}
              ID_PUBS: {stats?.id_pubs ?? "—"}
            </button>
            <button
              onClick={() => copy(code, "idcode")}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition-all active:scale-95"
              style={{ background: "rgba(255,178,0,0.10)", border: "1px solid rgba(255,178,0,0.25)", color: "#FFB200" }}>
              {copied === "idcode" ? <CheckCircle2 size={11} /> : <Copy size={11} />}
              ID_CODE: {code}
            </button>
          </div>
        </Card>
      </motion.div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <StatCard icon={Eye}         color="#0088CC" label="Impressions" value={(stats?.stats?.total_impressions ?? 0).toLocaleString("fr-FR")} sub="Total" />
        <StatCard icon={Wallet}      color="#FFB200" label="Solde"       value={`$${balance.toFixed(2)}`} sub="Disponible" />
        <StatCard icon={Zap}         color="#22C55E" label="Sessions"    value={stats?.stats?.active_sessions ?? 0} sub="Actives" />
        <StatCard icon={TrendingUp}  color="#EF4444" label="CPM"         value={`$${(stats?.cpm_rate ?? 0).toFixed(2)}`} sub="/ 1000 imp" />
      </div>

      {/* Contrôles */}
      <Card className="mb-4">
        <h3 className="font-bold text-base text-[#FFFFF0] mb-3 flex items-center gap-2">
          <Settings size={16} color="#0088CC" /> Configuration
        </h3>
        <div className="flex flex-col gap-4">
          {/* Toggle pubs */}
          <div className="flex items-center justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-[#FFFFF0]">Publicités requises</div>
              <div className="text-xs text-[#FFFFF0]/40 leading-snug mt-0.5">
                {adsEnabled
                  ? "Les utilisateurs voient des pubs pour accéder aux fichiers."
                  : "Accès direct — vous ne générez plus de revenus."}
              </div>
            </div>
            <button onClick={toggleAds} className="active:scale-90 transition-all shrink-0">
              {adsEnabled
                ? <ToggleRight size={40} color="#22C55E" />
                : <ToggleLeft  size={40} color="#EF4444" />}
            </button>
          </div>

          <div className="h-px bg-white/08" />

          {/* Durée session */}
          <div className="flex items-center justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-[#FFFFF0]">Durée de session</div>
              <div className="text-xs text-[#FFFFF0]/40 mt-0.5">Accès accordé après visionnage</div>
            </div>
            <button
              onClick={() => setDurSheet(true)}
              className="flex items-center gap-2 px-3 py-2 rounded-xl active:scale-95 transition-all shrink-0"
              style={{ background: "rgba(0,136,204,0.10)", border: "1px solid rgba(0,136,204,0.25)" }}>
              <Clock size={14} color="#0088CC" />
              <span className="text-sm font-bold text-[#0088CC]">{durationLabel(sessionDur)}</span>
            </button>
          </div>
        </div>
      </Card>

      {/* Retrait */}
      <Card className="mb-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-bold text-base text-[#FFFFF0] flex items-center gap-2">
            <Wallet size={16} color="#FFB200" /> Mes revenus
          </h3>
          <Badge color="#FFB200">${balance.toFixed(2)}</Badge>
        </div>
        <div className="text-xs text-[#FFFFF0]/40 mb-4 leading-relaxed">
          CPM actuel : <strong>${(stats?.cpm_rate ?? 0).toFixed(2)}</strong> / 1000 impressions.
          Minimum de retrait : <strong>${minW}</strong>.
        </div>
        <Button
          fullWidth
          disabled={balance < minW}
          onClick={() => setWithdrawSheet(true)}
          variant={balance >= minW ? "gold" : "ghost"}
        >
          <Wallet size={16} />
          {balance >= minW ? `Retirer $${balance.toFixed(2)}` : `Minimum $${minW} requis`}
        </Button>

        {/* Historique */}
        {(stats?.recent_withdrawals ?? []).length > 0 && (
          <div className="mt-4">
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="flex items-center gap-1.5 text-xs text-[#FFFFF0]/50 hover:text-[#FFFFF0] transition-colors w-full">
              {showHistory ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              Historique ({(stats?.recent_withdrawals ?? []).length} retraits)
            </button>
            {showHistory && (
              <div className="mt-3 flex flex-col gap-2">
                {(stats?.recent_withdrawals ?? []).map((w: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-xl"
                    style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)" }}>
                    <div>
                      <div className="text-xs font-semibold text-[#FFFFF0]">
                        ${w.amount?.toFixed?.(2) ?? w.amount} · {w.method?.toUpperCase?.() ?? w.method}
                      </div>
                      <div className="text-[10px] text-[#FFFFF0]/40">
                        {(w.requested_at ?? w.date ?? "")?.slice?.(0, 10) ?? "—"}
                      </div>
                    </div>
                    <Badge
                      color={w.status === "approved" ? "#22C55E" : w.status === "rejected" ? "#EF4444" : "#F59E0B"}>
                      {w.status === "approved" ? "Approuvé" : w.status === "rejected" ? "Refusé" : "En attente"}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Broadcast */}
      <Card className="mb-4">
        <h3 className="font-bold text-base text-[#FFFFF0] mb-1 flex items-center gap-2">
          <Send size={16} color="#0088CC" /> Broadcast
        </h3>
        <p className="text-xs text-[#FFFFF0]/45 mb-3 leading-relaxed">
          Envoyez un message à tous les utilisateurs de votre bot.
        </p>
        <textarea
          rows={4}
          value={broadcast}
          onChange={(e) => setBroadcast(e.target.value)}
          placeholder="Message à diffuser à tous vos utilisateurs..."
          className="w-full px-3 py-2.5 rounded-xl text-sm text-[#FFFFF0] mb-3 resize-none outline-none transition-colors"
          style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.10)" }}
        />
        <Button fullWidth loading={loading === "broadcast"} onClick={sendBroadcast}>
          Diffuser le message
        </Button>
      </Card>

      {/* Gestion des IDs */}
      <Card className="mb-4">
        <h3 className="font-bold text-base text-[#FFFFF0] mb-3 flex items-center gap-2">
          <RefreshCw size={16} color="#0088CC" /> Identifiants
        </h3>
        <div className="flex flex-col gap-2 mb-3 text-xs text-[#FFFFF0]/60 leading-relaxed">
          <div>
            <span className="text-[#FFFFF0]/40">ID_PUBS</span> — à intégrer dans votre WebApp pour identifier les revenus de votre bot.
          </div>
          <div>
            <span className="text-[#FFFFF0]/40">ID_CODE</span> — confidentiel, pour accéder à ce dashboard.
          </div>
        </div>
        <Button variant="ghost" fullWidth onClick={() => setRegenSheet(true)}>
          <RefreshCw size={15} /> Régénérer mes identifiants
        </Button>
        <div className="mt-3 flex gap-2 items-start p-3 rounded-xl"
          style={{ background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.15)" }}>
          <AlertTriangle size={14} color="#EF4444" className="shrink-0 mt-0.5" />
          <p className="text-xs text-[#FFFFF0]/55 leading-snug">
            Les anciens identifiants cesseront de fonctionner immédiatement après régénération.
          </p>
        </div>
      </Card>

      <button
        onClick={onLogout}
        className="w-full text-center text-sm text-[#FFFFF0]/35 py-5 hover:text-[#FFFFF0] flex items-center justify-center gap-2 transition-colors">
        <LogOut size={14} /> Déconnexion
      </button>

      {/* Sheet : Durée de session */}
      <BottomSheet isOpen={durSheet} onClose={() => setDurSheet(false)} title="Durée de session">
        <p className="text-sm text-[#FFFFF0]/60 mb-4 leading-relaxed">
          Combien de temps dure l'accès gratuit après qu'un utilisateur ait regardé une publicité ?
        </p>
        <div className="grid grid-cols-3 gap-2 mb-4">
          {PRESETS.map((p) => (
            <button key={p} onClick={() => saveDuration(p)}
              className="py-2.5 rounded-xl text-sm font-bold transition-all active:scale-95"
              style={{
                background: sessionDur === p ? "#0088CC" : "rgba(255,255,255,0.06)",
                color:      sessionDur === p ? "#fff"    : "rgba(255,255,240,0.65)",
                border:     sessionDur === p ? "none"    : "1px solid rgba(255,255,255,0.08)",
              }}>
              {durationLabel(p)}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            type="number"
            value={customDur}
            onChange={(e) => setCustomDur(e.target.value)}
            placeholder="Personnalisé (minutes)"
            className="flex-1 h-11 px-3 rounded-xl text-[#FFFFF0] text-sm outline-none"
            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)" }}
          />
          <Button onClick={() => {
            const v = parseInt(customDur);
            if (v > 0) saveDuration(v);
            else toast("Valeur invalide. Entrez un nombre supérieur à 0.", "error");
          }}>
            OK
          </Button>
        </div>
      </BottomSheet>

      {/* Sheet : Retrait */}
      <BottomSheet isOpen={withdrawSheet} onClose={() => setWithdrawSheet(false)} title="Demande de retrait">
        <p className="text-sm text-[#FFFFF0]/60 mb-4 leading-relaxed">
          Solde disponible : <strong className="text-[#FFB200]">${balance.toFixed(2)}</strong>. Minimum : <strong>${minW}</strong>.
        </p>

        <div className="mb-3">
          <label className="block text-xs text-[#FFFFF0]/45 uppercase tracking-wider mb-2 font-semibold">
            Méthode
          </label>
          <div className="flex gap-2">
            {(["usdt_ton", "stars"] as const).map((m) => (
              <button key={m} onClick={() => setMethod(m)}
                className="flex-1 h-11 rounded-xl text-sm font-bold uppercase tracking-wider transition-all active:scale-95"
                style={{
                  background: method === m ? "#0088CC" : "rgba(255,255,255,0.05)",
                  color:      method === m ? "#fff"    : "rgba(255,255,240,0.55)",
                  border:     method === m ? "none"    : "1px solid rgba(255,255,255,0.10)",
                }}>
                {m === "usdt_ton" ? "USDT (TON)" : "Telegram Stars"}
              </button>
            ))}
          </div>
        </div>

        <div className="mb-3">
          <label className="block text-xs text-[#FFFFF0]/45 uppercase tracking-wider mb-2 font-semibold">
            Montant ($)
          </label>
          <input
            type="number"
            placeholder={`Min $${minW}`}
            value={amount}
            min={minW}
            max={balance}
            step="0.01"
            onChange={(e) => setAmount(e.target.value)}
            className="w-full h-12 px-3 rounded-xl text-[#FFFFF0] text-sm outline-none"
            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)" }}
          />
        </div>

        {method === "usdt_ton" && (
          <div className="mb-4">
            <label className="block text-xs text-[#FFFFF0]/45 uppercase tracking-wider mb-2 font-semibold">
              Adresse TON
            </label>
            <input
              type="text"
              placeholder="UQxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
              value={account}
              onChange={(e) => setAccount(e.target.value)}
              className="w-full h-12 px-3 rounded-xl text-[#FFFFF0] text-sm font-mono outline-none"
              style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)" }}
            />
          </div>
        )}
        {method === "stars" && (
          <p className="text-xs text-[#FFFFF0]/45 mb-4 leading-relaxed">
            Vos Telegram Stars seront envoyées directement à votre compte Telegram (aucune adresse requise).
          </p>
        )}

        <Button fullWidth loading={loading === "withdraw"} onClick={submitWithdraw} variant="gold">
          Confirmer la demande
        </Button>
        <p className="text-xs text-[#FFFFF0]/35 text-center mt-2">
          Traitement sous 24-48h par l'administrateur.
        </p>
      </BottomSheet>

      {/* Sheet : Confirmation régénération */}
      <BottomSheet isOpen={regenSheet} onClose={() => setRegenSheet(false)} title="Régénérer les identifiants">
        <p className="text-sm text-[#FFFFF0]/70 leading-relaxed mb-4">
          Un nouveau <strong>ID_PUBS</strong> et un nouveau <strong>ID_CODE</strong> seront générés.<br /><br />
          Les anciens identifiants seront immédiatement invalides. Vous devrez mettre à jour votre WebApp avec le nouveau ID_PUBS.
        </p>
        <div className="flex gap-2">
          <Button variant="danger" fullWidth loading={loading === "regen"} onClick={doRegen}>
            Confirmer
          </Button>
          <Button variant="ghost" fullWidth onClick={() => setRegenSheet(false)}>
            Annuler
          </Button>
        </div>
      </BottomSheet>

    </PageWrapper>
  );
}

function StatCard({ icon: Icon, color, label, value, sub }: {
  icon: any; color: string; label: string; value: any; sub: string;
}) {
  return (
    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
      className="glass p-4 rounded-2xl"
      style={{ border: `1px solid ${color}22` }}>
      <Icon size={18} color={color} />
      <div className="font-bold text-xl text-[#FFFFF0] mt-2 truncate">{value}</div>
      <div className="text-xs text-[#FFFFF0]/55 uppercase tracking-wider mt-0.5">{label}</div>
      <div className="text-[10px] text-[#FFFFF0]/30 mt-0.5">{sub}</div>
    </motion.div>
  );
}
