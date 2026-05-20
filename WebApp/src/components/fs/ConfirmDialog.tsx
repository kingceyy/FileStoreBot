import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, X } from "lucide-react";
import { useEffect, type ReactNode } from "react";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "danger" | "primary";
  loading?: boolean;
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = "Confirmer",
  cancelLabel = "Annuler",
  tone = "primary",
  loading = false,
}: Props) {
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, onClose]);

  const isDanger = tone === "danger";
  const accent = isDanger ? "#EF4444" : "#0088CC";
  const Icon = isDanger ? AlertTriangle : CheckCircle2;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="fixed inset-0 bg-black/65 backdrop-blur-sm z-[80]"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.94, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ type: "spring", damping: 24, stiffness: 320 }}
            className="fixed left-1/2 top-1/2 z-[90] w-[min(92vw,400px)] -translate-x-1/2 -translate-y-1/2"
          >
            <div
              className="rounded-3xl p-5 relative overflow-hidden"
              style={{
                background:
                  "linear-gradient(160deg, rgba(26,26,26,0.98), rgba(17,17,17,0.98))",
                border: `1px solid ${accent}33`,
                boxShadow: `0 20px 60px -20px ${accent}55, 0 0 0 1px rgba(255,255,255,0.04) inset`,
              }}
            >
              <div
                className="absolute -top-16 -right-16 w-40 h-40 rounded-full pointer-events-none"
                style={{
                  background: `radial-gradient(circle, ${accent}25, transparent 70%)`,
                }}
              />

              <button
                onClick={onClose}
                className="absolute top-3 right-3 p-1.5 rounded-xl text-white/50 hover:text-white hover:bg-white/10 transition-all active:scale-90"
                aria-label="Fermer"
              >
                <X size={16} />
              </button>

              <div className="flex items-start gap-3 relative">
                <div
                  className="w-11 h-11 rounded-2xl flex items-center justify-center shrink-0"
                  style={{
                    background: `${accent}1F`,
                    border: `1px solid ${accent}40`,
                  }}
                >
                  <Icon size={20} color={accent} />
                </div>
                <div className="flex-1 pt-0.5">
                  <h3 className="font-display text-base text-[#FFFFF0] leading-tight">
                    {title}
                  </h3>
                  {description && (
                    <p className="mt-1.5 text-xs text-[#FFFFF0]/65 leading-relaxed">
                      {description}
                    </p>
                  )}
                </div>
              </div>

              <div className="mt-5 flex gap-2">
                <button
                  onClick={onClose}
                  disabled={loading}
                  className="flex-1 h-11 rounded-xl text-sm font-semibold text-[#FFFFF0] transition-all active:scale-[0.97] disabled:opacity-50"
                  style={{
                    background: "rgba(255,255,255,0.06)",
                    border: "1px solid rgba(255,255,255,0.10)",
                  }}
                >
                  {cancelLabel}
                </button>
                <button
                  onClick={onConfirm}
                  disabled={loading}
                  className="flex-1 h-11 rounded-xl text-sm font-bold transition-all active:scale-[0.97] disabled:opacity-60"
                  style={{
                    background: isDanger
                      ? "linear-gradient(135deg,#EF4444,#b91c1c)"
                      : "linear-gradient(135deg,#0088CC,#005f8f)",
                    color: "#FFFFF0",
                    boxShadow: `0 8px 24px -8px ${accent}80`,
                  }}
                >
                  {confirmLabel}
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
