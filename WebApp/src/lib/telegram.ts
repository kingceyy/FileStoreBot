declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData?: string;
        initDataUnsafe?: {
          user?: {
            id: number;
            first_name?: string;
            last_name?: string;
            username?: string;
            language_code?: string;
            is_premium?: boolean;
            photo_url?: string;
          };
          start_param?: string;
          auth_date?: number;
          hash?: string;
        };
        close: () => void;
        expand: () => void;
        ready: () => void;
        showAlert: (message: string, callback?: () => void) => void;
        showConfirm: (message: string, callback: (confirmed: boolean) => void) => void;
        HapticFeedback?: {
          notificationOccurred: (type: "error" | "success" | "warning") => void;
          impactOccurred: (style: "light" | "medium" | "heavy" | "rigid" | "soft") => void;
        };
        colorScheme?: "light" | "dark";
        version?: string;
        platform?: string;
      };
    };
    show_11019878?: (type?: string) => Promise<void>;
  }
}

export function getTelegramUser() {
  try {
    return window.Telegram?.WebApp?.initDataUnsafe?.user ?? null;
  } catch {
    return null;
  }
}

export function getTelegramInitData(): string {
  try {
    return window.Telegram?.WebApp?.initData ?? "";
  } catch {
    return "";
  }
}

export function getStartParam(): string | undefined {
  try {
    return window.Telegram?.WebApp?.initDataUnsafe?.start_param ?? undefined;
  } catch {
    return undefined;
  }
}

/**
 * Lit les parametres d'URL.
 * Accepte "id_pubs" ET "pubs" (les deux formes utilisees par le bot).
 * Accepte "clone_id" ET "clone" pour le cloneId.
 */
export function getQueryParams() {
  if (typeof window === "undefined") {
    return { cloneId: undefined, idPubs: undefined };
  }
  const params = new URLSearchParams(window.location.search);
  // id_pubs est la cle canonique ; "pubs" est l'ancien alias
  const idPubs = params.get("id_pubs") || params.get("pubs") || undefined;
  // clone_id est la cle canonique ; "clone" est l'alias
  const cloneId = params.get("clone_id") || params.get("clone") || undefined;
  return { cloneId, idPubs };
}

export function closeWebApp() {
  try { window.Telegram?.WebApp?.close(); } catch {}
}

export function expandWebApp() {
  try {
    window.Telegram?.WebApp?.ready();
    window.Telegram?.WebApp?.expand();
  } catch {}
}

export function hapticSuccess() {
  try { window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred("success"); } catch {}
}

export function hapticError() {
  try { window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred("error"); } catch {}
}

export function hapticImpact(style: "light" | "medium" | "heavy" = "medium") {
  try { window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(style); } catch {}
}
