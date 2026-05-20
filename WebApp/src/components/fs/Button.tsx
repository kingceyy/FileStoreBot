import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Loader2 } from "lucide-react";

type Variant = "primary" | "ghost" | "success" | "danger" | "gold";
type Size = "sm" | "md" | "lg";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  fullWidth?: boolean;
}

const variants: Record<Variant, string> = {
  primary: "bg-[#0088CC] text-[#FFFFF0] hover:bg-[#0099e0] shadow-[0_8px_24px_-8px_rgba(0,136,204,0.6)]",
  ghost: "bg-transparent border border-[#0088CC]/40 text-[#0088CC] hover:bg-[#0088CC]/10",
  success: "bg-[#22C55E] text-white hover:bg-[#1eb557]",
  danger: "bg-[#EF4444] text-white hover:bg-[#dc2f2f]",
  gold: "bg-[#FFB200] text-[#0A0A0A] hover:bg-[#ffbe26] shadow-[0_8px_24px_-8px_rgba(255,178,0,0.6)]",
};

const sizes: Record<Size, string> = {
  sm: "h-9 px-3 text-sm rounded-lg",
  md: "h-12 px-5 text-[15px] rounded-xl",
  lg: "h-[52px] px-6 text-base rounded-xl",
};

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant = "primary", size = "md", loading, fullWidth, className = "", children, disabled, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 font-display tracking-wide active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed transition-all ${variants[variant]} ${sizes[size]} ${fullWidth ? "w-full" : ""} ${className}`}
      {...rest}
    >
      {loading && <Loader2 className="animate-spin" size={18} />}
      {children}
    </button>
  );
});
