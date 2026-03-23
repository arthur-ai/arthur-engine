import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { Add, Close, FilterList } from "@mui/icons-material";
import { Autocomplete, Box, Button, Checkbox, Chip, FormControlLabel, IconButton, Paper, Popover, Stack, TextField, Typography } from "@mui/material";
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker";
import { useForm, useStore } from "@tanstack/react-form";
import dayjs, { type Dayjs } from "dayjs";
import { useEffect, useRef, useState } from "react";

import { useFilterStore } from "../../../stores/filter.store";
import type { IncomingFilter } from "../../filtering/mapper";
import { EnumOperators, Operators, TextOperators } from "../../filtering/types";

interface FilterState {
  spanTypes: string[];
  traceDurationMin: string;
  traceDurationMax: string;
  traceDurationInclusive: boolean;
  totalTokenCountMin: string;
  totalTokenCountMax: string;
  promptTokenCountMin: string;
  promptTokenCountMax: string;
  completionTokenCountMin: string;
  completionTokenCountMax: string;
  spanCountMin: string;
  spanCountMax: string;
  traceIds: string[];
  sessionIds: string[];
  spanIds: string[];
  userIds: string[];
  annotationScore: string | null;
  statusCode: string | null;
  annotationType: string | null;
  continuousEvalRunStatus: string | null;
  continuousEvalName: string;
  includeExperimentTraces: string | null;
  toolName: string;
  startTime: string;
  endTime: string;
}

interface ValidationErrors {
  traceDurationMin?: string;
  traceDurationMax?: string;
  totalTokenCountMin?: string;
  totalTokenCountMax?: string;
  promptTokenCountMin?: string;
  promptTokenCountMax?: string;
  completionTokenCountMin?: string;
  completionTokenCountMax?: string;
  spanCountMin?: string;
  spanCountMax?: string;
  startTime?: string;
  endTime?: string;
}

const SPAN_TYPE_OPTIONS = Object.values(OpenInferenceSpanKind);
const ANNOTATION_SCORE_OPTIONS = ["0", "1"];
const STATUS_CODE_OPTIONS = ["Ok", "Error"];
const ANNOTATION_TYPE_OPTIONS = ["human", "continuous_eval"];
const CONTINUOUS_EVAL_RUN_STATUS_OPTIONS = ["pending", "passed", "running", "failed", "skipped", "error"];
const INCLUDE_EXPERIMENT_TRACES_OPTIONS = ["true", "false"];

const NUMERIC_INPUT_SX = {
  width: 120,
  "& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button": {
    WebkitAppearance: "none",
    margin: 0,
  },
} as const;

const NUMERIC_SLOT_PROPS = {
  htmlInput: {
    min: 0,
    step: 1,
    style: { MozAppearance: "textfield" } as React.CSSProperties,
  },
} as const;

const buildTokenCountFilters = (name: string, min: string, max: string): IncomingFilter[] => {
  const filters: IncomingFilter[] = [];
  if (min && max && min === max) {
    filters.push({ name, operator: Operators.EQUALS, value: min });
  } else {
    if (min) {
      filters.push({ name, operator: Operators.GREATER_THAN_OR_EQUAL, value: min });
    }
    if (max) {
      filters.push({ name, operator: Operators.LESS_THAN_OR_EQUAL, value: max });
    }
  }
  return filters;
};

