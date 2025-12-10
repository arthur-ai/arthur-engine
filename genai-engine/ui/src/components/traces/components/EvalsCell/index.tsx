import SyncIcon from "@mui/icons-material/Sync";
import { motion } from "framer-motion";

import { cn } from "@/utils/cn";

type Props = {
  className?: string;
};

export const EvalsCell = ({ className }: Props) => {
  return (
    <motion.button
      className={cn(
        "bg-[color-mix(in_oklab,var(--color)_20%,white)] border border-(--color)/50 text-(--color) rounded-md text-nowrap overflow-hidden cursor-pointer group",
        className
      )}
      style={{ "--color": "var(--color-green-700)" } as React.CSSProperties}
      animate={{ width: "auto" }}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      transition={{ type: "spring", bounce: 0, duration: 0.25 }}
    >
      <div className="px-1 flex items-center gap-1">
        <SyncIcon sx={{ fontSize: 12 }} />
        <span>3 of 5 evals</span>
      </div>
    </motion.button>
  );
};
