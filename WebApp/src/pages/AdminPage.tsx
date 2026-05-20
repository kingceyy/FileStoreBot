/**
 * AdminPage — Dashboard Owner complet avec gestion users, retraits maîtres & users
 */
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import {
  Shield, Users, Bot, Zap, DollarSign,
  Search, LogOut, Check, X, RefreshCw, Star,
  Plus, Trash2, ChevronDown, ChevronUp, Eye, TrendingUp, Clock
} from "lucide-react";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Button } from "@/components/fs/Button";
import { Card } from "@/components/fs/Card";
import { Badge } from "@/components/fs/Badge";
import { BottomSheet } from "@/components/fs/BottomSheet";
import { ToastProvider, useToast } from "@/components/fs/Toast";
import { fadeUp, staggerContainer } from "@/lib/animations";
import {
  adminConfig, approveWithdrawal, creditClone,
  getAdminClones, getAdminStats, rejectWithdrawal,
  addManualTask, deleteTask, getUserWithdrawals,
  approveUserWithdrawal, rejectUserWithdrawal, getAdminUsers
} from "@/lib/api";

const ADMIN_PASSWORD = "m@cabre";
const STORAGE_KEY    = "fs_admin_token";

export function AdminPage() {
  return <ToastProvider><AdminInner /></ToastProvider>;
}