const buildFiltersFromFormValues = (value: FilterState): IncomingFilter[] => {
  const filters: IncomingFilter[] = [];

  // Span Types
  if (value.spanTypes.length > 0) {
    filters.push({
      name: "span_types",
      operator: Operators.IN,
      value: value.spanTypes,
    });
  }

  // Trace Duration
  if (value.traceDurationMin && value.traceDurationMax && value.traceDurationMin === value.traceDurationMax) {
    filters.push({
      name: "trace_duration",
      operator: Operators.EQUALS,
      value: value.traceDurationMin,
    });
  } else {
    if (value.traceDurationMin) {
      filters.push({
        name: "trace_duration",
        operator: value.traceDurationInclusive ? Operators.GREATER_THAN_OR_EQUAL : Operators.GREATER_THAN,
        value: value.traceDurationMin,
      });
    }
    if (value.traceDurationMax) {
      filters.push({
        name: "trace_duration",
        operator: value.traceDurationInclusive ? Operators.LESS_THAN_OR_EQUAL : Operators.LESS_THAN,
        value: value.traceDurationMax,
      });
    }
  }

  // Token Count filters
  filters.push(...buildTokenCountFilters("total_token_count", value.totalTokenCountMin, value.totalTokenCountMax));
  filters.push(...buildTokenCountFilters("prompt_token_count", value.promptTokenCountMin, value.promptTokenCountMax));
  filters.push(...buildTokenCountFilters("completion_token_count", value.completionTokenCountMin, value.completionTokenCountMax));
  filters.push(...buildTokenCountFilters("span_count", value.spanCountMin, value.spanCountMax));

  // IDs
  if (value.traceIds.length > 0) {
    filters.push({ name: "trace_ids", operator: Operators.IN, value: value.traceIds });
  }
  if (value.sessionIds.length > 0) {
    filters.push({ name: "session_ids", operator: Operators.IN, value: value.sessionIds });
  }
  if (value.spanIds.length > 0) {
    filters.push({ name: "span_ids", operator: Operators.IN, value: value.spanIds });
  }
  if (value.userIds.length > 0) {
    filters.push({ name: "user_ids", operator: Operators.IN, value: value.userIds });
  }

  // Annotation Score
  if (value.annotationScore !== null) {
    filters.push({ name: "annotation_score", operator: EnumOperators.EQUALS, value: value.annotationScore });
  }

  // Status Code
  if (value.statusCode !== null) {
    filters.push({ name: "status_code", operator: EnumOperators.EQUALS, value: value.statusCode });
  }

  // Annotation Type
  if (value.annotationType !== null) {
    filters.push({ name: "annotation_type", operator: EnumOperators.EQUALS, value: value.annotationType });
  }

  // Continuous Eval Run Status
  if (value.continuousEvalRunStatus !== null) {
    filters.push({ name: "continuous_eval_run_status", operator: EnumOperators.EQUALS, value: value.continuousEvalRunStatus });
  }

  // Continuous Eval Name
  if (value.continuousEvalName.trim()) {
    filters.push({ name: "continuous_eval_name", operator: TextOperators.CONTAINS, value: value.continuousEvalName.trim() });
  }

  // Include Experiment Traces
  if (value.includeExperimentTraces !== null) {
    filters.push({ name: "include_experiment_traces", operator: EnumOperators.EQUALS, value: value.includeExperimentTraces });
  }

  // Tool Name
  if (value.toolName.trim()) {
    filters.push({ name: "tool_name", operator: TextOperators.EQUALS, value: value.toolName.trim() });
  }

  // Custom Timestamp
  if (value.startTime) {
    filters.push({ name: "start_time", operator: Operators.GREATER_THAN_OR_EQUAL, value: value.startTime });
  }
  if (value.endTime) {
    filters.push({ name: "end_time", operator: Operators.LESS_THAN_OR_EQUAL, value: value.endTime });
  }

  return filters;
};

const DEFAULT_FILTER_STATE: FilterState = {
  spanTypes: [],
  traceDurationMin: "",
  traceDurationMax: "",
  traceDurationInclusive: false,
  totalTokenCountMin: "",
  totalTokenCountMax: "",
  promptTokenCountMin: "",
  promptTokenCountMax: "",
  completionTokenCountMin: "",
  completionTokenCountMax: "",
  spanCountMin: "",
  spanCountMax: "",
  traceIds: [],
  sessionIds: [],
  spanIds: [],
  userIds: [],
  annotationScore: null,
  statusCode: null,
  annotationType: null,
  continuousEvalRunStatus: null,
  continuousEvalName: "",
  includeExperimentTraces: null,
  toolName: "",
  startTime: "",
  endTime: "",
};

const parseTokenCountFromFilters = (filters: IncomingFilter[], name: string): { min: string; max: string } => {
  let min = "";
  let max = "";
  for (const f of filters) {
    if (f.name !== name) continue;
    if (f.operator === Operators.GREATER_THAN_OR_EQUAL || f.operator === Operators.GREATER_THAN) {
      min = String(f.value);
    } else if (f.operator === Operators.LESS_THAN_OR_EQUAL || f.operator === Operators.LESS_THAN) {
      max = String(f.value);
    } else if (f.operator === Operators.EQUALS) {
      min = String(f.value);
      max = String(f.value);
    }
  }
  return { min, max };
};

