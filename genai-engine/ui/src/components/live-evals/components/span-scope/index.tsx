import Alert from "@mui/material/Alert";
import FormControlLabel from "@mui/material/FormControlLabel";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import {
  describeSpanScopeCost,
  describeWholeTraceInSpanScope,
  effectiveTransformVariables,
  ROLLUP_RULES,
  spanScopeSchema,
  type SpanScopeValues,
} from "./spanScope";

import { useTransformVersions } from "@/components/transforms/hooks/useTransformVersions";
import { wholeTraceVariableNames } from "@/components/transforms/variableRows";

export * from "./spanScope";

type Props = {
  value: SpanScopeValues;
  onChange: (value: SpanScopeValues) => void;
  // The eval's transform, to warn about whole-trace variables in span scope.
  transformId?: string | null;
  transformVersionId?: string | null;
};

const fieldError = (value: SpanScopeValues, field: keyof SpanScopeValues): string | undefined => {
  const result = spanScopeSchema.safeParse(value);
  return result.success ? undefined : result.error.issues.find((issue) => issue.path[0] === field)?.message;
};

export const SpanScopeField = ({ value, onChange, transformId, transformVersionId }: Props) => {
  const update = (patch: Partial<SpanScopeValues>) => onChange({ ...value, ...patch });
  const { data: versions = [] } = useTransformVersions(value.scope === "span" ? transformId : null);
  const wholeTraceWarning = describeWholeTraceInSpanScope(
    wholeTraceVariableNames(effectiveTransformVariables(versions, transformVersionId)),
    value.maxSpans
  );
  const spanNameError = fieldError(value, "spanName");
  const maxSpansError = fieldError(value, "maxSpans");
  const rollupError = fieldError(value, "rollupRule");

  return (
    <Stack spacing={1.5}>
      <Stack spacing={0.5}>
        <Typography variant="subtitle2" color="text.primary">
          What each run judges
        </Typography>
        <RadioGroup row value={value.scope} onChange={(e) => update({ scope: e.target.value as SpanScopeValues["scope"] })}>
          <FormControlLabel value="trace" control={<Radio />} label="The whole trace, once" />
          <FormControlLabel value="span" control={<Radio />} label="Each matching span" />
        </RadioGroup>
        <Typography variant="body2" color="text.secondary">
          {value.scope === "span"
            ? "Every span matching the filter gets its own verdict and label, and the trace gets one verdict from them. Use a transform variable set to read the judged span."
            : "One verdict per trace, as before."}
        </Typography>
      </Stack>
      {value.scope === "span" && (
        <>
          <Stack direction="row" spacing={1}>
            <TextField
              label="Span name"
              size="small"
              placeholder="e.g. lookup_order"
              value={value.spanName}
              onChange={(e) => update({ spanName: e.target.value })}
              error={!!spanNameError}
              helperText={spanNameError}
              sx={{ flex: 2 }}
            />
            <TextField
              label="Span kind"
              size="small"
              placeholder="e.g. TOOL"
              value={value.spanKind}
              onChange={(e) => update({ spanKind: e.target.value })}
              sx={{ flex: 1 }}
            />
            <TextField
              label="Most spans per trace"
              size="small"
              type="number"
              value={value.maxSpans}
              onChange={(e) => update({ maxSpans: e.target.value })}
              error={!!maxSpansError}
              helperText={maxSpansError}
              sx={{ flex: 1 }}
            />
          </Stack>
          <Stack spacing={0.5}>
            <Typography variant="subtitle2" color="text.primary">
              How span verdicts decide the trace
            </Typography>
            <RadioGroup value={value.rollupRule} onChange={(e) => update({ rollupRule: e.target.value as SpanScopeValues["rollupRule"] })}>
              {ROLLUP_RULES.map((rule) => (
                <FormControlLabel
                  key={rule.value}
                  value={rule.value}
                  control={<Radio />}
                  label={
                    <Stack>
                      <Typography variant="body2" color="text.primary">
                        {rule.label}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {rule.help}
                      </Typography>
                    </Stack>
                  }
                />
              ))}
            </RadioGroup>
            {rollupError && (
              <Typography variant="caption" color="error.main">
                {rollupError}
              </Typography>
            )}
          </Stack>
          <Alert severity="warning">{describeSpanScopeCost(value)}</Alert>
          {wholeTraceWarning && <Alert severity="error">{wholeTraceWarning}</Alert>}
        </>
      )}
    </Stack>
  );
};
