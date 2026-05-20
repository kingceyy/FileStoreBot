import { useCallback, useEffect, useRef } from "react";

interface ShowPromiseResult {
  done: boolean;
  description: string;
  state: "load" | "render" | "playing" | "destroy";
  error: boolean;
}

interface AdController {
  show(): Promise<ShowPromiseResult>;
  destroy(): void;
}

declare global {
  interface Window {
    Adsgram?: {
      init(params: { blockId: string; debug?: boolean }): AdController;
    };
    show_10971920?: () => Promise<void>;
  }
}

interface UseAdsgramOptions {
  blockId: string;
  onReward: () => void;
  onError?: (result: unknown) => void;
}

/**
 * Hook AdsGram — intégration officielle
 * API : window.Adsgram.init({ blockId }).show()
 * SDK : <script src="https://sad.adsgram.ai/js/sad.min.js" async></script>
 */
export function useAdsgram({ blockId, onReward, onError }: UseAdsgramOptions) {
  const controllerRef = useRef<AdController | undefined>(undefined);

  useEffect(() => {
    // Initialiser le controller dès que le SDK est disponible
    if (window.Adsgram) {
      controllerRef.current = window.Adsgram.init({ blockId, debug: false });
    }
  }, [blockId]);

  const show = useCallback(async () => {
    if (!controllerRef.current) {
      // SDK pas encore chargé — réessayer une fois après 500ms
      await new Promise((r) => setTimeout(r, 500));
      if (window.Adsgram) {
        controllerRef.current = window.Adsgram.init({ blockId, debug: false });
      }
    }

    if (controllerRef.current) {
      try {
        await controllerRef.current.show();
        onReward();
      } catch (result) {
        onError?.(result);
      }
    } else {
      onError?.({
        error: true,
        done: false,
        state: "load",
        description: "AdsGram SDK non chargé",
      });
    }
  }, [blockId, onReward, onError]);

  return { show };
}
