import { Add as AddIcon, DeleteOutlined as DeleteOutlineIcon } from "@mui/icons-material";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { emptyTraceFilterRow, TRACE_FILTER_OPERATORS, type TraceFilterRow } from "./traceFilter";

export {
  completeTraceFilterRows,
  emptyTraceFilterRow,
  rowsToTraceFilter,
  traceFilterSchema,
  traceFilterToRows,
  type TraceFilterRow,
} from "./traceFilter";

type Props = {
  value: TraceFilterRow[];
  onChange: (value: TraceFilterRow[]) => void;
};

export const TraceFilterField = ({ value, onChange }: Props) => {
  const updateRow = (index: number, patch: Partial<TraceFilterRow>) =>
    onChange(value.map((row, i) => (i === index ? { ...row, ...patch, ...(patch.operator === "exists" ? { value: "" } : {}) } : row)));

  return (
    <Stack spacing={1.5}>
      <Stack spacing={0.5}>
        <Typography variant="subtitle2" color="text.primary">
          Trace filter
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Judge only traces that meet every condition. Others are skipped before the judge is called, so they cost nothing. Paths work like transform
          paths, e.g. attributes.metadata.plan. Leave empty to judge every sampled trace.
        </Typography>
      </Stack>
      {value.map((row, index) => (
        <Stack key={index} direction="row" spacing={1} sx={{ alignItems: "flex-start" }}>
          <TextField
            label="Span name"
            size="small"
            placeholder="Any span"
            value={row.spanName}
            onChange={(e) => updateRow(index, { spanName: e.target.value })}
            sx={{ flex: 1 }}
          />
          <TextField
            label="Attribute path"
            size="small"
            required
            placeholder="attributes.metadata.plan"
            value={row.attributePath}
            onChange={(e) => updateRow(index, { attributePath: e.target.value })}
            error={row.attributePath.trim() === ""}
            sx={{ flex: 2 }}
          />
          <TextField
            select
            label="Operator"
            size="small"
            value={row.operator}
            onChange={(e) => updateRow(index, { operator: e.target.value as TraceFilterRow["operator"] })}
            sx={{ flex: 1 }}
          >
            {TRACE_FILTER_OPERATORS.map((op) => (
              <MenuItem key={op.value} value={op.value}>
                {op.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Value"
            size="small"
            disabled={row.operator === "exists"}
            value={row.value}
            onChange={(e) => updateRow(index, { value: e.target.value })}
            error={row.operator !== "exists" && row.value.trim() === ""}
            sx={{ flex: 1 }}
          />
          <IconButton aria-label="Remove condition" onClick={() => onChange(value.filter((_, i) => i !== index))}>
            <DeleteOutlineIcon />
          </IconButton>
        </Stack>
      ))}
      <Button variant="text" startIcon={<AddIcon />} onClick={() => onChange([...value, emptyTraceFilterRow()])} sx={{ alignSelf: "flex-start" }}>
        Add condition
      </Button>
    </Stack>
  );
};
