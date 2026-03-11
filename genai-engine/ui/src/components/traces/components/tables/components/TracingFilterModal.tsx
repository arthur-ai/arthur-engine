import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { Add, Close, FilterList } from "@mui/icons-material";
import { Autocomplete, Box, Button, Checkbox, Chip, FormControlLabel, IconButton, Paper, Popover, Stack, TextField, Typography } from "@mui/material";
import { useForm, useStore } from "@tanstack/react-form";
import { useEffect, useRef, useState } from "react";

import { useFilterStore } from "../../../stores/filter.store";
import type { IncomingFilter } from "../../filtering/mapper";
import { EnumOperators, Operators, TextOperators } from "../../filtering/types";

interface FilterState {
  spanTypes: string[];
  traceDurationMin: string;
  traceDurationMax: string;
  traceDurationInclusive: boolean;
  spanCountMin: string;
  spanCountMax: string;
  spanCountInclusive: boolean;
  totalTokenCountMin: string;
  totalTokenCountMax: string;
  totalTokenCountInclusive: boolean;
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
}

interface ValidationErrors {
  traceDurationMin?: string;
  traceDurationMax?: string;
  spanCountMin?: string;
  spanCountMax?: string;
  totalTokenCountMin?: string;
  totalTokenCountMax?: string;
}

interface TracingFilterModalProps {
  mode?: "trace" | "span";
}

const SPAN_TYPE_OPTIONS = Object.values(OpenInferenceSpanKind);
const ANNOTATION_SCORE_OPTIONS = ["0", "1"];
const STATUS_CODE_OPTIONS = ["Ok", "Error"];
const ANNOTATION_TYPE_OPTIONS = ["human", "continuous_eval"];
const CONTINUOUS_EVAL_RUN_STATUS_OPTIONS = ["pending", "passed", "running", "failed", "skipped", "error"];
const INCLUDE_EXPERIMENT_TRACES_OPTIONS = ["true", "false"];

// Helper function to build filters from form values
const buildFiltersFromFormValues = (value: FilterState, includeSpanCount: boolean): IncomingFilter[] => {
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

  // Span Count (trace mode only)
  if (includeSpanCount) {
    if (value.spanCountMin && value.spanCountMax && value.spanCountMin === value.spanCountMax) {
      filters.push({
        name: "span_count",
        operator: Operators.EQUALS,
        value: value.spanCountMin,
      });
    } else {
      if (value.spanCountMin) {
        filters.push({
          name: "span_count",
          operator: value.spanCountInclusive ? Operators.GREATER_THAN_OR_EQUAL : Operators.GREATER_THAN,
          value: value.spanCountMin,
        });
      }
      if (value.spanCountMax) {
        filters.push({
          name: "span_count",
          operator: value.spanCountInclusive ? Operators.LESS_THAN_OR_EQUAL : Operators.LESS_THAN,
          value: value.spanCountMax,
        });
      }
    }
  }

  // Total Token Count
  if (value.totalTokenCountMin && value.totalTokenCountMax && value.totalTokenCountMin === value.totalTokenCountMax) {
    filters.push({
      name: "total_token_count",
      operator: Operators.EQUALS,
      value: value.totalTokenCountMin,
    });
  } else {
    if (value.totalTokenCountMin) {
      filters.push({
        name: "total_token_count",
        operator: value.totalTokenCountInclusive ? Operators.GREATER_THAN_OR_EQUAL : Operators.GREATER_THAN,
        value: value.totalTokenCountMin,
      });
    }
    if (value.totalTokenCountMax) {
      filters.push({
        name: "total_token_count",
        operator: value.totalTokenCountInclusive ? Operators.LESS_THAN_OR_EQUAL : Operators.LESS_THAN,
        value: value.totalTokenCountMax,
      });
    }
  }

  // IDs
  if (value.traceIds.length > 0) {
    filters.push({
      name: "trace_ids",
      operator: Operators.IN,
      value: value.traceIds,
    });
  }
  if (value.sessionIds.length > 0) {
    filters.push({
      name: "session_ids",
      operator: Operators.IN,
      value: value.sessionIds,
    });
  }
  if (value.spanIds.length > 0) {
    filters.push({
      name: "span_ids",
      operator: Operators.IN,
      value: value.spanIds,
    });
  }
  if (value.userIds.length > 0) {
    filters.push({
      name: "user_ids",
      operator: Operators.IN,
      value: value.userIds,
    });
  }

  // Annotation Score
  if (value.annotationScore !== null) {
    filters.push({
      name: "annotation_score",
      operator: EnumOperators.EQUALS,
      value: value.annotationScore,
    });
  }

  // Status Code
  if (value.statusCode !== null) {
    filters.push({
      name: "status_code",
      operator: EnumOperators.EQUALS,
      value: value.statusCode,
    });
  }

  // Annotation Type
  if (value.annotationType !== null) {
    filters.push({
      name: "annotation_type",
      operator: EnumOperators.EQUALS,
      value: value.annotationType,
    });
  }

  // Continuous Eval Run Status
  if (value.continuousEvalRunStatus !== null) {
    filters.push({
      name: "continuous_eval_run_status",
      operator: EnumOperators.EQUALS,
      value: value.continuousEvalRunStatus,
    });
  }

  // Continuous Eval Name
  if (value.continuousEvalName.trim()) {
    filters.push({
      name: "continuous_eval_name",
      operator: TextOperators.CONTAINS,
      value: value.continuousEvalName.trim(),
    });
  }

  // Include Experiment Traces
  if (value.includeExperimentTraces !== null) {
    filters.push({
      name: "include_experiment_traces",
      operator: EnumOperators.EQUALS,
      value: value.includeExperimentTraces,
    });
  }

  return filters;
};

