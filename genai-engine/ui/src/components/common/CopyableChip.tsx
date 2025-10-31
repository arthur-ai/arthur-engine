import useSnackbar from "@/hooks/useSnackbar";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import { Alert, Snackbar } from "@mui/material";
import Chip from "@mui/material/Chip";
import { SxProps, Theme } from "@mui/material/styles";

type Props = {
  label: string;
  size?: "small" | "medium";
  color?:
    | "default"
    | "primary"
    | "secondary"
    | "error"
    | "info"
    | "success"
    | "warning";
  variant?: "filled" | "outlined";
  showIcon?: boolean;
  onCopy?: (text: string) => void;
  propagateClick?: boolean;
  sx?: SxProps<Theme>;
};

export const CopyableChip = ({
  label,
  size = "medium",
  color = "default",
  variant = "filled",
  showIcon = true,
  onCopy,
  propagateClick = false,
  sx,
}: Props) => {
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();

  const handleCopy = async (e: React.MouseEvent<HTMLDivElement>) => {
    if (!propagateClick) {
      e.stopPropagation();
    }

    try {
      await navigator.clipboard.writeText(label);
      showSnackbar("Copied to clipboard!", "success");

      // Call optional callback
      onCopy?.(label);
    } catch (error) {
      console.error("Failed to copy to clipboard:", error);
      showSnackbar("Failed to copy to clipboard", "error");
    }
  };

  return (
    <>
      <Chip
        size={size}
        label={label}
        color={color}
        variant={variant}
        onClick={handleCopy}
        icon={showIcon ? <ContentCopyIcon /> : undefined}
        clickable
        sx={[
          {
            cursor: "pointer",
            "&:hover": {
              backgroundColor: "action.hover",
            },
            "& .MuiChip-icon": {
              fontSize: "1rem",
              ml: 1,
            },
          },
          ...(Array.isArray(sx) ? sx : sx ? [sx] : []),
        ]}
      />

      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>
    </>
  );
};
