export interface Plan {
  id: string;
  name: string;
  duration: string;
  days: number;
  priceFCFA: number;
  priceCDF: number;
  priceUSD: number;
  asset: string;
  color: string;
  glow: string;
  popular?: boolean;
}

export const PLANS: Plan[] = [
  { id: "bronze", name: "Bronze", duration: "7 jours", days: 7, priceFCFA: 520, priceCDF: 2500, priceUSD: 0.94, asset: "bronze.png", color: "#CD7F32", glow: "rgba(205,127,50,0.25)" },
  { id: "argent", name: "Argent", duration: "30 jours", days: 30, priceFCFA: 2100, priceCDF: 8800, priceUSD: 3.80, asset: "argent.png", color: "#A8A8A8", glow: "rgba(168,168,168,0.25)", popular: true },
  { id: "or", name: "Or", duration: "2 mois", days: 60, priceFCFA: 4200, priceCDF: 17600, priceUSD: 7.50, asset: "or.png", color: "#FFB200", glow: "rgba(255,178,0,0.25)" },
  { id: "platine", name: "Platine", duration: "3 mois", days: 90, priceFCFA: 6300, priceCDF: 26400, priceUSD: 11.0, asset: "platine.png", color: "#E8E8E8", glow: "rgba(232,232,232,0.20)" },
  { id: "diamant", name: "Diamant", duration: "6 mois", days: 180, priceFCFA: 12600, priceCDF: 52800, priceUSD: 22.0, asset: "diamant.png", color: "#0088CC", glow: "rgba(0,136,204,0.30)" },
  { id: "adamantide", name: "Adamantide", duration: "12 mois", days: 365, priceFCFA: 25200, priceCDF: 105500, priceUSD: 45.2, asset: "adamantide.png", color: "#FFFFFF", glow: "rgba(255,255,255,0.15)" },
];

export function formatPrice(plan: Plan, currency: "fcfa" | "cdf" | "usd") {
  if (currency === "fcfa") return `${plan.priceFCFA.toLocaleString("fr-FR")} FCFA`;
  if (currency === "cdf") return `${plan.priceCDF.toLocaleString("fr-FR")} CDF`;
  return `$${plan.priceUSD.toFixed(2)}`;
}
