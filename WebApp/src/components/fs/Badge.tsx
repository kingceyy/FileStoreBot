import type { HTMLAttributes } from "react";

interface Props extends HTMLAttributes<HTMLSpanElement> {
  color?: string;
}

export function Badge({ color = "#0088CC", className = "", children, style, ...rest }: Props) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${className}`}
      style={{ background: `${color}20`, color, border: `1px solid ${color}40`, ...style }}
      {...rest}
    >
      {children}
    </span>
  );
}
