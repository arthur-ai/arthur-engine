import InputAdornment from "@mui/material/InputAdornment";
import TextField from "@mui/material/TextField";

export { dailyCapSchema, dailyCapToUsd, usdToDailyCap } from "./dailyCap";

type Props = {
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  errors: unknown[];
};

const errorMessage = (errors: unknown[]): string | undefined => {
  const [first] = errors;
  if (typeof first === "string") return first;
  if (first && typeof first === "object" && "message" in first && typeof first.message === "string") return first.message;
  return undefined;
};

export const DailyCapField = ({ value, onChange, onBlur, errors }: Props) => {
  const error = errorMessage(errors);
  return (
    <TextField
      label="Daily spend cap"
      type="number"
      fullWidth
      variant="outlined"
      placeholder="No cap"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onBlur}
      error={error !== undefined}
      helperText={
        error ??
        "Most this eval may spend on judge calls per day. Once reached, new traces are skipped until midnight (engine time, UTC by default). Runs already calling the judge still finish, so spend can go slightly past the cap. Leave empty for no cap."
      }
      slotProps={{
        htmlInput: { min: 0, step: "any" },
        input: { startAdornment: <InputAdornment position="start">$</InputAdornment> },
      }}
    />
  );
};
