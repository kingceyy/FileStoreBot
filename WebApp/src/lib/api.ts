const BASE_URL = (import.meta.env.VITE_API_URL as string) || "https://yumeflowerbot.koyeb.app";

async function call<T = any>(
  path: string,
  method: "GET" | "POST" = "POST",
  body?: object
): Promise<T> {
  try {
    let url = `${BASE_URL}${path}`;
    const opts: RequestInit = {
      method,
      headers: { "Content-Type": "application/json" },
    };

    if (method === "GET" && body) {
      const params = new URLSearchParams();
      Object.entries(body).forEach(([k, v]) => {
        if (v !== undefined && v !== null) params.append(k, String(v));
      });
      if (params.toString()) url += `?${params.toString()}`;
    } else if (body) {
      opts.body = JSON.stringify(body);
    }

    console.log(`[API Call] ${method} ${url}`, body);

    const res = await fetch(url, opts);

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      console.error(`[API Error] ${path}:`, err);
      return { success: false, error: err?.error || `HTTP ${res.status}` } as T;
    }
    return await res.json();
  } catch (e) {
    console.error(`[API Catch] ${path}:`, e);
    return { success: false, error: String(e) } as T;
  }
}

// ─── Sessions & Ads ───────────────────────────────────────────────────────────
export async function checkSession(userId: number, cloneId?: string, idPubs?: string) {
  return call("/api/check-session", "POST", {
    user_id: userId,
    clone_id: cloneId,
    id_pubs: idPubs,
  });
}

export async function watchAd(userId: number, cloneId?: string, idPubs?: string) {
  return call("/api/watch-ad", "POST", {
    user_id: userId,
    clone_id: cloneId,
    id_pubs: idPubs || "YUMEFLOWER",
  });
}

// ─── Tasks & Profile ─────────────────────────────────────────────────────────
export async function getTasks(userId: number) {
  return call("/api/tasks", "GET", { user_id: userId });
}

export async function claimTask(userId: number, taskId: string) {
  return call("/api/tasks/claim", "POST", {
    user_id: userId,
    task_id: taskId,
  });
}

export async function getUserProfile(userId: number) {
  return call("/api/user/profile", "GET", { user_id: userId });
}

// ─── User Withdrawal ─────────────────────────────────────────────────────────
export async function requestUserWithdrawal(
  userId: number,
  amount: number,
  method: string,
  accountInfo: string
) {
  return call("/api/user/withdraw", "POST", {
    user_id: userId,
    amount,
    method,
    address: accountInfo,
  });
}

// ─── Clone / Maître ───────────────────────────────────────────────────────────
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
  return call("/api/master/withdraw", "POST", {
    id_code: idCode,
    amount,
    method,
    account_info: accountInfo,
  });
}

export async function regenerateIds(idCode: string) {
  return call("/api/regenerate-ids", "POST", { id_code: idCode });
}

// ─── Admin Functions ─────────────────────────────────────────────────────────
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
    reason: reason || "Rejeté par l'administrateur",
  });
}

export async function addManualTask(title: string, description: string, reward: number, url?: string) {
  return call("/api/admin/tasks/add", "POST", {
    title,
    description,
    reward_kgc: reward,
    url,
  });
}

export async function deleteTask(taskId: string) {
  return call("/api/admin/tasks/delete", "POST", { task_id: taskId });
}

export async function getUserWithdrawals() {
  return call<any>("/api/admin/user-withdrawals", "GET");
}

export async function approveUserWithdrawal(withdrawalId: string) {
  return call("/api/admin/approve-user-withdrawal", "POST", { withdrawal_id: withdrawalId });
}

export async function rejectUserWithdrawal(withdrawalId: string, reason?: string) {
  return call("/api/admin/reject-user-withdrawal", "POST", {
    withdrawal_id: withdrawalId,
    reason: reason || "Rejeté par l'administrateur",
  });
}

export async function adminConfig(_token: string, freeDuration: number) {
  return call("/api/admin/config", "POST", { free_duration: freeDuration });
}
