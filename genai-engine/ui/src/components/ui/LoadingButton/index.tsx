import { CircularProgress, useTheme } from "@mui/material";
import { motion } from "framer-motion";

import { cn } from "@/utils/cn";

interface Props extends React.ComponentProps<"button"> {
  loading?: boolean;
}

export const LoadingButton = ({
  loading = false,
  className,
  children,
  ...props
}: Props) => {
  const { palette } = useTheme();

  return (
    <button
      style={
        {
          "--background-color": palette.background.paper,
        } as React.CSSProperties
      }
      className={cn(
        "grid grid-cols-1 *:col-start-1 *:row-start-1 place-items-center text-black bg-(--background-color)",
        className
      )}
      {...props}
    >
      <motion.span
        animate={{
          opacity: loading ? 1 : 0,
          y: loading ? 0 : -4,
        }}
        transition={{
          duration: 0.4,
          type: "spring",
        }}
        className="size-4"
      >
        <CircularProgress size={16} color="inherit" />
      </motion.span>
      <motion.span
        animate={{
          opacity: loading ? 0 : 1,
          y: loading ? -4 : 0,
        }}
        transition={{
          duration: 0.4,
          type: "spring",
        }}
      >
        {children}
      </motion.span>
    </button>
  );
};
