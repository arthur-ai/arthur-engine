export const METRIC_COLORS = {
  traces: { main: "#3B82F6", light: "#EFF6FF", border: "#BFDBFE" },
  tokens: { main: "#9333EA", light: "#FAF5FF", border: "#E9D5FF" },
  cost: { main: "#D97706", light: "#FFFBEB", border: "#FDE68A" },
  evals: { main: "#0D9488", light: "#F0FDFA", border: "#99F6E4" },
  successRate: { main: "#059669", light: "#ECFDF5", border: "#A7F3D0" },
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

export const formatCurrency = (amount: number): string => {
  return `$${amount.toFixed(2)}`;
};

export const formatCostAxisValue = (value: number): string => {
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`;
  }
  if (value >= 1) {
    return `$${value.toFixed(2)}`;
  }
  if (value >= 0.01) {
    return `$${value.toFixed(2)}`;
  }
  if (value >= 0.001) {
    return `$${value.toFixed(3)}`;
  }
  if (value >= 0.0001) {
    return `$${value.toFixed(4)}`;
  }
  if (value === 0) {
    return "$0";
  }
  return `$${value.toExponential(1)}`;
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
