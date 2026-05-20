/**
 * Gestion locale des moyens de paiement enregistrés par l'utilisateur.
 * Stockés dans localStorage — n'interfère avec aucun appel API.
 *
 * UNIQUEMENT JessiKaPay : les gains KGC sont versés via JessiKaPay
 * sur un compte au format JP-XXXXXX.
 */

export type PaymentType = "jkpay";

export interface SavedPaymentMethod {
  id: string;
  type: PaymentType;
  label: string;
  /** Numéro JessiKaPay au format JP-XXXXXX */
  address: string;
  createdAt: number;
}

const KEY = (userId: number | string) => `kgc:payment_methods:${userId}`;

/** Valide un numéro JessiKaPay (JP- suivi de 4 caractères alphanum minimum). */
export function isValidJpNumber(addr: string): boolean {
  return /^JP-[A-Z0-9]{4,}$/i.test(addr.trim());
}

/** Normalise un numéro JessiKaPay en majuscules. */
export function normalizeJpNumber(addr: string): string {
  return addr.trim().toUpperCase();
}

export function loadPaymentMethods(
  userId: number | string,
): SavedPaymentMethod[] {
  if (!userId) return [];
  try {
    const raw = localStorage.getItem(KEY(userId));
    if (!raw) return [];
    const list = JSON.parse(raw);
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

export function savePaymentMethod(
  userId: number | string,
  method: Omit<SavedPaymentMethod, "id" | "createdAt">,
): SavedPaymentMethod {
  const list = loadPaymentMethods(userId);
  const entry: SavedPaymentMethod = {
    ...method,
    address: normalizeJpNumber(method.address),
    id: `pm_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`,
    createdAt: Date.now(),
  };
  list.unshift(entry);
  try {
    localStorage.setItem(KEY(userId), JSON.stringify(list.slice(0, 10)));
  } catch {
    /* ignore quota */
  }
  return entry;
}

export function deletePaymentMethod(userId: number | string, id: string) {
  const list = loadPaymentMethods(userId).filter((m) => m.id !== id);
  try {
    localStorage.setItem(KEY(userId), JSON.stringify(list));
  } catch {
    /* ignore quota */
  }
  return list;
}
