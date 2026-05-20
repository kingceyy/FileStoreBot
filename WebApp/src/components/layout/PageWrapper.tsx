import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { Zap } from "lucide-react";
import { useLocation } from "@tanstack/react-router";
import { BottomNav } from "@/components/layout/BottomNav";

export function PageWrapper({ children, title, subtitle }: { children: ReactNode; title?: string; subtitle?: string }) {
  const { pathname } = useLocation();
  return (
    <>
      <motion.main
        key={pathname}
        initial={{ opacity: 0, y: 14, filter: "blur(6px)" }}
        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
        className="min-h-screen w-full max-w-[480px] mx-auto px-5 pt-6 pb-28 relative"
      >
        <motion.header
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.05 }}
          className="flex items-center gap-2.5 mb-8"
        >
          <motion.div
            whileHover={{ rotate: -8, scale: 1.05 }}
            whileTap={{ scale: 0.92 }}
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: "linear-gradient(135deg,#0088CC,#005f8f)", boxShadow: "0 8px 24px -8px rgba(0,136,204,0.6)" }}
          >
            <Zap size={20} color="#FFFFF0" fill="#FFFFF0" />
          </motion.div>
          <div className="leading-tight">
            <div className="font-display text-lg text-[#FFFFF0]">FileStore</div>
            {subtitle && <div className="text-xs text-[#FFFFF0]/55">{subtitle}</div>}
          </div>
        </motion.header>
        {title && (
          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="font-display text-3xl md:text-4xl text-[#FFFFF0] mb-6"
          >
            {title}
          </motion.h1>
        )}
        {children}
      </motion.main>
      <BottomNav />
    </>
  );
}
