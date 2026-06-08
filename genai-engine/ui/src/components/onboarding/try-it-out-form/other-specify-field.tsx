import { TextField } from "@mui/material";
import type { AnyFieldApi } from "@tanstack/react-form";

import { textFieldSx } from "./styles";

/**
 * Text input revealed when a question's "Other" option is selected.
 *
 * The submit button stays gated by the form schema (an empty "Other" input keeps it
 * disabled), so submit-driven validation can never fire here. Instead we derive the
 * feedback from the field's value + blur state: a persistent "Required" hint while
 * empty, switching to a red border + "Please specify" once the user blurs while empty,
 * and clearing as soon as they type.
 */
export const OtherSpecifyField: React.FC<{ field: AnyFieldApi; placeholder: string }> = ({ field, placeholder }) => {
  const empty = !String(field.state.value ?? "").trim();
  const showError = empty && field.state.meta.isBlurred;
  return (
    <TextField
      placeholder={placeholder}
      value={field.state.value}
      onBlur={field.handleBlur}
      onChange={(e) => field.handleChange(e.target.value)}
      required
      error={showError}
      helperText={showError ? "Please specify" : empty ? "Required" : undefined}
      size="small"
      fullWidth
      sx={{ ...textFieldSx, mt: -1 }}
    />
  );
};
