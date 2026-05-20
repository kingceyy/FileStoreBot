import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, AlertCircle, Info } from "lucide-react";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type Variant = "success" | "error" | "info";
interface ToastItem { id: number; msg: string; variant: Variant }

const ToastCtx = createContext<{ toast: (msg: string, v?: Variant) => void } | null>(null);

export function useToast() {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const toast = useCallback((msg: string, variant: Variant = "info") => {
    const id = Date.now() + Math.random();
    setItems((prev) => [...prev, { id, msg, variant }]);
    setTimeout(() => setItems((p) => p.filter((i) => i.id !== id)), 3000);
  }, []);

  const colors: Record<Variant, string> = {
    success: "#22C55E",
    error: "#EF4444",
    info: "#0088CC",
  };
  const Icon = (v: Variant) => (v === "success" ? CheckCircle2 : v === "error" ? AlertCircle : Info);

  return (
    <ToastCtx.Provider value={{ toast }}>
      {children}
      <div className="fixed top-4 left-0 right-0 z-[100] flex flex-col items-center gap-2 px-4 pointer-events-none">
        <AnimatePresence>
          {items.map((it) => {
            const I = Icon(it.variant);
            return (
              <motion.div
                key={it.id}
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="glass flex items-center gap-3 px-4 py-3 max-w-sm w-full"
                style={{ borderColor: `${colors[it.variant]}40` }}
              >
                <I size={20} color={colors[it.variant]} />
                <span className="text-sm text-[#FFFFF0]">{it.msg}</span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastCtx.Provider>
  );
}
