import { Link, useLocation } from "@tanstack/react-router";
import { Home, Crown, Key, Shield, User } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";

const ITEMS = [
  { to: "/",       label: "Accueil",  icon: Home   },
  { to: "/prime",  label: "Premium",  icon: Crown  },
  { to: "/profile",label: "Profil",   icon: User   },
  { to: "/master", label: "Maître",   icon: Key    },
  { to: "/admin",  label: "Admin",    icon: Shield },
] as const;

export function BottomNav() {
  const { pathname } = useLocation();
  const [sheetOpen, setSheetOpen] = useState(false);

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setSheetOpen(document.body.getAttribute("data-sheet") === "open");
    });
    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ["data-sheet"],
    });
    return () => observer.disconnect();
  }, []);

  // Cacher la nav sur la page /tasks (non visible dans la navbar)
  const hiddenPaths = ["/tasks"];
  if (hiddenPaths.includes(pathname)) return null;

  return (
    <AnimatePresence>
      {!sheetOpen && (
        <motion.nav
          key="bottom-nav"
          initial={{ y: 80, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 80, opacity: 0 }}
          transition={{ type: "spring", damping: 22, stiffness: 260 }}
          className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[480px] z-50 px-3 pb-3 pt-2"
          style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
        >
          <div className="glass flex items-center justify-around rounded-2xl px-1 py-2 relative">
            {ITEMS.map(({ to, label, icon: Icon }) => {
              const active = pathname === to;
              return (
                <Link
                  key={to}
                  to={to}
                  preload="intent"
                  className="flex-1 relative flex flex-col items-center gap-0.5 py-1.5 rounded-xl transition-colors active:scale-90"
                  style={{ color: active ? "#0088CC" : "rgba(255,255,240,0.45)" }}
                >
                  {active && (
                    <motion.div
                      layoutId="nav-active-pill"
                      transition={{ type: "spring", damping: 24, stiffness: 320 }}
                      className="absolute inset-0 rounded-xl"
                      style={{
                        background: "rgba(0,136,204,0.12)",
                        boxShadow:
                          "0 4px 16px -6px rgba(0,136,204,0.5), inset 0 0 0 1px rgba(0,136,204,0.22)",
                      }}
                    />
                  )}
                  <motion.div
                    animate={active ? { scale: 1.08, y: -1 } : { scale: 1, y: 0 }}
                    transition={{ type: "spring", damping: 18, stiffness: 320 }}
                    className="relative z-10"
                  >
                    <Icon size={19} strokeWidth={active ? 2.6 : 2} />
                  </motion.div>
                  <span className="text-[10px] font-semibold relative z-10 leading-none">{label}</span>
                </Link>
              );
            })}
          </div>
        </motion.nav>
      )}
    </AnimatePresence>
  );
}
