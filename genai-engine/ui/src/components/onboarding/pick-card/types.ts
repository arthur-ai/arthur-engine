import type { ReactNode } from "react";

export interface PickCardProps {
  variant: "primary" | "default";
  icon: ReactNode;
  badge?: string;
  title: string;
  description: string;
  cta: string;
  onClick: () => void;
}
