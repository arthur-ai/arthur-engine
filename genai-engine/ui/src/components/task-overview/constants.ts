export const METRIC_COLORS = {
  traces: { main: "#3B82F6", light: "#EFF6FF", dark: "rgba(59,130,246,0.12)", border: "#BFDBFE", darkBorder: "rgba(59,130,246,0.3)" },
  tokens: { main: "#9333EA", light: "#FAF5FF", dark: "rgba(147,51,234,0.12)", border: "#E9D5FF", darkBorder: "rgba(147,51,234,0.3)" },
  cost: { main: "#D97706", light: "#FFFBEB", dark: "rgba(217,119,6,0.12)", border: "#FDE68A", darkBorder: "rgba(217,119,6,0.3)" },
  evals: { main: "#0D9488", light: "#F0FDFA", dark: "rgba(13,148,136,0.12)", border: "#99F6E4", darkBorder: "rgba(13,148,136,0.3)" },
  successRate: { main: "#059669", light: "#ECFDF5", dark: "rgba(5,150,105,0.12)", border: "#A7F3D0", darkBorder: "rgba(5,150,105,0.3)" },
} as const;

export const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toString();
};

function getCurrencySymbol(currencyCode: string): string {
  const parts = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currencyCode || "USD",
  }).formatToParts(0);
  return parts.find((p) => p.type === "currency")?.value ?? "$";
}

export const formatCostAxisValue = (value: number, currencyCode: string = "USD"): string => {
  const symbol = getCurrencySymbol(currencyCode);
  if (value >= 1000) {
    return `${symbol}${(value / 1000).toFixed(1)}K`;
  }
  if (value >= 1) {
    return `${symbol}${value.toFixed(2)}`;
  }
  if (value >= 0.01) {
    return `${symbol}${value.toFixed(2)}`;
  }
  if (value >= 0.001) {
    return `${symbol}${value.toFixed(3)}`;
  }
  if (value >= 0.0001) {
    return `${symbol}${value.toFixed(4)}`;
  }
  if (value === 0) {
    return `${symbol}0`;
  }
  return `${symbol}${value.toExponential(1)}`;
};

export const formatPercentValue = (value: number): string => {
  return `${value.toFixed(1)}%`;
};

export const formatXLabel = (date: Date, xLabelFormat: "time" | "date"): string => {
  switch (xLabelFormat) {
    case "time":
      return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
    case "date":
      return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    default:
      return "";
  }
};