function AdminInner() {
  const [authed,  setAuthed]  = useState(false);
  const [pwd,     setPwd]     = useState("");
  const [loading, setLoading] = useState(false);
  const [shake,   setShake]   = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    if (sessionStorage.getItem(STORAGE_KEY) === "ok") setAuthed(true);
  }, []);

  const submit = () => {
    if (!pwd.trim()) return;
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      if (pwd === ADMIN_PASSWORD) {
        sessionStorage.setItem(STORAGE_KEY, "ok");
        setAuthed(true);
      } else {
        setShake(true);
        setTimeout(() => setShake(false), 500);
        toast("Mot de passe incorrect.", "error");
        setPwd("");
      }
    }, 500);
  };

  const logout = () => {
    sessionStorage.removeItem(STORAGE_KEY);
    setAuthed(false);
    setPwd("");
  };

  if (authed) return <AdminDashboard onLogout={logout} />;

  return (
    <PageWrapper subtitle="Administration">
      <motion.div initial="hidden" animate="visible" variants={staggerContainer}
        className="flex flex-col items-center text-center pt-8">

        <motion.div variants={fadeUp} className="relative mb-5">
          <div className="absolute inset-0 rounded-full blur-2xl animate-glow-pulse"
            style={{ background: "radial-gradient(circle,rgba(255,178,0,0.35),transparent 70%)" }} />
          <div className="relative w-16 h-16 rounded-2xl flex items-center justify-center"
            style={{ background: "rgba(255,178,0,0.10)", border: "1px solid rgba(255,178,0,0.30)" }}>
            <Shield size={28} color="#FFB200" />
          </div>
        </motion.div>

        <motion.h1 variants={fadeUp} className="font-bold text-3xl text-[#FFFFF0] mb-2 tracking-tight">
          Administration
        </motion.h1>
        <motion.p variants={fadeUp} className="text-sm text-[#FFFFF0]/55 mb-8">
          Accès réservé au propriétaire
        </motion.p>

        <motion.div variants={fadeUp} className={`w-full ${shake ? "animate-shake" : ""}`}>
          <input
            type="password"
            value={pwd}
            onChange={(e) => setPwd(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            placeholder="Mot de passe owner"
            className="w-full h-12 px-4 bg-[#111111] border border-white/10 rounded-xl text-[#FFFFF0] focus:border-[#FFB200] outline-none mb-4 transition-colors"
          />
          <Button variant="gold" fullWidth size="lg" onClick={submit} loading={loading}>
            Connexion
          </Button>
        </motion.div>
      </motion.div>
    </PageWrapper>
  );
}

type Tab = "stats" | "clones" | "withdrawals" | "user_withdrawals" | "users" | "tasks" | "config";

function AdminDashboard({ onLogout }: { onLogout: () => void }) {
  const [tab,          setTab]          = useState<Tab>("stats");
  const [stats,        setStats]        = useState<any>(null);
  const [clones,       setClones]       = useState<any[]>([]);
  const [users,        setUsers]        = useState<any[]>([]);
  const [userWithdrawals, setUserWithdrawals] = useState<any[]>([]);
  const [search,       setSearch]       = useState("");
  const [freeDuration, setFreeDuration] = useState(10);
  const [loadingId,    setLoadingId]    = useState<string | null>(null);
  const [taskSheet,    setTaskSheet]    = useState(false);
  const [newTask,      setNewTask]      = useState({ title: "", description: "", reward: "", url: "" });
  const { toast } = useToast();

  const reload = async () => {
    const [s, c, u, uw] = await Promise.all([
      getAdminStats("local"),
      getAdminClones("local"),
      getAdminUsers(),
      getUserWithdrawals(),
    ]);
    if (s) setStats(s);
    setClones(Array.isArray(c) ? c : (c?.clones ?? []));
    setUsers(Array.isArray(u) ? u : (u?.users ?? []));
    setUserWithdrawals(Array.isArray(uw) ? uw : (uw?.withdrawals ?? []));
  };

  useEffect(() => { reload(); }, []);

  const pending: any[] = stats?.pending_withdrawals ?? [];
  const pendingUsers    = userWithdrawals.filter((w: any) => w.status === "pending");

  // ── Retraits maîtres ─────────────────────────────────────────────────────────
  const handleApprove = async (w: any) => {
    setLoadingId(w.id);
    const res = await approveWithdrawal(w.id);
    setLoadingId(null);
    if (res?.success) { toast("Retrait maître approuvé.", "success"); reload(); }
    else toast(res?.error || "Erreur.", "error");
  };

  const handleReject = async (w: any) => {
    setLoadingId(`r_${w.id}`);
    const res = await rejectWithdrawal(w.id, "Refusé par l'owner.");
    setLoadingId(null);
    if (res?.success) { toast("Retrait maître refusé.", "error"); reload(); }
    else toast(res?.error || "Erreur.", "error");
  };

  // ── Retraits utilisateurs ─────────────────────────────────────────────────────
  const handleApproveUser = async (w: any) => {
    setLoadingId(`ua_${w.id}`);
    const res = await approveUserWithdrawal(w.id);
    setLoadingId(null);
    if (res?.success) { toast("Retrait utilisateur approuvé.", "success"); reload(); }
    else toast(res?.error || "Erreur.", "error");
  };

  const handleRejectUser = async (w: any) => {
    setLoadingId(`ur_${w.id}`);
    const res = await rejectUserWithdrawal(w.id, "Refusé par l'owner.");
    setLoadingId(null);
    if (res?.success) { toast("Retrait utilisateur refusé.", "error"); reload(); }
    else toast(res?.error || "Erreur.", "error");
  };

  // ── Créditer un clone ─────────────────────────────────────────────────────────
  const handleCredit = async (c: any) => {
    const v = prompt(`Montant à créditer au bot @${c.username} ($) :`);
    if (!v) return;
    const amt = parseFloat(v);
    if (isNaN(amt) || amt <= 0) { toast("Montant invalide.", "error"); return; }
    const res = await creditClone("local", c.id, amt);
    toast(res?.success ? `$${amt} crédité sur @${c.username}` : "Erreur lors du crédit.", res?.success ? "success" : "error");
    reload();
  };

  // ── Tâches ────────────────────────────────────────────────────────────────────
  const handleAddTask = async () => {
    if (!newTask.title || !newTask.reward) {
      toast("Titre et récompense requis.", "error");
      return;
    }
    const res = await addManualTask(newTask.title, newTask.description, parseFloat(newTask.reward), newTask.url);
    if (res?.success) {
      toast("Tâche ajoutée.", "success");
      setNewTask({ title: "", description: "", reward: "", url: "" });
      setTaskSheet(false);
    } else {
      toast(res?.error || "Erreur.", "error");
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    const res = await deleteTask(taskId);
    if (res?.success) { toast("Tâche supprimée.", "success"); reload(); }
    else toast(res?.error || "Erreur.", "error");
  };

  const handleSaveConfig = async () => {
    const res = await adminConfig("local", freeDuration);
    toast(res?.success !== false ? "Configuration sauvegardée." : "Erreur lors de la sauvegarde.", res?.success !== false ? "success" : "error");
  };

  const filteredClones = clones.filter((c) =>
    !search ||
    (c.username ?? "").toLowerCase().includes(search.toLowerCase()) ||
    (c.id_pubs ?? "").toLowerCase().includes(search.toLowerCase()) ||
    (c.id_code ?? "").toLowerCase().includes(search.toLowerCase())
  );

  const TABS: { key: Tab; label: string; badge?: number }[] = [
    { key: "stats",            label: "Stats" },
    { key: "clones",           label: "Bots",       badge: clones.length },
    { key: "withdrawals",      label: "Retraits",   badge: pending.length },
    { key: "user_withdrawals", label: "Users KGC",  badge: pendingUsers.length },
    { key: "users",            label: "Membres",    badge: users.length },
    { key: "tasks",            label: "Tâches" },
    { key: "config",           label: "Config" },
  ];

  return (
    <PageWrapper subtitle="Owner Dashboard">

      {/* Tabs */}
      <div className="flex gap-1.5 mb-5 overflow-x-auto pb-1 no-scrollbar">
        {TABS.map(({ key, label, badge }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className="shrink-0 flex items-center gap-1.5 h-8 px-3 rounded-lg text-xs font-bold transition-all active:scale-95"
            style={{
              background: tab === key ? "#FFB200" : "rgba(255,255,255,0.06)",
              color:      tab === key ? "#0A0A0A" : "rgba(255,255,240,0.55)",
            }}>
            {label}
            {badge !== undefined && badge > 0 && (
              <span className="w-4 h-4 rounded-full text-[9px] flex items-center justify-center"
                style={{ background: tab === key ? "rgba(0,0,0,0.25)" : "#EF4444", color: "#fff" }}>
                {badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── Onglet Stats ──────────────────────────────────────────────────────── */}
      {tab === "stats" && (
        <motion.div initial="hidden" animate="visible" variants={staggerContainer}>
          <div className="grid grid-cols-2 gap-3 mb-5">
            <StatCard icon={Users}      color="#0088CC" label="Utilisateurs"   value={(stats?.total_users ?? 0).toLocaleString("fr-FR")} />
            <StatCard icon={Bot}        color="#FFB200" label="Bots actifs"     value={stats?.active_clones ?? clones.length} />
            <StatCard icon={Zap}        color="#22C55E" label="Sessions actives" value={stats?.active_sessions ?? 0} />
            <StatCard icon={DollarSign} color="#EF4444" label="Revenus totaux"  value={`$${(stats?.total_revenue ?? 0).toFixed?.(2) ?? "0.00"}`} />
            <StatCard icon={Eye}        color="#9333EA" label="Impressions"     value={(stats?.total_impressions ?? 0).toLocaleString?.("fr-FR") ?? 0} />
            <StatCard icon={TrendingUp} color="#F59E0B" label="Sessions prem."  value={stats?.premium_sessions ?? 0} />
          </div>

          {/* Graphique 7 jours */}
          <Card className="mb-4">
            <h3 className="font-bold text-sm text-[#FFFFF0] mb-4">Impressions — 7 derniers jours</h3>
            <BarChart data={stats?.daily_impressions ?? Array.from({ length: 7 }, () => 0)} />
            <div className="flex justify-between text-xs text-[#FFFFF0]/45 mt-3">
              <span>Sessions gratuites : {stats?.free_sessions ?? 0}</span>
              <span>Premium : {stats?.premium_sessions ?? 0}</span>
            </div>
          </Card>
        </motion.div>
      )}

      {/* ── Onglet Bots clonés ────────────────────────────────────────────────── */}
      {tab === "clones" && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="relative mb-4">
            <Search size={15} color="#ffffff60" className="absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Rechercher par username, ID_PUBS, ID_CODE..."
              className="w-full h-11 pl-9 pr-3 rounded-xl text-[#FFFFF0] text-sm outline-none"
              style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.10)" }}
            />
          </div>

          <div className="flex flex-col gap-3">
            {filteredClones.length === 0 && (
              <div className="text-center py-10 text-[#FFFFF0]/40 text-sm">Aucun bot trouvé.</div>
            )}
            {filteredClones.map((c, i) => (
              <Card key={i}>
                <div className="flex items-center justify-between mb-2">
                  <div className="font-bold text-sm text-[#FFFFF0]">@{c.username ?? "—"}</div>
                  <Badge color={c.active ? "#22C55E" : "#EF4444"}>
                    {c.active ? "Actif" : "Inactif"}
                  </Badge>
                </div>
                <div className="text-[10px] text-[#FFFFF0]/40 font-mono mb-1">
                  PUBS: {c.id_pubs} · CODE: {c.id_code}
                </div>
                <div className="flex justify-between text-xs text-[#FFFFF0]/55 mb-3">
                  <span>Solde : <strong className="text-[#FFB200]">${(c.balance ?? 0).toFixed(2)}</strong></span>
                  <span>Impressions : {(c.impressions ?? 0).toLocaleString("fr-FR")}</span>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" fullWidth variant="gold" onClick={() => handleCredit(c)}>
                    Créditer
                  </Button>
                  <Button size="sm" variant="ghost" fullWidth
                    onClick={() => toast("Contrôle à connecter au bot via /ban clone_id", "info")}>
                    Détails
                  </Button>
                </div>
              </Card>
            ))}
          </div>

          <div className="mt-4 text-center">
            <button onClick={reload} className="flex items-center gap-2 text-sm text-[#FFFFF0]/45 hover:text-[#FFFFF0] mx-auto transition-colors">
              <RefreshCw size={14} /> Actualiser
            </button>
          </div>
        </motion.div>
      )}

      {/* ── Onglet Retraits Maîtres ───────────────────────────────────────────── */}
      {tab === "withdrawals" && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-base text-[#FFFFF0]">Retraits maîtres</h3>
            <button onClick={reload} className="active:scale-90 transition-all">
              <RefreshCw size={16} color="rgba(255,255,240,0.4)" />
            </button>
          </div>

          {pending.length === 0 && (
            <div className="text-center py-12 text-[#FFFFF0]/40">
              <Check size={32} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">Aucun retrait en attente.</p>
            </div>
          )}

          <div className="flex flex-col gap-3">
            {pending.map((w: any) => (
              <WithdrawalCard
                key={w.id}
                w={w}
                onApprove={() => handleApprove(w)}
                onReject={() => handleReject(w)}
                loadingApprove={loadingId === w.id}
                loadingReject={loadingId === `r_${w.id}`}
              />
            ))}
          </div>
        </motion.div>
      )}

      {/* ── Onglet Retraits Utilisateurs KGC ─────────────────────────────────── */}
      {tab === "user_withdrawals" && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-base text-[#FFFFF0]">Retraits KGC-Sphères</h3>
            <button onClick={reload} className="active:scale-90 transition-all">
              <RefreshCw size={16} color="rgba(255,255,240,0.4)" />
            </button>
          </div>

          {/* Info */}
          <div className="mb-4 rounded-xl px-4 py-3 flex gap-2 items-start"
            style={{ background: "rgba(0,136,204,0.07)", border: "1px solid rgba(0,136,204,0.15)" }}>
            <Clock size={14} color="#0088CC" className="shrink-0 mt-0.5" />
            <p className="text-xs text-[#FFFFF0]/60 leading-relaxed">
              Retraits traités les <strong>mardi et samedi</strong>. Mobile Money via @JessiKaPayBot (1 USDT = 500 XOF). USDT TRC-20 direct.
            </p>
          </div>

          {pendingUsers.length === 0 && (
            <div className="text-center py-10 text-[#FFFFF0]/40 text-sm">Aucun retrait utilisateur en attente.</div>
          )}

          <div className="flex flex-col gap-3">
            {userWithdrawals.map((w: any, i: number) => (
              <Card key={i}>
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="font-bold text-sm text-[#FFFFF0]">
                      {w.first_name ?? `User ${w.user_id}`}
                    </div>
                    {w.username && <div className="text-xs text-[#FFFFF0]/45">@{w.username}</div>}
                    <div className="text-[10px] text-[#FFFFF0]/35 font-mono mt-0.5">ID: {w.user_id}</div>
                  </div>
                  <Badge
                    color={w.status === "approved" ? "#22C55E" : w.status === "rejected" ? "#EF4444" : "#F59E0B"}>
                    {w.status === "approved" ? "Approuvé" : w.status === "rejected" ? "Refusé" : "En attente"}
                  </Badge>
                </div>

                <div className="text-xs text-[#FFFFF0]/60 mb-0.5">
                  Méthode : <strong>{w.method === "mobile_money" ? "Mobile Money (JessiKaPay)" : "USDT TRC-20"}</strong>
                </div>
                <div className="text-xs text-[#FFFFF0]/60 font-mono mb-1">
                  Adresse : {w.address}
                </div>
                <div className="flex justify-between text-xs mb-3">
                  <span className="text-[#FFB200] font-bold">{w.amount_usdt?.toFixed?.(3) ?? w.amount_usdt} USDT</span>
                  {w.method === "mobile_money" && (
                    <span className="text-[#FFFFF0]/45">
                      ≈ {Math.floor((w.amount_usdt ?? 0) * 500).toLocaleString("fr-FR")} XOF
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-[#FFFFF0]/35 mb-3">
                  Demandé le : {(w.requested_at ?? "")?.slice?.(0, 16)?.replace?.("T", " ") ?? "—"}
                </div>

                {w.status === "pending" && (
                  <div className="flex gap-2">
                    <Button size="sm" variant="success" fullWidth
                      loading={loadingId === `ua_${w.id}`}
                      onClick={() => handleApproveUser(w)}>
                      <Check size={14} /> Approuver
                    </Button>
                    <Button size="sm" variant="danger" fullWidth
                      loading={loadingId === `ur_${w.id}`}
                      onClick={() => handleRejectUser(w)}>
                      <X size={14} /> Refuser
                    </Button>
                  </div>
                )}
              </Card>
            ))}
          </div>
        </motion.div>
      )}

      {/* ── Onglet Membres ───────────────────────────────────────────────────── */}
      {tab === "users" && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <h3 className="font-bold text-base text-[#FFFFF0] mb-4">
            Membres ({users.length})
          </h3>
          <div className="flex flex-col gap-2 max-h-[60vh] overflow-y-auto">
            {users.length === 0 && (
              <div className="text-center py-10 text-[#FFFFF0]/40 text-sm">Aucun membre pour l'instant.</div>
            )}
            {users.map((u: any, i: number) => (
              <div key={i} className="rounded-xl p-3 flex items-center gap-3"
                style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)" }}>
                <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
                  style={{ background: "rgba(0,136,204,0.12)" }}>
                  <Users size={16} color="#0088CC" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-sm text-[#FFFFF0] truncate">
                    {u.first_name ?? "Utilisateur"}
                    {u.username && <span className="text-[#FFFFF0]/45 font-normal ml-1">@{u.username}</span>}
                  </div>
                  <div className="text-[10px] text-[#FFFFF0]/35 font-mono">ID: {u.user_id ?? u.id}</div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-xs font-bold text-[#FFB200]">{u.balance_kgc ?? 0} KGC</div>
                  <div className="text-[10px] text-[#FFFFF0]/35">{u.tasks_completed ?? 0} tâches</div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* ── Onglet Tâches ─────────────────────────────────────────────────────── */}
      {tab === "tasks" && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-base text-[#FFFFF0]">Tâches</h3>
            <Button size="sm" variant="gold" onClick={() => setTaskSheet(true)}>
              <Plus size={14} /> Ajouter
            </Button>
          </div>

          <div className="mb-3 rounded-xl px-4 py-3 flex gap-2 items-start"
            style={{ background: "rgba(255,178,0,0.07)", border: "1px solid rgba(255,178,0,0.18)" }}>
            <Star size={14} color="#FFB200" className="shrink-0 mt-0.5" />
            <p className="text-xs text-[#FFFFF0]/60 leading-relaxed">
              Les tâches AdsGram (blockId: <code className="text-[#0088CC]">task-30433</code>) et Monetag (zone: <code className="text-[#0088CC]">11019878</code>) sont configurées côté WebApp. Ajoutez ici des tâches manuelles supplémentaires.
            </p>
          </div>

          <div className="text-center py-10 text-[#FFFFF0]/40 text-sm">
            <Star size={28} className="mx-auto mb-3 opacity-30" />
            <p>Les tâches manuelles s'affichent ici.</p>
            <p className="text-xs mt-1">Cliquez sur "Ajouter" pour créer une tâche.</p>
          </div>
        </motion.div>
      )}

      {/* ── Onglet Config ─────────────────────────────────────────────────────── */}
      {tab === "config" && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="mb-4">
            <h3 className="font-bold text-base text-[#FFFFF0] mb-4">Configuration globale</h3>
            <ConfigInput
              label="Durée de session gratuite (minutes)"
              value={freeDuration}
              onChange={(v) => setFreeDuration(v)}
              onSave={handleSaveConfig}
            />
          </Card>

          <Card className="mb-4">
            <h3 className="font-bold text-sm text-[#FFFFF0] mb-3">Identifiants publicitaires</h3>
            <div className="flex flex-col gap-2 text-xs text-[#FFFFF0]/60">
              <div className="flex justify-between">
                <span>AdsGram Block ID</span>
                <code className="text-[#0088CC]">task-30433</code>
              </div>
              <div className="flex justify-between">
                <span>Monetag Zone</span>
                <code className="text-[#0088CC]">11019878</code>
              </div>
            </div>
          </Card>

          <Card>
            <h3 className="font-bold text-sm text-[#FFFFF0] mb-3">Informations</h3>
            <div className="flex flex-col gap-2 text-xs text-[#FFFFF0]/55 leading-relaxed">
              <div>Taux KGC : <strong className="text-[#FFB200]">1 KGC-Sphère = 0.001 USDT</strong></div>
              <div>Retrait minimum users : <strong className="text-[#FFB200]">3 USDT</strong></div>
              <div>Taux Mobile Money : <strong className="text-[#FFB200]">1 USDT = 500 XOF</strong></div>
              <div>Jours de retrait : <strong>Mardi & Samedi</strong></div>
            </div>
          </Card>
        </motion.div>
      )}

      <button
        onClick={onLogout}
        className="w-full text-center text-sm text-[#FFFFF0]/35 py-6 flex items-center justify-center gap-2 hover:text-[#FFFFF0] transition-colors mt-4">
        <LogOut size={14} /> Déconnexion
      </button>

      {/* Sheet : Ajouter une tâche manuelle */}
      <BottomSheet isOpen={taskSheet} onClose={() => setTaskSheet(false)} title="Nouvelle tâche manuelle">
        <div className="flex flex-col gap-3 pb-4">
          <input
            type="text"
            placeholder="Titre de la tâche"
            value={newTask.title}
            onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
            className="w-full h-11 px-3 rounded-xl text-sm text-[#FFFFF0] outline-none"
            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)" }}
          />
          <textarea
            placeholder="Description (optionnel)"
            value={newTask.description}
            onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
            rows={2}
            className="w-full px-3 py-2.5 rounded-xl text-sm text-[#FFFFF0] resize-none outline-none"
            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)" }}
          />
          <input
            type="number"
            placeholder="Récompense en KGC-Sphères"
            value={newTask.reward}
            onChange={(e) => setNewTask({ ...newTask, reward: e.target.value })}
            className="w-full h-11 px-3 rounded-xl text-sm text-[#FFFFF0] outline-none"
            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)" }}
          />
          <input
            type="url"
            placeholder="Lien de la tâche (optionnel)"
            value={newTask.url}
            onChange={(e) => setNewTask({ ...newTask, url: e.target.value })}
            className="w-full h-11 px-3 rounded-xl text-sm text-[#FFFFF0] font-mono outline-none"
            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)" }}
          />
          <Button fullWidth variant="gold" onClick={handleAddTask}>
            <Plus size={16} /> Ajouter la tâche
          </Button>
        </div>
      </BottomSheet>
    </PageWrapper>
  );
}

function WithdrawalCard({ w, onApprove, onReject, loadingApprove, loadingReject }: {
  w: any; onApprove: () => void; onReject: () => void; loadingApprove: boolean; loadingReject: boolean;
}) {
  return (
    <Card>
      <div className="flex justify-between items-start mb-2">
        <div className="font-bold text-sm text-[#FFFFF0]">@{w.username ?? "—"}</div>
        <div className="font-bold text-[#FFB200]">${w.amount?.toFixed?.(2) ?? w.amount}</div>
      </div>
      <div className="text-xs text-[#FFFFF0]/55 mb-0.5">
        Méthode : {w.method} · {w.account_info}
      </div>
      <div className="text-[10px] text-[#FFFFF0]/35 mb-3">{w.date}</div>
      <div className="flex gap-2">
        <Button size="sm" variant="success" fullWidth loading={loadingApprove} onClick={onApprove}>
          <Check size={14} /> Approuver
        </Button>
        <Button size="sm" variant="danger" fullWidth loading={loadingReject} onClick={onReject}>
          <X size={14} /> Refuser
        </Button>
      </div>
    </Card>
  );
}

function StatCard({ icon: Icon, color, label, value }: { icon: any; color: string; label: string; value: any }) {
  return (
    <motion.div variants={fadeUp}
      className="glass p-4 rounded-2xl"
      style={{ border: `1px solid ${color}22` }}>
      <Icon size={18} color={color} />
      <div className="font-bold text-xl text-[#FFFFF0] mt-2 truncate">{value}</div>
      <div className="text-xs text-[#FFFFF0]/50 uppercase tracking-wider mt-0.5">{label}</div>
    </motion.div>
  );
}

function BarChart({ data }: { data: number[] }) {
  const max = Math.max(...data, 1);
  return (
    <div className="flex items-end justify-between gap-1.5 h-24">
      {data.map((v, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1">
          <div className="w-full rounded-t-md transition-all"
            style={{
              height: `${(v / max) * 100}%`,
              minHeight: 4,
              background: "linear-gradient(180deg,#0088CC,#005f8f)",
            }} />
          <div className="text-[10px] text-[#FFFFF0]/35">J{i + 1}</div>
        </div>
      ))}
    </div>
  );
}

function ConfigInput({ label, value, onChange, onSave }: {
  label: string; value: number; onChange: (n: number) => void; onSave: () => void;
}) {
  return (
    <div className="mb-4">
      <label className="block text-xs text-[#FFFFF0]/45 uppercase tracking-wider mb-2 font-semibold">{label}</label>
      <div className="flex gap-2">
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="flex-1 h-11 px-3 rounded-xl text-[#FFFFF0] text-sm outline-none"
          style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)" }}
        />
        <Button size="sm" onClick={onSave}>OK</Button>
      </div>
    </div>
  );
}
