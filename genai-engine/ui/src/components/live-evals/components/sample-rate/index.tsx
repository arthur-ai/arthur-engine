import InputAdornment from "@mui/material/InputAdornment";
import TextField from "@mui/material/TextField";

export { percentToSampleRate, samplePercentSchema, sampleRateToPercent } from "./sampleRate";

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

export const SampleRateField = ({ value, onChange, onBlur, errors }: Props) => {
  const error = errorMessage(errors);
  return (
    <TextField
      label="Sample rate"
      type="number"
      fullWidth
      variant="outlined"
      placeholder="100"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onBlur}
      error={error !== undefined}
      helperText={
        error ??
        "Share of traces to evaluate. Leave empty to evaluate every trace. Traces are picked by trace ID, so continuous evals with the same rate evaluate the same traces."
      }
      slotProps={{
        htmlInput: { min: 1, max: 100, step: 1 },
        input: { endAdornment: <InputAdornment position="end">%</InputAdornment> },
      }}
    />
  );
};