export const TracingFilterModal = ({ mode = "trace" }: TracingFilterModalProps) => {
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

  // Initialize form with @tanstack/react-form
  const form = useForm({
    defaultValues: {
      spanTypes: [] as string[],
      traceDurationMin: "",
      traceDurationMax: "",
      traceDurationInclusive: false,
      spanCountMin: "",
      spanCountMax: "",
      spanCountInclusive: false,
      totalTokenCountMin: "",
      totalTokenCountMax: "",
      totalTokenCountInclusive: false,
      traceIds: [] as string[],
      sessionIds: [] as string[],
      spanIds: [] as string[],
      userIds: [] as string[],
      annotationScore: null as string | null,
      statusCode: null as string | null,
      annotationType: null as string | null,
      continuousEvalRunStatus: null as string | null,
      continuousEvalName: "",
      includeExperimentTraces: null as string | null,
    },
    onSubmit: async ({ value }) => {
      const filters = buildFiltersFromFormValues(value as FilterState, mode === "trace");
      setPendingFilters(filters);
      handleClose();
    },
  });

  // Populate form from currentFilters when modal opens
  useEffect(() => {
    if (!open) return;

    const newFilterState: FilterState = {
      spanTypes: [],
      traceDurationMin: "",
      traceDurationMax: "",
      traceDurationInclusive: false,
      spanCountMin: "",
      spanCountMax: "",
      spanCountInclusive: false,
      totalTokenCountMin: "",
      totalTokenCountMax: "",
      totalTokenCountInclusive: false,
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
    };

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
        case "span_count":
          if (filter.operator === Operators.GREATER_THAN || filter.operator === Operators.GREATER_THAN_OR_EQUAL) {
            newFilterState.spanCountMin = String(filter.value);
            newFilterState.spanCountInclusive = filter.operator === Operators.GREATER_THAN_OR_EQUAL;
          } else if (filter.operator === Operators.LESS_THAN || filter.operator === Operators.LESS_THAN_OR_EQUAL) {
            newFilterState.spanCountMax = String(filter.value);
            newFilterState.spanCountInclusive = filter.operator === Operators.LESS_THAN_OR_EQUAL;
          } else if (filter.operator === Operators.EQUALS) {
            newFilterState.spanCountMin = String(filter.value);
            newFilterState.spanCountMax = String(filter.value);
          }
          break;
        case "total_token_count":
          if (filter.operator === Operators.GREATER_THAN || filter.operator === Operators.GREATER_THAN_OR_EQUAL) {
            newFilterState.totalTokenCountMin = String(filter.value);
            newFilterState.totalTokenCountInclusive = filter.operator === Operators.GREATER_THAN_OR_EQUAL;
          } else if (filter.operator === Operators.LESS_THAN || filter.operator === Operators.LESS_THAN_OR_EQUAL) {
            newFilterState.totalTokenCountMax = String(filter.value);
            newFilterState.totalTokenCountInclusive = filter.operator === Operators.LESS_THAN_OR_EQUAL;
          } else if (filter.operator === Operators.EQUALS) {
            newFilterState.totalTokenCountMin = String(filter.value);
            newFilterState.totalTokenCountMax = String(filter.value);
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
      // Preserve span_name filter from search bar
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
    // Preserve span_name filter from search bar
    const spanNameFilter = currentFilters.find((f) => f.name === "span_name");
    setFilters(spanNameFilter ? [spanNameFilter] : []);
  };

  // Subscribe to form state to check for active filters
  const formState = useStore(form.store, (state) => state.values);
  const hasActiveFilters =
    formState.spanTypes.length > 0 ||
    formState.traceDurationMin !== "" ||
    formState.traceDurationMax !== "" ||
    (mode === "trace" && (formState.spanCountMin !== "" || formState.spanCountMax !== "")) ||
    formState.totalTokenCountMin !== "" ||
    formState.totalTokenCountMax !== "" ||
    formState.traceIds.length > 0 ||
    formState.sessionIds.length > 0 ||
    formState.spanIds.length > 0 ||
    formState.userIds.length > 0 ||
    formState.annotationScore !== null ||
    formState.statusCode !== null ||
    formState.annotationType !== null ||
    formState.continuousEvalRunStatus !== null ||
    formState.continuousEvalName.trim() !== "" ||
    formState.includeExperimentTraces !== null;

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
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "left",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "left",
        }}
        slotProps={{
          transition: {
            onExited: handleExited,
          },
        }}
        transitionDuration={150}
      >
        <Paper sx={{ width: 400, maxHeight: 600, display: "flex", flexDirection: "column" }}>
          <Box sx={{ p: 2, overflowY: "auto", flex: 1 }}>
            <Stack spacing={3}>
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
                          onChange={(e) => {
                            const val = e.target.value;
                            setValidationErrors((prev) => ({ ...prev, traceDurationMin: undefined, traceDurationMax: undefined }));
                            if (val === "") {
                              field.handleChange(val);
                              return;
                            }
                            const numVal = parseFloat(val);
                            if (numVal < 0) {
                              field.handleChange("0");
                              setValidationErrors((prev) => ({ ...prev, traceDurationMin: "Value cannot be less than 0. Reset to 0." }));
                            } else {
                              field.handleChange(val);
                            }
                          }}
                          slotProps={{
                            htmlInput: {
                              min: 0,
                              step: 1,
                              style: { MozAppearance: "textfield" },
                            },
                          }}
                          sx={{
                            width: 100,
                            "& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button": {
                              WebkitAppearance: "none",
                              margin: 0,
                            },
                          }}
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
                          onChange={(e) => {
                            const val = e.target.value;
                            const minVal = form.getFieldValue("traceDurationMin");
                            setValidationErrors((prev) => ({ ...prev, traceDurationMin: undefined, traceDurationMax: undefined }));
                            if (val === "") {
                              field.handleChange(val);
                              return;
                            }
                            const numVal = parseFloat(val);
                            if (numVal < 0) {
                              field.handleChange("0");
                              setValidationErrors((prev) => ({ ...prev, traceDurationMax: "Value cannot be less than 0. Reset to 0." }));
                            } else if (minVal && numVal < parseFloat(minVal)) {
                              setValidationErrors((prev) => ({ ...prev, traceDurationMax: "Max cannot be less than min." }));
                              field.handleChange(val);
                            } else {
                              field.handleChange(val);
                            }
                          }}
                          slotProps={{
                            htmlInput: {
                              min: 0,
                              step: 1,
                              style: { MozAppearance: "textfield" },
                            },
                          }}
                          sx={{
                            width: 100,
                            "& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button": {
                              WebkitAppearance: "none",
                              margin: 0,
                            },
                          }}
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

              {/* Span Count - trace mode only */}
              {mode === "trace" && (
                <Box>
                  <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                    Span Count
                  </Typography>
                  <Stack spacing={1}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <form.Field name="spanCountMin">
                        {(field) => (
                          <TextField
                            size="small"
                            type="number"
                            placeholder="Min"
                            value={field.state.value}
                            onChange={(e) => {
                              const val = e.target.value;
                              setValidationErrors((prev) => ({ ...prev, spanCountMin: undefined, spanCountMax: undefined }));
                              if (val === "") {
                                field.handleChange(val);
                                return;
                              }
                              const numVal = parseFloat(val);
                              if (numVal < 1) {
                                field.handleChange("1");
                                setValidationErrors((prev) => ({ ...prev, spanCountMin: "Value cannot be less than 1. Reset to 1." }));
                              } else {
                                field.handleChange(val);
                              }
                            }}
                            slotProps={{
                              htmlInput: {
                                min: 1,
                                step: 1,
                                style: { MozAppearance: "textfield" },
                              },
                            }}
                            sx={{
                              width: 100,
                              "& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button": {
                                WebkitAppearance: "none",
                                margin: 0,
                              },
                            }}
                          />
                        )}
                      </form.Field>
                      <form.Field name="spanCountMax">
                        {(field) => (
                          <TextField
                            size="small"
                            type="number"
                            placeholder="Max"
                            value={field.state.value}
                            onChange={(e) => {
                              const val = e.target.value;
                              const minVal = form.getFieldValue("spanCountMin");
                              setValidationErrors((prev) => ({ ...prev, spanCountMin: undefined, spanCountMax: undefined }));
                              if (val === "") {
                                field.handleChange(val);
                                return;
                              }
                              const numVal = parseFloat(val);
                              if (numVal < 1) {
                                field.handleChange("1");
                                setValidationErrors((prev) => ({ ...prev, spanCountMax: "Value cannot be less than 1. Reset to 1." }));
                              } else if (minVal && numVal < parseFloat(minVal)) {
                                setValidationErrors((prev) => ({ ...prev, spanCountMax: "Max cannot be less than min." }));
                                field.handleChange(val);
                              } else {
                                field.handleChange(val);
                              }
                            }}
                            slotProps={{
                              htmlInput: {
                                min: 1,
                                step: 1,
                                style: { MozAppearance: "textfield" },
                              },
                            }}
                            sx={{
                              width: 100,
                              "& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button": {
                                WebkitAppearance: "none",
                                margin: 0,
                              },
                            }}
                          />
                        )}
                      </form.Field>
                      <form.Field name="spanCountInclusive">
                        {(field) => (
                          <FormControlLabel
                            control={<Checkbox checked={field.state.value} onChange={(e) => field.handleChange(e.target.checked)} size="small" />}
                            label="Inclusive"
                            sx={{ whiteSpace: "nowrap" }}
                          />
                        )}
                      </form.Field>
                    </Stack>
                    {(validationErrors.spanCountMin || validationErrors.spanCountMax) && (
                      <Typography variant="caption" color="error">
                        {validationErrors.spanCountMin || validationErrors.spanCountMax}
                      </Typography>
                    )}
                  </Stack>
                </Box>
              )}

              {/* Token Count */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Token Count
                </Typography>
                <Stack spacing={1}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <form.Field name="totalTokenCountMin">
                      {(field) => (
                        <TextField
                          size="small"
                          type="number"
                          placeholder="Min"
                          value={field.state.value}
                          onChange={(e) => {
                            const val = e.target.value;
                            setValidationErrors((prev) => ({ ...prev, totalTokenCountMin: undefined, totalTokenCountMax: undefined }));
                            if (val === "") {
                              field.handleChange(val);
                              return;
                            }
                            const numVal = parseFloat(val);
                            if (numVal < 1) {
                              field.handleChange("1");
                              setValidationErrors((prev) => ({ ...prev, totalTokenCountMin: "Value cannot be less than 1. Reset to 1." }));
                            } else {
                              field.handleChange(val);
                            }
                          }}
                          slotProps={{
                            htmlInput: {
                              min: 1,
                              step: 1,
                              style: { MozAppearance: "textfield" },
                            },
                          }}
                          sx={{
                            width: 100,
                            "& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button": {
                              WebkitAppearance: "none",
                              margin: 0,
                            },
                          }}
                        />
                      )}
                    </form.Field>
                    <form.Field name="totalTokenCountMax">
                      {(field) => (
                        <TextField
                          size="small"
                          type="number"
                          placeholder="Max"
                          value={field.state.value}
                          onChange={(e) => {
                            const val = e.target.value;
                            const minVal = form.getFieldValue("totalTokenCountMin");
                            setValidationErrors((prev) => ({ ...prev, totalTokenCountMin: undefined, totalTokenCountMax: undefined }));
                            if (val === "") {
                              field.handleChange(val);
                              return;
                            }
                            const numVal = parseFloat(val);
                            if (numVal < 1) {
                              field.handleChange("1");
                              setValidationErrors((prev) => ({ ...prev, totalTokenCountMax: "Value cannot be less than 1. Reset to 1." }));
                            } else if (minVal && numVal < parseFloat(minVal)) {
                              setValidationErrors((prev) => ({ ...prev, totalTokenCountMax: "Max cannot be less than min." }));
                              field.handleChange(val);
                            } else {
                              field.handleChange(val);
                            }
                          }}
                          slotProps={{
                            htmlInput: {
                              min: 1,
                              step: 1,
                              style: { MozAppearance: "textfield" },
                            },
                          }}
                          sx={{
                            width: 100,
                            "& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button": {
                              WebkitAppearance: "none",
                              margin: 0,
                            },
                          }}
                        />
                      )}
                    </form.Field>
                    <form.Field name="totalTokenCountInclusive">
                      {(field) => (
                        <FormControlLabel
                          control={<Checkbox checked={field.state.value} onChange={(e) => field.handleChange(e.target.checked)} size="small" />}
                          label="Inclusive"
                          sx={{ whiteSpace: "nowrap" }}
                        />
                      )}
                    </form.Field>
                  </Stack>
                  {(validationErrors.totalTokenCountMin || validationErrors.totalTokenCountMax) && (
                    <Typography variant="caption" color="error">
                      {validationErrors.totalTokenCountMin || validationErrors.totalTokenCountMax}
                    </Typography>
                  )}
                </Stack>
              </Box>

              {/* Trace IDs */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Trace ID
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                  <TextField
                    size="small"
                    fullWidth
                    value={traceIdInput}
                    onChange={(e) => setTraceIdInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddId("trace", traceIdInput);
                      }
                    }}
                    placeholder="Enter Trace ID"
                  />
                  <IconButton size="small" onClick={() => handleAddId("trace", traceIdInput)} disabled={!traceIdInput.trim()} color="primary">
                    <Add />
                  </IconButton>
                </Stack>
                <form.Field name="traceIds">
                  {(field) => (
                    <Stack direction="row" flexWrap="wrap" gap={1}>
                      {field.state.value.map((id) => (
                        <Chip key={id} label={id} size="small" onDelete={() => handleRemoveId("trace", id)} deleteIcon={<Close />} />
                      ))}
                    </Stack>
                  )}
                </form.Field>
              </Box>

              {/* Session IDs */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Session ID
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                  <TextField
                    size="small"
                    fullWidth
                    value={sessionIdInput}
                    onChange={(e) => setSessionIdInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddId("session", sessionIdInput);
                      }
                    }}
                    placeholder="Enter Session ID"
                  />
                  <IconButton size="small" onClick={() => handleAddId("session", sessionIdInput)} disabled={!sessionIdInput.trim()} color="primary">
                    <Add />
                  </IconButton>
                </Stack>
                <form.Field name="sessionIds">
                  {(field) => (
                    <Stack direction="row" flexWrap="wrap" gap={1}>
                      {field.state.value.map((id) => (
                        <Chip key={id} label={id} size="small" onDelete={() => handleRemoveId("session", id)} deleteIcon={<Close />} />
                      ))}
                    </Stack>
                  )}
                </form.Field>
              </Box>

              {/* Span IDs */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Span ID
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                  <TextField
                    size="small"
                    fullWidth
                    value={spanIdInput}
                    onChange={(e) => setSpanIdInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddId("span", spanIdInput);
                      }
                    }}
                    placeholder="Enter Span ID"
                  />
                  <IconButton size="small" onClick={() => handleAddId("span", spanIdInput)} disabled={!spanIdInput.trim()} color="primary">
                    <Add />
                  </IconButton>
                </Stack>
                <form.Field name="spanIds">
                  {(field) => (
                    <Stack direction="row" flexWrap="wrap" gap={1}>
                      {field.state.value.map((id) => (
                        <Chip key={id} label={id} size="small" onDelete={() => handleRemoveId("span", id)} deleteIcon={<Close />} />
                      ))}
                    </Stack>
                  )}
                </form.Field>
              </Box>

              {/* User IDs */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  User ID
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                  <TextField
                    size="small"
                    fullWidth
                    value={userIdInput}
                    onChange={(e) => setUserIdInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddId("user", userIdInput);
                      }
                    }}
                    placeholder="Enter User ID"
                  />
                  <IconButton size="small" onClick={() => handleAddId("user", userIdInput)} disabled={!userIdInput.trim()} color="primary">
                    <Add />
                  </IconButton>
                </Stack>
                <form.Field name="userIds">
                  {(field) => (
                    <Stack direction="row" flexWrap="wrap" gap={1}>
                      {field.state.value.map((id) => (
                        <Chip key={id} label={id} size="small" onDelete={() => handleRemoveId("user", id)} deleteIcon={<Close />} />
                      ))}
                    </Stack>
                  )}
                </form.Field>
              </Box>

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

          {/* Action Buttons - Sticky at bottom */}
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
