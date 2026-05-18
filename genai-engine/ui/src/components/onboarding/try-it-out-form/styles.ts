import { alpha, type Theme } from "@mui/material/styles";
import type { AnyFieldApi } from "@tanstack/react-form";

export const labelSx = { fontSize: 13, fontWeight: 500, color: "text.primary" };
export const sectionLabelSx = { fontSize: 13, fontWeight: 600, color: "text.primary" };

export const textFieldSx = {
  "& .MuiOutlinedInput-root": { borderRadius: "8px", fontSize: 14 },
  "& .MuiOutlinedInput-input": { py: "10px" },
};

export const radioCardSx = (selected: boolean) => (theme: Theme) => ({
  m: 0,
  px: 1.5,
  py: 1.25,
  width: "100%",
  border: "1px solid",
  borderRadius: "8px",
  borderColor: selected ? theme.palette.primary.main : theme.palette.divider,
  backgroundColor: selected ? alpha(theme.palette.primary.main, 0.08) : theme.palette.background.paper,
  cursor: "pointer",
  transition: "border-color 0.12s, background 0.12s",
  "&:hover": selected ? {} : { backgroundColor: theme.palette.action.hover },
  "& .MuiFormControlLabel-label": { width: "100%", fontSize: 13, color: theme.palette.text.primary },
});

export const chipSx = (selected: boolean) => (theme: Theme) => ({
  fontSize: 13,
  fontWeight: 500,
  height: "auto",
  py: 0.875,
  borderRadius: "999px",
  backgroundColor: selected ? alpha(theme.palette.primary.main, 0.08) : theme.palette.background.paper,
  color: selected ? theme.palette.primary.main : theme.palette.text.primary,
  borderColor: selected ? theme.palette.primary.main : theme.palette.divider,
  "& .MuiChip-label": { px: 1.25 },
  "&:hover": selected ? { backgroundColor: alpha(theme.palette.primary.main, 0.08) } : { backgroundColor: theme.palette.action.hover },
});

export const fieldErrorMessage = (field: AnyFieldApi): string | undefined => {
  const err = field.state.meta.errors[0];
  if (!err) return undefined;
  if (typeof err === "string") return err;
  if (typeof err === "object" && err !== null && "message" in err) {
    return String((err as { message: unknown }).message ?? "");
  }
  return undefined;
};
