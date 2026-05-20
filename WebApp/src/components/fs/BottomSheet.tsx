import { AnimatePresence, motion } from "framer-motion";
import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
}

export function BottomSheet({ isOpen, onClose, title, children }: Props) {
  // Cache la navbar quand le sheet est ouvert
  useEffect(() => {
    document.body.setAttribute("data-sheet", isOpen ? "open" : "closed");
    return () => {
      document.body.setAttribute("data-sheet", "closed");
    };
  }, [isOpen]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60]"
            onClick={onClose}
          />

          {/* Sheet */}
          <motion.div
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 300 }}
            className="fixed bottom-0 left-0 right-0 z-[70] bg-[#111111] border-t border-white/10 rounded-t-3xl max-h-[90vh] overflow-y-auto"
            style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
          >
            {/* Header sticky */}
            <div className="sticky top-0 bg-[#111111] pt-3 pb-2 z-10">
              <div className="mx-auto h-1.5 w-12 rounded-full bg-white/20" />
              {title && (
                <div className="flex items-center justify-between px-5 pt-3">
                  <h3 className="font-bold text-lg text-[#FFFFF0]">{title}</h3>
                  <button
                    onClick={onClose}
                    className="p-1.5 rounded-xl text-white/60 hover:text-white hover:bg-white/10 transition-all active:scale-90"
                  >
                    <X size={20} />
                  </button>
                </div>
              )}
            </div>

            <div className="px-5 pb-6 pt-2">{children}</div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
