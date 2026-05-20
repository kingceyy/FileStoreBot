// URL du backend Koyeb
// Priorité : variable d'env Vite > fallback hardcodé
const BASE_URL = (
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "")
  ?? "https://yumeflower.koyeb.app"
);

async function call<T = any>(
  path: string,
  method: "GET" | "POST" = "POST",
  body?: object
): Promise<T> {
  try {
    const opts: RequestInit = {
      method,
      headers: { "Content-Type": "application/json" },
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${BASE_URL}${path}`, opts);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return { success: false, error: err?.error || `HTTP ${res.status}` } as T;
    }
    return await res.json();
  } catch (e) {
    return { success: false, error: String(e) } as T;
  }
}

// ─── Sessions ─────────────────────────────────────────────────────────────────

/**
 * Verifie la session active.
 * - Si idPubs est fourni (bot clone) → /api/check-session-clone
 * - Sinon (bot mere) → /api/check-session
 * Retourne un objet normalise : { active, expires_at, type, time_left }
 */
export async function checkSession(userId: number, cloneId?: string, idPubs?: string) {
  if (idPubs) {
    const res = await call<any>("/api/check-session-clone", "POST", {
      user_id: userId,
      id_pubs: idPubs,
    });
    // Normaliser la reponse clone vers le format attendu par IndexPage
    return {
      active:     res?.has_access ?? false,
      expires_at: res?.expires_at ?? null,
      type:       res?.type ?? "free",
      time_left:  res?.time_left ?? 0,
      success:    res?.success ?? false,
    };
  }
  // Bot mere
  const res = await call<any>("/api/check-session", "POST", {
    user_id:  userId,
    clone_id: cloneId,
  });
  return {
    active:     res?.has_access ?? false,
    expires_at: res?.expires_at ?? null,
    type:       res?.type ?? "free",
    time_left:  res?.time_left ?? 0,
  };
}

/**
 * Enregistre une pub vue et cree la session.
 * - Si idPubs est fourni (bot clone) → /api/watch-ad-clone
 * - Sinon (bot mere) → /api/watch-ad
 */
export async function watchAd(userId: number, cloneId?: string, idPubs?: string) {
  if (idPubs) {
    return call("/api/watch-ad-clone", "POST", {
      user_id: userId,
      id_pubs: idPubs,
    });
  }
  return call("/api/watch-ad", "POST", {
    user_id:  userId,
    clone_id: cloneId,
  });
}

// ─── Clone / Maitre ───────────────────────────────────────────────────────────

export async function verifyPubs(idPubs: string) {
  return call("/api/verify-pubs", "POST", { id_pubs: idPubs });
}

export async function verifyCode(idCode: string) {
  return call("/api/verify-code", "POST", { id_code: idCode });
}

export async function getMasterStats(idCode: string) {
  return call<any>(`/api/master-stats?id_code=${idCode}`, "GET");
}

export async function updateMasterConfig(
  idCode: string,
  payload: { ads_enabled?: boolean; session_duration?: number }
) {
  return call("/api/master-config", "POST", { id_code: idCode, ...payload });
}

export async function sendMasterBroadcast(idCode: string, message: string) {
  return call("/api/master-broadcast", "POST", { id_code: idCode, message });
}

export async function requestWithdrawal(
  idCode: string,
  amount: number,
  method: string,
  accountInfo: string
) {
  return call("/api/request-withdrawal", "POST", {
    id_code:      idCode,
    amount,
    method,
    account_info: accountInfo,
  });
}

export async function regenerateIds(idCode: string) {
  return call("/api/regenerate-ids", "POST", { id_code: idCode });
}

// ─── Taches & Gains utilisateur ──────────────────────────────────────────────

export async function getUserProfile(userId: number) {
  return call<any>(`/api/user/profile?user_id=${userId}`, "GET");
}

export async function getTasks(userId: number) {
  return call<any>(`/api/tasks?user_id=${userId}`, "GET");
}

export async function claimTask(userId: number, taskId: string) {
  return call("/api/tasks/claim", "POST", { user_id: userId, task_id: taskId });
}

export async function requestUserWithdrawal(
  userId: number,
  amount: number,
  method: "mobile_money" | "usdt_trc20",
  address: string
) {
  return call("/api/user/withdraw", "POST", { user_id: userId, amount, method, address });
}

// ─── Admin / Owner ────────────────────────────────────────────────────────────

export async function adminLogin(password: string) {
  return call("/api/admin/login", "POST", { password });
}

export async function getAdminStats(_token: string) {
  return call<any>("/api/admin/stats", "GET");
}

export async function getAdminClones(_token: string) {
  return call<any>("/api/admin/clones", "GET");
}

export async function getAdminUsers() {
  return call<any>("/api/admin/users", "GET");
}

export async function creditClone(_token: string, cloneId: string, amount: number) {
  return call("/api/admin/credit", "POST", { clone_id: cloneId, amount });
}

export async function approveWithdrawal(withdrawalId: string) {
  return call("/api/admin/approve-withdrawal", "POST", { withdrawal_id: withdrawalId });
}

export async function rejectWithdrawal(withdrawalId: string, reason?: string) {
  return call("/api/admin/reject-withdrawal", "POST", {
    withdrawal_id: withdrawalId,
    reason:        reason || "Rejete par l'administrateur",
  });
}

export async function approveUserWithdrawal(withdrawalId: string) {
  return call("/api/admin/approve-user-withdrawal", "POST", { withdrawal_id: withdrawalId });
}

export async function rejectUserWithdrawal(withdrawalId: string, reason?: string) {
  return call("/api/admin/reject-user-withdrawal", "POST", {
    withdrawal_id: withdrawalId,
    reason:        reason || "Rejete par l'administrateur",
  });
}

export async function adminConfig(_token: string, freeDuration: number) {
  return call("/api/admin/config", "POST", { free_duration: freeDuration });
}

export async function addManualTask(title: string, description: string, reward: number, url: string) {
  return call("/api/admin/tasks/add", "POST", { title, description, reward_kgc: reward, url });
}

export async function deleteTask(taskId: string) {
  return call("/api/admin/tasks/delete", "POST", { task_id: taskId });
}

export async function getUserWithdrawals() {
  return call<any>("/api/admin/user-withdrawals", "GET");
}
