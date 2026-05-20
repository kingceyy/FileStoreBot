import type { HTMLAttributes } from "react";

interface Props extends HTMLAttributes<HTMLDivElement> {
  borderColor?: string;
  glowColor?: string;
}

export function Card({ borderColor, glowColor, className = "", style, children, ...rest }: Props) {
  return (
    <div
      className={`glass p-5 relative overflow-hidden ${className}`}
      style={{
        ...(borderColor ? { borderColor } : {}),
        ...(glowColor ? { boxShadow: `0 12px 40px -12px ${glowColor}` } : {}),
        ...style,
      }}
      {...rest}
    >
      {children}
    </div>
  );
}
