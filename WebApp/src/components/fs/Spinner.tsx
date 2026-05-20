import { Loader2 } from "lucide-react";

export function Spinner({ size = "md", color = "#0088CC" }: { size?: "sm" | "md" | "lg"; color?: string }) {
  const px = size === "sm" ? 16 : size === "lg" ? 40 : 24;
  return <Loader2 className="animate-spin" size={px} color={color} />;
}