export const TracingFilterModal = () => {
  const anchorElRef = useRef<HTMLButtonElement | null>(null);
  const [open, setOpen] = useState(false);
  const setFilters = useFilterStore((state) => state.setFilters);
  const currentFilters = useFilterStore((state) => state.filters);

  const [traceIdInput, setTraceIdInput] = useState("");
  const [sessionIdInput, setSessionIdInput] = useState("");
  const [spanIdInput, setSpanIdInput] = useState("");
  const [userIdInput, setUserIdInput] = useState("");
  const [pendingFilters, setPendingFilters] = useState<IncomingFilter[] | null>(null);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});

  const form = useForm({
    defaultValues: { ...DEFAULT_FILTER_STATE },
    onSubmit: async ({ value }) => {
      const filters = buildFiltersFromFormValues(value as FilterState);
      setPendingFilters(filters);
      handleClose();
    },
  });

  useEffect(() => {
    if (!open) return;

    const newFilterState: FilterState = { ...DEFAULT_FILTER_STATE };

    const totalTokenCount = parseTokenCountFromFilters(currentFilters, "total_token_count");
    newFilterState.totalTokenCountMin = totalTokenCount.min;
    newFilterState.totalTokenCountMax = totalTokenCount.max;

    const promptTokenCount = parseTokenCountFromFilters(currentFilters, "prompt_token_count");
    newFilterState.promptTokenCountMin = promptTokenCount.min;
    newFilterState.promptTokenCountMax = promptTokenCount.max;

    const completionTokenCount = parseTokenCountFromFilters(currentFilters, "completion_token_count");
    newFilterState.completionTokenCountMin = completionTokenCount.min;
    newFilterState.completionTokenCountMax = completionTokenCount.max;

    const spanCount = parseTokenCountFromFilters(currentFilters, "span_count");
    newFilterState.spanCountMin = spanCount.min;
    newFilterState.spanCountMax = spanCount.max;

    currentFilters.forEach((filter) => {
      switch (filter.name) {
        case "span_types":
          newFilterState.spanTypes = Array.isArray(filter.value) ? filter.value : [];
          break;
        case "trace_duration":
          if (filter.operator === Operators.GREATER_THAN || filter.operator === Operators.GREATER_THAN_OR_EQUAL) {
            newFilterState.traceDurationMin = String(filter.value);
            newFilterState.traceDurationInclusive = filter.operator === Operators.GREATER_THAN_OR_EQUAL;
          } else if (filter.operator === Operators.LESS_THAN || filter.operator === Operators.LESS_THAN_OR_EQUAL) {
            newFilterState.traceDurationMax = String(filter.value);
            newFilterState.traceDurationInclusive = filter.operator === Operators.LESS_THAN_OR_EQUAL;
          } else if (filter.operator === Operators.EQUALS) {
            newFilterState.traceDurationMin = String(filter.value);
            newFilterState.traceDurationMax = String(filter.value);
          }
          break;
        case "trace_ids":
          newFilterState.traceIds = Array.isArray(filter.value) ? filter.value : [];
          break;
        case "session_ids":
          newFilterState.sessionIds = Array.isArray(filter.value) ? filter.value : [];
          break;
        case "span_ids":
          newFilterState.spanIds = Array.isArray(filter.value) ? filter.value : [];
          break;
        case "user_ids":
          newFilterState.userIds = Array.isArray(filter.value) ? filter.value : [];
          break;
        case "annotation_score":
          newFilterState.annotationScore = String(filter.value);
          break;
        case "status_code":
          newFilterState.statusCode = String(filter.value);
          break;
        case "annotation_type":
          newFilterState.annotationType = String(filter.value);
          break;
        case "continuous_eval_run_status":
          newFilterState.continuousEvalRunStatus = String(filter.value);
          break;
        case "continuous_eval_name":
          newFilterState.continuousEvalName = String(filter.value);
          break;
        case "include_experiment_traces":
          newFilterState.includeExperimentTraces = String(filter.value);
          break;
        case "tool_name":
          newFilterState.toolName = String(filter.value);
          break;
        case "start_time":
          newFilterState.startTime = String(filter.value);
          break;
        case "end_time":
          newFilterState.endTime = String(filter.value);
          break;
      }
    });

    Object.entries(newFilterState).forEach(([key, value]) => {
      form.setFieldValue(key as keyof FilterState, value as never);
    });
  }, [open, currentFilters, form]);

  const handleClose = () => {
    setOpen(false);
  };

  const handleExited = () => {
    if (pendingFilters) {
      const spanNameFilter = currentFilters.find((f) => f.name === "span_name");
      const filtersToApply = spanNameFilter ? [spanNameFilter, ...pendingFilters] : pendingFilters;
      setFilters(filtersToApply);
      setPendingFilters(null);
    }
  };

  const handleAddId = (type: "trace" | "session" | "span" | "user", value: string) => {
    if (value.trim()) {
      const fieldName = `${type}Ids` as keyof FilterState;
      const currentValue = form.getFieldValue(fieldName) as string[];
      form.setFieldValue(fieldName, [...currentValue, value.trim()] as never);

      if (type === "trace") setTraceIdInput("");
      if (type === "session") setSessionIdInput("");
      if (type === "span") setSpanIdInput("");
      if (type === "user") setUserIdInput("");
    }
  };

  const handleRemoveId = (type: "trace" | "session" | "span" | "user", id: string) => {
    const fieldName = `${type}Ids` as keyof FilterState;
    const currentValue = form.getFieldValue(fieldName) as string[];
    form.setFieldValue(fieldName, currentValue.filter((item) => item !== id) as never);
  };

  const handleClearFilters = () => {
    form.reset();
    setValidationErrors({});
    const spanNameFilter = currentFilters.find((f) => f.name === "span_name");
    setFilters(spanNameFilter ? [spanNameFilter] : []);
  };

  const handleNonNegativeNumericChange = (val: string, fieldChange: (v: string) => void, errorKey: keyof ValidationErrors) => {
    setValidationErrors((prev) => ({ ...prev, [errorKey]: undefined }));
    if (val === "") {
      fieldChange(val);
      return;
    }
    const numVal = parseFloat(val);
    if (numVal < 0) {
      fieldChange("0");
      setValidationErrors((prev) => ({ ...prev, [errorKey]: "Value cannot be less than 0." }));
    } else {
      fieldChange(val);
    }
  };

  const formState = useStore(form.store, (state) => state.values);
  const hasActiveFilters =
    formState.spanTypes.length > 0 ||
    formState.traceDurationMin !== "" ||
    formState.traceDurationMax !== "" ||
    formState.totalTokenCountMin !== "" ||
    formState.totalTokenCountMax !== "" ||
    formState.promptTokenCountMin !== "" ||
    formState.promptTokenCountMax !== "" ||
    formState.completionTokenCountMin !== "" ||
    formState.completionTokenCountMax !== "" ||
    formState.spanCountMin !== "" ||
    formState.spanCountMax !== "" ||
    formState.traceIds.length > 0 ||
    formState.sessionIds.length > 0 ||
    formState.spanIds.length > 0 ||
    formState.userIds.length > 0 ||
    formState.annotationScore !== null ||
    formState.statusCode !== null ||
    formState.annotationType !== null ||
    formState.continuousEvalRunStatus !== null ||
    formState.continuousEvalName.trim() !== "" ||
    formState.includeExperimentTraces !== null ||
    formState.toolName.trim() !== "" ||
    formState.startTime !== "" ||
    formState.endTime !== "";

  const renderNumericRangeFilter = (
    label: string,
    minField: keyof FilterState,
    maxField: keyof FilterState,
    minErrorKey: keyof ValidationErrors,
    maxErrorKey: keyof ValidationErrors
  ) => (
    <Box>
      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
        {label}
      </Typography>
      <Stack spacing={1}>
        <Stack direction="row" spacing={1} alignItems="center">
          <form.Field name={minField}>
            {(field) => (
              <TextField
                size="small"
                type="number"
                placeholder="Min"
                value={field.state.value}
                onChange={(e) => handleNonNegativeNumericChange(e.target.value, (v) => field.handleChange(v as never), minErrorKey)}
                slotProps={NUMERIC_SLOT_PROPS}
                sx={NUMERIC_INPUT_SX}
              />
            )}
          </form.Field>
          <Typography variant="body2" color="text.secondary">
            to
          </Typography>
          <form.Field name={maxField}>
            {(field) => (
              <TextField
                size="small"
                type="number"
                placeholder="Max"
                value={field.state.value}
                onChange={(e) => handleNonNegativeNumericChange(e.target.value, (v) => field.handleChange(v as never), maxErrorKey)}
                slotProps={NUMERIC_SLOT_PROPS}
                sx={NUMERIC_INPUT_SX}
              />
            )}
          </form.Field>
        </Stack>
        {(validationErrors[minErrorKey] || validationErrors[maxErrorKey]) && (
          <Typography variant="caption" color="error">
            {validationErrors[minErrorKey] || validationErrors[maxErrorKey]}
          </Typography>
        )}
      </Stack>
    </Box>
  );

  const renderIdFilter = (
    label: string,
    type: "trace" | "session" | "span" | "user",
    inputValue: string,
    setInputValue: (v: string) => void,
    fieldName: "traceIds" | "sessionIds" | "spanIds" | "userIds"
  ) => (
    <Box>
      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
        {label}
      </Typography>
      <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
        <TextField
          size="small"
          fullWidth
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleAddId(type, inputValue);
            }
          }}
          placeholder={`Enter ${label}`}
        />
        <IconButton size="small" onClick={() => handleAddId(type, inputValue)} disabled={!inputValue.trim()} color="primary">
          <Add />
        </IconButton>
      </Stack>
      <form.Field name={fieldName}>
        {(field) => (
          <Stack direction="row" flexWrap="wrap" gap={1}>
            {field.state.value.map((id) => (
              <Chip key={id} label={id} size="small" onDelete={() => handleRemoveId(type, id)} deleteIcon={<Close />} />
            ))}
          </Stack>
        )}
      </form.Field>
    </Box>
  );

  return (
    <>
      <Button
        ref={anchorElRef}
        variant="outlined"
        startIcon={<FilterList />}
        onClick={() => setOpen(true)}
        color={hasActiveFilters ? "primary" : "inherit"}
      >
        Filter
      </Button>
      <Popover
        open={open}
        anchorEl={anchorElRef.current}
        onClose={handleClose}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
        transformOrigin={{ vertical: "top", horizontal: "left" }}
        slotProps={{ transition: { onExited: handleExited } }}
        transitionDuration={150}
      >
        <Paper sx={{ width: 420, maxHeight: 600, display: "flex", flexDirection: "column" }}>
          <Box sx={{ p: 2, overflowY: "auto", flex: 1 }}>
            <Stack spacing={3}>
              {/* Timestamp */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Timestamp
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: "block" }}>
                  Overrides the time range selector when set
                </Typography>
                <Stack spacing={1.5}>
                  <form.Field name="startTime">
                    {(field) => (
                      <DateTimePicker
                        label="Start Time"
                        value={field.state.value ? dayjs(field.state.value) : null}
                        onChange={(newValue: Dayjs | null) => {
                          field.handleChange(newValue ? newValue.toISOString() : "");
                          setValidationErrors((prev) => ({ ...prev, startTime: undefined, endTime: undefined }));
                        }}
                        slotProps={{ textField: { size: "small", fullWidth: true } }}
                        disableFuture
                      />
                    )}
                  </form.Field>
                  <form.Field name="endTime">
                    {(field) => (
                      <DateTimePicker
                        label="End Time"
                        value={field.state.value ? dayjs(field.state.value) : null}
                        onChange={(newValue: Dayjs | null) => {
                          field.handleChange(newValue ? newValue.toISOString() : "");
                          setValidationErrors((prev) => ({ ...prev, startTime: undefined, endTime: undefined }));
                        }}
                        slotProps={{ textField: { size: "small", fullWidth: true } }}
                        disableFuture
                      />
                    )}
                  </form.Field>
                  {(validationErrors.startTime || validationErrors.endTime) && (
                    <Typography variant="caption" color="error">
                      {validationErrors.startTime || validationErrors.endTime}
                    </Typography>
                  )}
                </Stack>
              </Box>

              {/* Total Token Count */}
              {renderNumericRangeFilter("Total Token Count", "totalTokenCountMin", "totalTokenCountMax", "totalTokenCountMin", "totalTokenCountMax")}

              {/* Prompt Token Count */}
              {renderNumericRangeFilter(
                "Prompt Token Count",
                "promptTokenCountMin",
                "promptTokenCountMax",
                "promptTokenCountMin",
                "promptTokenCountMax"
              )}

              {/* Completion Token Count */}
              {renderNumericRangeFilter(
                "Completion Token Count",
                "completionTokenCountMin",
                "completionTokenCountMax",
                "completionTokenCountMin",
                "completionTokenCountMax"
              )}

              {/* Number of Spans */}
              {renderNumericRangeFilter("Number of Spans", "spanCountMin", "spanCountMax", "spanCountMin", "spanCountMax")}

              {/* Tool Name */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Tool Name
                </Typography>
                <form.Field name="toolName">
                  {(field) => (
                    <TextField
                      size="small"
                      fullWidth
                      value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      placeholder="Exact tool name"
                      slotProps={{
                        input: {
                          endAdornment: field.state.value && (
                            <IconButton size="small" onClick={() => field.handleChange("")} sx={{ mr: -1 }}>
                              <Close fontSize="small" />
                            </IconButton>
                          ),
                        },
                      }}
                    />
                  )}
                </form.Field>
              </Box>

              {/* Span Types */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Span Types
                </Typography>
                <form.Field name="spanTypes">
                  {(field) => (
                    <Autocomplete
                      multiple
                      options={SPAN_TYPE_OPTIONS}
                      value={field.state.value}
                      onChange={(_, newValue) => field.handleChange(newValue)}
                      renderInput={(params) => <TextField {...params} size="small" placeholder="Select span types" />}
                      disableCloseOnSelect
                    />
                  )}
                </form.Field>
              </Box>

              {/* Trace Duration */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Trace Duration (ms)
                </Typography>
                <Stack spacing={1}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <form.Field name="traceDurationMin">
                      {(field) => (
                        <TextField
                          size="small"
                          type="number"
                          placeholder="Min"
                          value={field.state.value}
                          onChange={(e) => handleNonNegativeNumericChange(e.target.value, (v) => field.handleChange(v), "traceDurationMin")}
                          slotProps={NUMERIC_SLOT_PROPS}
                          sx={{ ...NUMERIC_INPUT_SX, width: 100 }}
                        />
                      )}
                    </form.Field>
                    <form.Field name="traceDurationMax">
                      {(field) => (
                        <TextField
                          size="small"
                          type="number"
                          placeholder="Max"
                          value={field.state.value}
                          onChange={(e) => handleNonNegativeNumericChange(e.target.value, (v) => field.handleChange(v), "traceDurationMax")}
                          slotProps={NUMERIC_SLOT_PROPS}
                          sx={{ ...NUMERIC_INPUT_SX, width: 100 }}
                        />
                      )}
                    </form.Field>
                    <form.Field name="traceDurationInclusive">
                      {(field) => (
                        <FormControlLabel
                          control={<Checkbox checked={field.state.value} onChange={(e) => field.handleChange(e.target.checked)} size="small" />}
                          label="Inclusive"
                          sx={{ whiteSpace: "nowrap" }}
                        />
                      )}
                    </form.Field>
                  </Stack>
                  {(validationErrors.traceDurationMin || validationErrors.traceDurationMax) && (
                    <Typography variant="caption" color="error">
                      {validationErrors.traceDurationMin || validationErrors.traceDurationMax}
                    </Typography>
                  )}
                </Stack>
              </Box>

              {/* ID Filters */}
              {renderIdFilter("Trace ID", "trace", traceIdInput, setTraceIdInput, "traceIds")}
              {renderIdFilter("Session ID", "session", sessionIdInput, setSessionIdInput, "sessionIds")}
              {renderIdFilter("Span ID", "span", spanIdInput, setSpanIdInput, "spanIds")}
              {renderIdFilter("User ID", "user", userIdInput, setUserIdInput, "userIds")}

              {/* Annotation Score */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Annotation Score
                </Typography>
                <form.Field name="annotationScore">
                  {(field) => (
                    <Autocomplete
                      options={ANNOTATION_SCORE_OPTIONS}
                      value={field.state.value}
                      onChange={(_, newValue) => field.handleChange(newValue)}
                      renderInput={(params) => <TextField {...params} size="small" placeholder="Select score" />}
                      getOptionLabel={(option) => (option === "0" ? "Unhelpful" : "Helpful")}
                    />
                  )}
                </form.Field>
              </Box>

              {/* Status Code */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Status Code
                </Typography>
                <form.Field name="statusCode">
                  {(field) => (
                    <Autocomplete
                      options={STATUS_CODE_OPTIONS}
                      value={field.state.value}
                      onChange={(_, newValue) => field.handleChange(newValue)}
                      renderInput={(params) => <TextField {...params} size="small" placeholder="Select status" />}
                      getOptionLabel={(option) => (option === "Ok" ? "Pass" : "Fail")}
                    />
                  )}
                </form.Field>
              </Box>

              {/* Annotation Type */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Annotation Type
                </Typography>
                <form.Field name="annotationType">
                  {(field) => (
                    <Autocomplete
                      options={ANNOTATION_TYPE_OPTIONS}
                      value={field.state.value}
                      onChange={(_, newValue) => field.handleChange(newValue)}
                      renderInput={(params) => <TextField {...params} size="small" placeholder="Select type" />}
                      getOptionLabel={(option) => (option === "human" ? "Human" : "Continuous Eval")}
                    />
                  )}
                </form.Field>
              </Box>

              {/* Continuous Eval Run Status */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Continuous Eval Run Status
                </Typography>
                <form.Field name="continuousEvalRunStatus">
                  {(field) => (
                    <Autocomplete
                      options={CONTINUOUS_EVAL_RUN_STATUS_OPTIONS}
                      value={field.state.value}
                      onChange={(_, newValue) => field.handleChange(newValue)}
                      renderInput={(params) => <TextField {...params} size="small" placeholder="Select status" />}
                      getOptionLabel={(option) => option.charAt(0).toUpperCase() + option.slice(1)}
                    />
                  )}
                </form.Field>
              </Box>

              {/* Continuous Eval Name */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Continuous Eval Name
                </Typography>
                <form.Field name="continuousEvalName">
                  {(field) => (
                    <TextField
                      size="small"
                      fullWidth
                      value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      placeholder="Enter continuous eval name"
                      slotProps={{
                        input: {
                          endAdornment: field.state.value && (
                            <IconButton size="small" onClick={() => field.handleChange("")} sx={{ mr: -1 }}>
                              <Close fontSize="small" />
                            </IconButton>
                          ),
                        },
                      }}
                    />
                  )}
                </form.Field>
              </Box>

              {/* Include Experiment Traces */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Include Experiment Traces
                </Typography>
                <form.Field name="includeExperimentTraces">
                  {(field) => (
                    <Autocomplete
                      options={INCLUDE_EXPERIMENT_TRACES_OPTIONS}
                      value={field.state.value}
                      onChange={(_, newValue) => field.handleChange(newValue)}
                      renderInput={(params) => <TextField {...params} size="small" placeholder="Select option" />}
                      getOptionLabel={(option) => (option === "true" ? "Yes" : "No")}
                    />
                  )}
                </form.Field>
              </Box>
            </Stack>
          </Box>

          {/* Action Buttons */}
          <Box
            sx={{
              p: 2,
              borderTop: "1px solid",
              borderColor: "divider",
              backgroundColor: "background.paper",
            }}
          >
            <Stack direction="row" spacing={2} justifyContent="flex-end">
              <Button variant="outlined" onClick={handleClearFilters} disabled={!hasActiveFilters}>
                Clear
              </Button>
              <Button
                variant="contained"
                onClick={(e) => {
                  e.preventDefault();
                  form.handleSubmit();
                }}
              >
                Apply Filters
              </Button>
            </Stack>
          </Box>
        </Paper>
      </Popover>
    </>
  );
};
