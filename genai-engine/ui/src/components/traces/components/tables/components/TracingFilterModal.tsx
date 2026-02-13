import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { Add, Close, FilterList } from "@mui/icons-material";
import { Autocomplete, Box, Button, Checkbox, Chip, FormControlLabel, IconButton, Paper, Popover, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useState } from "react";

import { useFilterStore } from "../../../stores/filter.store";
import type { IncomingFilter } from "../../filtering/mapper";
import { EnumOperators, Operators, TextOperators } from "../../filtering/types";

interface FilterState {
  spanTypes: string[];
  queryRelevanceMin: string;
  queryRelevanceMax: string;
  queryRelevanceInclusive: boolean;
  responseRelevanceMin: string;
  responseRelevanceMax: string;
  responseRelevanceInclusive: boolean;
  traceDurationMin: string;
  traceDurationMax: string;
  traceDurationInclusive: boolean;
  toolSelection: string | null;
  toolUsage: string | null;
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
  queryRelevanceMin?: string;
  queryRelevanceMax?: string;
  responseRelevanceMin?: string;
  responseRelevanceMax?: string;
  traceDurationMin?: string;
  traceDurationMax?: string;
}

const SPAN_TYPE_OPTIONS = Object.values(OpenInferenceSpanKind);
const TOOL_OPTIONS = ["0", "1", "2"];
const ANNOTATION_SCORE_OPTIONS = ["0", "1"];
const STATUS_CODE_OPTIONS = ["Ok", "Error"];
const ANNOTATION_TYPE_OPTIONS = ["human", "continuous_eval"];
const CONTINUOUS_EVAL_RUN_STATUS_OPTIONS = ["pending", "passed", "running", "failed", "skipped", "error"];
const INCLUDE_EXPERIMENT_TRACES_OPTIONS = ["true", "false"];

const getToolLabel = (option: string) => {
  const labels: Record<string, string> = { "0": "NOT RELEVANT", "1": "RELEVANT", "2": "N/A" };
  return labels[option] || option;
};

export const TracingFilterModal = () => {
  const [anchorEl, setAnchorEl] = useState<HTMLButtonElement | null>(null);
  const setFilters = useFilterStore((state) => state.setFilters);
  const currentFilters = useFilterStore((state) => state.filters);

  const [filterState, setFilterState] = useState<FilterState>({
    spanTypes: [],
    queryRelevanceMin: "",
    queryRelevanceMax: "",
    queryRelevanceInclusive: false,
    responseRelevanceMin: "",
    responseRelevanceMax: "",
    responseRelevanceInclusive: false,
    traceDurationMin: "",
    traceDurationMax: "",
    traceDurationInclusive: false,
    toolSelection: null,
    toolUsage: null,
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
  });

  const [traceIdInput, setTraceIdInput] = useState("");
  const [sessionIdInput, setSessionIdInput] = useState("");
  const [spanIdInput, setSpanIdInput] = useState("");
  const [userIdInput, setUserIdInput] = useState("");
  const [pendingFilters, setPendingFilters] = useState<IncomingFilter[] | null>(null);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});

  const open = Boolean(anchorEl);

  // Populate filter state from currentFilters when modal opens
  useEffect(() => {
    if (open) {
      const newFilterState: FilterState = {
        spanTypes: [],
        queryRelevanceMin: "",
        queryRelevanceMax: "",
        queryRelevanceInclusive: false,
        responseRelevanceMin: "",
        responseRelevanceMax: "",
        responseRelevanceInclusive: false,
        traceDurationMin: "",
        traceDurationMax: "",
        traceDurationInclusive: false,
        toolSelection: null,
        toolUsage: null,
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
          case "query_relevance":
            if (filter.operator === Operators.GREATER_THAN || filter.operator === Operators.GREATER_THAN_OR_EQUAL) {
              newFilterState.queryRelevanceMin = String(filter.value);
              newFilterState.queryRelevanceInclusive = filter.operator === Operators.GREATER_THAN_OR_EQUAL;
            } else if (filter.operator === Operators.LESS_THAN || filter.operator === Operators.LESS_THAN_OR_EQUAL) {
              newFilterState.queryRelevanceMax = String(filter.value);
              newFilterState.queryRelevanceInclusive = filter.operator === Operators.LESS_THAN_OR_EQUAL;
            } else if (filter.operator === Operators.EQUALS) {
              newFilterState.queryRelevanceMin = String(filter.value);
              newFilterState.queryRelevanceMax = String(filter.value);
            }
            break;
          case "response_relevance":
            if (filter.operator === Operators.GREATER_THAN || filter.operator === Operators.GREATER_THAN_OR_EQUAL) {
              newFilterState.responseRelevanceMin = String(filter.value);
              newFilterState.responseRelevanceInclusive = filter.operator === Operators.GREATER_THAN_OR_EQUAL;
            } else if (filter.operator === Operators.LESS_THAN || filter.operator === Operators.LESS_THAN_OR_EQUAL) {
              newFilterState.responseRelevanceMax = String(filter.value);
              newFilterState.responseRelevanceInclusive = filter.operator === Operators.LESS_THAN_OR_EQUAL;
            } else if (filter.operator === Operators.EQUALS) {
              newFilterState.responseRelevanceMin = String(filter.value);
              newFilterState.responseRelevanceMax = String(filter.value);
            }
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
          case "tool_selection":
            newFilterState.toolSelection = String(filter.value);
            break;
          case "tool_usage":
            newFilterState.toolUsage = String(filter.value);
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

      setFilterState(newFilterState);
    }
  }, [open, currentFilters]);

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
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
      setFilterState((prev) => ({
        ...prev,
        [`${type}Ids`]: [...prev[`${type}Ids` as keyof FilterState] as string[], value.trim()],
      }));
      if (type === "trace") setTraceIdInput("");
      if (type === "session") setSessionIdInput("");
      if (type === "span") setSpanIdInput("");
      if (type === "user") setUserIdInput("");
    }
  };

  const handleRemoveId = (type: "trace" | "session" | "span" | "user", id: string) => {
    setFilterState((prev) => ({
      ...prev,
      [`${type}Ids`]: (prev[`${type}Ids` as keyof FilterState] as string[]).filter((item) => item !== id),
    }));
  };

  const handleApplyFilters = () => {
    const filters: IncomingFilter[] = [];

    // Span Types
    if (filterState.spanTypes.length > 0) {
      filters.push({
        name: "span_types",
        operator: Operators.IN,
        value: filterState.spanTypes,
      });
    }

    // Query Relevance
    if (filterState.queryRelevanceMin && filterState.queryRelevanceMax && filterState.queryRelevanceMin === filterState.queryRelevanceMax) {
      // If min and max are the same, use EQUALS
      filters.push({
        name: "query_relevance",
        operator: Operators.EQUALS,
        value: filterState.queryRelevanceMin,
      });
    } else {
      if (filterState.queryRelevanceMin) {
        filters.push({
          name: "query_relevance",
          operator: filterState.queryRelevanceInclusive ? Operators.GREATER_THAN_OR_EQUAL : Operators.GREATER_THAN,
          value: filterState.queryRelevanceMin,
        });
      }
      if (filterState.queryRelevanceMax) {
        filters.push({
          name: "query_relevance",
          operator: filterState.queryRelevanceInclusive ? Operators.LESS_THAN_OR_EQUAL : Operators.LESS_THAN,
          value: filterState.queryRelevanceMax,
        });
      }
    }

    // Response Relevance
    if (filterState.responseRelevanceMin && filterState.responseRelevanceMax && filterState.responseRelevanceMin === filterState.responseRelevanceMax) {
      // If min and max are the same, use EQUALS
      filters.push({
        name: "response_relevance",
        operator: Operators.EQUALS,
        value: filterState.responseRelevanceMin,
      });
    } else {
      if (filterState.responseRelevanceMin) {
        filters.push({
          name: "response_relevance",
          operator: filterState.responseRelevanceInclusive ? Operators.GREATER_THAN_OR_EQUAL : Operators.GREATER_THAN,
          value: filterState.responseRelevanceMin,
        });
      }
      if (filterState.responseRelevanceMax) {
        filters.push({
          name: "response_relevance",
          operator: filterState.responseRelevanceInclusive ? Operators.LESS_THAN_OR_EQUAL : Operators.LESS_THAN,
          value: filterState.responseRelevanceMax,
        });
      }
    }

    // Trace Duration
    if (filterState.traceDurationMin && filterState.traceDurationMax && filterState.traceDurationMin === filterState.traceDurationMax) {
      // If min and max are the same, use EQUALS
      filters.push({
        name: "trace_duration",
        operator: Operators.EQUALS,
        value: filterState.traceDurationMin,
      });
    } else {
      if (filterState.traceDurationMin) {
        filters.push({
          name: "trace_duration",
          operator: filterState.traceDurationInclusive ? Operators.GREATER_THAN_OR_EQUAL : Operators.GREATER_THAN,
          value: filterState.traceDurationMin,
        });
      }
      if (filterState.traceDurationMax) {
        filters.push({
          name: "trace_duration",
          operator: filterState.traceDurationInclusive ? Operators.LESS_THAN_OR_EQUAL : Operators.LESS_THAN,
          value: filterState.traceDurationMax,
        });
      }
    }

    // Tool Selection
    if (filterState.toolSelection !== null) {
      filters.push({
        name: "tool_selection",
        operator: EnumOperators.EQUALS,
        value: filterState.toolSelection,
      });
    }

    // Tool Usage
    if (filterState.toolUsage !== null) {
      filters.push({
        name: "tool_usage",
        operator: EnumOperators.EQUALS,
        value: filterState.toolUsage,
      });
    }

    // IDs
    if (filterState.traceIds.length > 0) {
      filters.push({
        name: "trace_ids",
        operator: Operators.IN,
        value: filterState.traceIds,
      });
    }
    if (filterState.sessionIds.length > 0) {
      filters.push({
        name: "session_ids",
        operator: Operators.IN,
        value: filterState.sessionIds,
      });
    }
    if (filterState.spanIds.length > 0) {
      filters.push({
        name: "span_ids",
        operator: Operators.IN,
        value: filterState.spanIds,
      });
    }
    if (filterState.userIds.length > 0) {
      filters.push({
        name: "user_ids",
        operator: Operators.IN,
        value: filterState.userIds,
      });
    }

    // Annotation Score
    if (filterState.annotationScore !== null) {
      filters.push({
        name: "annotation_score",
        operator: EnumOperators.EQUALS,
        value: filterState.annotationScore,
      });
    }

    // Status Code
    if (filterState.statusCode !== null) {
      filters.push({
        name: "status_code",
        operator: EnumOperators.EQUALS,
        value: filterState.statusCode,
      });
    }

    // Annotation Type
    if (filterState.annotationType !== null) {
      filters.push({
        name: "annotation_type",
        operator: EnumOperators.EQUALS,
        value: filterState.annotationType,
      });
    }

    // Continuous Eval Run Status
    if (filterState.continuousEvalRunStatus !== null) {
      filters.push({
        name: "continuous_eval_run_status",
        operator: EnumOperators.EQUALS,
        value: filterState.continuousEvalRunStatus,
      });
    }

    // Continuous Eval Name
    if (filterState.continuousEvalName.trim()) {
      filters.push({
        name: "continuous_eval_name",
        operator: TextOperators.CONTAINS,
        value: filterState.continuousEvalName.trim(),
      });
    }

    // Include Experiment Traces
    if (filterState.includeExperimentTraces !== null) {
      filters.push({
        name: "include_experiment_traces",
        operator: EnumOperators.EQUALS,
        value: filterState.includeExperimentTraces,
      });
    }

    setPendingFilters(filters);
    handleClose();
  };

  const handleClearFilters = () => {
    setFilterState({
      spanTypes: [],
      queryRelevanceMin: "",
      queryRelevanceMax: "",
      queryRelevanceInclusive: false,
      responseRelevanceMin: "",
      responseRelevanceMax: "",
      responseRelevanceInclusive: false,
      traceDurationMin: "",
      traceDurationMax: "",
      traceDurationInclusive: false,
      toolSelection: null,
      toolUsage: null,
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
    });
    // Clear all validation errors
    setValidationErrors({});
    // Preserve span_name filter from search bar
    const spanNameFilter = currentFilters.find((f) => f.name === "span_name");
    setFilters(spanNameFilter ? [spanNameFilter] : []);
  };

  const hasActiveFilters =
    filterState.spanTypes.length > 0 ||
    filterState.queryRelevanceMin !== "" ||
    filterState.queryRelevanceMax !== "" ||
    filterState.responseRelevanceMin !== "" ||
    filterState.responseRelevanceMax !== "" ||
    filterState.traceDurationMin !== "" ||
    filterState.traceDurationMax !== "" ||
    filterState.toolSelection !== null ||
    filterState.toolUsage !== null ||
    filterState.traceIds.length > 0 ||
    filterState.sessionIds.length > 0 ||
    filterState.spanIds.length > 0 ||
    filterState.userIds.length > 0 ||
    filterState.annotationScore !== null ||
    filterState.statusCode !== null ||
    filterState.annotationType !== null ||
    filterState.continuousEvalRunStatus !== null ||
    filterState.continuousEvalName.trim() !== "" ||
    filterState.includeExperimentTraces !== null;

  return (
    <>
      <Button variant="outlined" startIcon={<FilterList />} onClick={handleClick} color={hasActiveFilters ? "primary" : "inherit"}>
        Filter
      </Button>
      <Popover
        open={open}
        anchorEl={anchorEl}
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
                <Autocomplete
                  multiple
                  options={SPAN_TYPE_OPTIONS}
                  value={filterState.spanTypes}
                  onChange={(_, newValue) => setFilterState((prev) => ({ ...prev, spanTypes: newValue }))}
                  renderInput={(params) => <TextField {...params} size="small" placeholder="Select span types" />}
                  disableCloseOnSelect
                />
              </Box>

              {/* Query Relevance */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Query Relevance (0-1)
                </Typography>
                <Stack spacing={1}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <TextField
                      size="small"
                      type="number"
                      placeholder="Min"
                      value={filterState.queryRelevanceMin}
                      onChange={(e) => {
                        const val = e.target.value;
                        // Clear errors when user makes any change
                        setValidationErrors((prev) => ({ ...prev, queryRelevanceMin: undefined, queryRelevanceMax: undefined }));

                        if (val === "") {
                          setFilterState((prev) => ({ ...prev, queryRelevanceMin: val }));
                          return;
                        }
                        const numVal = parseFloat(val);
                        if (numVal < 0) {
                          setFilterState((prev) => ({ ...prev, queryRelevanceMin: "0" }));
                          setValidationErrors((prev) => ({ ...prev, queryRelevanceMin: "Value cannot be less than 0. Reset to 0." }));
                        } else if (numVal > 1) {
                          setFilterState((prev) => ({ ...prev, queryRelevanceMin: "1" }));
                          setValidationErrors((prev) => ({ ...prev, queryRelevanceMin: "Value cannot be greater than 1. Reset to 1." }));
                        } else {
                          setFilterState((prev) => ({ ...prev, queryRelevanceMin: val }));
                        }
                      }}
                      slotProps={{
                        htmlInput: {
                          min: 0,
                          max: 1,
                          step: 0.1,
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
                    <TextField
                      size="small"
                      type="number"
                      placeholder="Max"
                      value={filterState.queryRelevanceMax}
                      onChange={(e) => {
                        const val = e.target.value;
                        // Clear errors when user makes any change
                        setValidationErrors((prev) => ({ ...prev, queryRelevanceMin: undefined, queryRelevanceMax: undefined }));

                        if (val === "") {
                          setFilterState((prev) => ({ ...prev, queryRelevanceMax: val }));
                          return;
                        }
                        const numVal = parseFloat(val);
                        if (numVal < 0) {
                          setFilterState((prev) => ({ ...prev, queryRelevanceMax: "0" }));
                          setValidationErrors((prev) => ({ ...prev, queryRelevanceMax: "Value cannot be less than 0. Reset to 0." }));
                        } else if (numVal > 1) {
                          setFilterState((prev) => ({ ...prev, queryRelevanceMax: "1" }));
                          setValidationErrors((prev) => ({ ...prev, queryRelevanceMax: "Value cannot be greater than 1. Reset to 1." }));
                        } else if (filterState.queryRelevanceMin && numVal < parseFloat(filterState.queryRelevanceMin)) {
                          setValidationErrors((prev) => ({ ...prev, queryRelevanceMax: "Max cannot be less than min." }));
                          setFilterState((prev) => ({ ...prev, queryRelevanceMax: val }));
                        } else {
                          setFilterState((prev) => ({ ...prev, queryRelevanceMax: val }));
                        }
                      }}
                      slotProps={{
                        htmlInput: {
                          min: 0,
                          max: 1,
                          step: 0.1,
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
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={filterState.queryRelevanceInclusive}
                          onChange={(e) => setFilterState((prev) => ({ ...prev, queryRelevanceInclusive: e.target.checked }))}
                          size="small"
                        />
                      }
                      label="Inclusive"
                      sx={{ whiteSpace: "nowrap" }}
                    />
                  </Stack>
                  {(validationErrors.queryRelevanceMin || validationErrors.queryRelevanceMax) && (
                    <Typography variant="caption" color="error">
                      {validationErrors.queryRelevanceMin || validationErrors.queryRelevanceMax}
                    </Typography>
                  )}
                </Stack>
              </Box>

              {/* Response Relevance */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Response Relevance (0-1)
                </Typography>
                <Stack spacing={1}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <TextField
                      size="small"
                      type="number"
                      placeholder="Min"
                      value={filterState.responseRelevanceMin}
                      onChange={(e) => {
                        const val = e.target.value;
                        // Clear errors when user makes any change
                        setValidationErrors((prev) => ({ ...prev, responseRelevanceMin: undefined, responseRelevanceMax: undefined }));

                        if (val === "") {
                          setFilterState((prev) => ({ ...prev, responseRelevanceMin: val }));
                          return;
                        }
                        const numVal = parseFloat(val);
                        if (numVal < 0) {
                          setFilterState((prev) => ({ ...prev, responseRelevanceMin: "0" }));
                          setValidationErrors((prev) => ({ ...prev, responseRelevanceMin: "Value cannot be less than 0. Reset to 0." }));
                        } else if (numVal > 1) {
                          setFilterState((prev) => ({ ...prev, responseRelevanceMin: "1" }));
                          setValidationErrors((prev) => ({ ...prev, responseRelevanceMin: "Value cannot be greater than 1. Reset to 1." }));
                        } else {
                          setFilterState((prev) => ({ ...prev, responseRelevanceMin: val }));
                        }
                      }}
                      slotProps={{
                        htmlInput: {
                          min: 0,
                          max: 1,
                          step: 0.1,
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
                    <TextField
                      size="small"
                      type="number"
                      placeholder="Max"
                      value={filterState.responseRelevanceMax}
                      onChange={(e) => {
                        const val = e.target.value;
                        // Clear errors when user makes any change
                        setValidationErrors((prev) => ({ ...prev, responseRelevanceMin: undefined, responseRelevanceMax: undefined }));

                        if (val === "") {
                          setFilterState((prev) => ({ ...prev, responseRelevanceMax: val }));
                          return;
                        }
                        const numVal = parseFloat(val);
                        if (numVal < 0) {
                          setFilterState((prev) => ({ ...prev, responseRelevanceMax: "0" }));
                          setValidationErrors((prev) => ({ ...prev, responseRelevanceMax: "Value cannot be less than 0. Reset to 0." }));
                        } else if (numVal > 1) {
                          setFilterState((prev) => ({ ...prev, responseRelevanceMax: "1" }));
                          setValidationErrors((prev) => ({ ...prev, responseRelevanceMax: "Value cannot be greater than 1. Reset to 1." }));
                        } else if (filterState.responseRelevanceMin && numVal < parseFloat(filterState.responseRelevanceMin)) {
                          setValidationErrors((prev) => ({ ...prev, responseRelevanceMax: "Max cannot be less than min." }));
                          setFilterState((prev) => ({ ...prev, responseRelevanceMax: val }));
                        } else {
                          setFilterState((prev) => ({ ...prev, responseRelevanceMax: val }));
                        }
                      }}
                      slotProps={{
                        htmlInput: {
                          min: 0,
                          max: 1,
                          step: 0.1,
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
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={filterState.responseRelevanceInclusive}
                          onChange={(e) => setFilterState((prev) => ({ ...prev, responseRelevanceInclusive: e.target.checked }))}
                          size="small"
                        />
                      }
                      label="Inclusive"
                      sx={{ whiteSpace: "nowrap" }}
                    />
                  </Stack>
                  {(validationErrors.responseRelevanceMin || validationErrors.responseRelevanceMax) && (
                    <Typography variant="caption" color="error">
                      {validationErrors.responseRelevanceMin || validationErrors.responseRelevanceMax}
                    </Typography>
                  )}
                </Stack>
              </Box>

              {/* Trace Duration */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Trace Duration (ms)
                </Typography>
                <Stack spacing={1}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <TextField
                      size="small"
                      type="number"
                      placeholder="Min"
                      value={filterState.traceDurationMin}
                      onChange={(e) => {
                        const val = e.target.value;
                        // Clear errors when user makes any change
                        setValidationErrors((prev) => ({ ...prev, traceDurationMin: undefined, traceDurationMax: undefined }));

                        if (val === "") {
                          setFilterState((prev) => ({ ...prev, traceDurationMin: val }));
                          return;
                        }
                        const numVal = parseFloat(val);
                        if (numVal < 0) {
                          setFilterState((prev) => ({ ...prev, traceDurationMin: "0" }));
                          setValidationErrors((prev) => ({ ...prev, traceDurationMin: "Value cannot be less than 0. Reset to 0." }));
                        } else {
                          setFilterState((prev) => ({ ...prev, traceDurationMin: val }));
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
                    <TextField
                      size="small"
                      type="number"
                      placeholder="Max"
                      value={filterState.traceDurationMax}
                      onChange={(e) => {
                        const val = e.target.value;
                        // Clear errors when user makes any change
                        setValidationErrors((prev) => ({ ...prev, traceDurationMin: undefined, traceDurationMax: undefined }));

                        if (val === "") {
                          setFilterState((prev) => ({ ...prev, traceDurationMax: val }));
                          return;
                        }
                        const numVal = parseFloat(val);
                        if (numVal < 0) {
                          setFilterState((prev) => ({ ...prev, traceDurationMax: "0" }));
                          setValidationErrors((prev) => ({ ...prev, traceDurationMax: "Value cannot be less than 0. Reset to 0." }));
                        } else if (filterState.traceDurationMin && numVal < parseFloat(filterState.traceDurationMin)) {
                          setValidationErrors((prev) => ({ ...prev, traceDurationMax: "Max cannot be less than min." }));
                          setFilterState((prev) => ({ ...prev, traceDurationMax: val }));
                        } else {
                          setFilterState((prev) => ({ ...prev, traceDurationMax: val }));
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
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={filterState.traceDurationInclusive}
                          onChange={(e) => setFilterState((prev) => ({ ...prev, traceDurationInclusive: e.target.checked }))}
                          size="small"
                        />
                      }
                      label="Inclusive"
                      sx={{ whiteSpace: "nowrap" }}
                    />
                  </Stack>
                  {(validationErrors.traceDurationMin || validationErrors.traceDurationMax) && (
                    <Typography variant="caption" color="error">
                      {validationErrors.traceDurationMin || validationErrors.traceDurationMax}
                    </Typography>
                  )}
                </Stack>
              </Box>

              {/* Tool Selection */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Tool Selection
                </Typography>
                <Autocomplete
                  options={TOOL_OPTIONS}
                  value={filterState.toolSelection}
                  onChange={(_, newValue) => setFilterState((prev) => ({ ...prev, toolSelection: newValue }))}
                  renderInput={(params) => <TextField {...params} size="small" placeholder="Select tool selection" />}
                  getOptionLabel={getToolLabel}
                />
              </Box>

              {/* Tool Usage */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Tool Usage
                </Typography>
                <Autocomplete
                  options={TOOL_OPTIONS}
                  value={filterState.toolUsage}
                  onChange={(_, newValue) => setFilterState((prev) => ({ ...prev, toolUsage: newValue }))}
                  renderInput={(params) => <TextField {...params} size="small" placeholder="Select tool usage" />}
                  getOptionLabel={getToolLabel}
                />
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
                <Stack direction="row" flexWrap="wrap" gap={1}>
                  {filterState.traceIds.map((id) => (
                    <Chip key={id} label={id} size="small" onDelete={() => handleRemoveId("trace", id)} deleteIcon={<Close />} />
                  ))}
                </Stack>
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
                <Stack direction="row" flexWrap="wrap" gap={1}>
                  {filterState.sessionIds.map((id) => (
                    <Chip key={id} label={id} size="small" onDelete={() => handleRemoveId("session", id)} deleteIcon={<Close />} />
                  ))}
                </Stack>
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
                <Stack direction="row" flexWrap="wrap" gap={1}>
                  {filterState.spanIds.map((id) => (
                    <Chip key={id} label={id} size="small" onDelete={() => handleRemoveId("span", id)} deleteIcon={<Close />} />
                  ))}
                </Stack>
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
                <Stack direction="row" flexWrap="wrap" gap={1}>
                  {filterState.userIds.map((id) => (
                    <Chip key={id} label={id} size="small" onDelete={() => handleRemoveId("user", id)} deleteIcon={<Close />} />
                  ))}
                </Stack>
              </Box>

              {/* Annotation Score */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Annotation Score
                </Typography>
                <Autocomplete
                  options={ANNOTATION_SCORE_OPTIONS}
                  value={filterState.annotationScore}
                  onChange={(_, newValue) => setFilterState((prev) => ({ ...prev, annotationScore: newValue }))}
                  renderInput={(params) => <TextField {...params} size="small" placeholder="Select score" />}
                  getOptionLabel={(option) => (option === "0" ? "Unhelpful" : "Helpful")}
                />
              </Box>

              {/* Status Code */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Status Code
                </Typography>
                <Autocomplete
                  options={STATUS_CODE_OPTIONS}
                  value={filterState.statusCode}
                  onChange={(_, newValue) => setFilterState((prev) => ({ ...prev, statusCode: newValue }))}
                  renderInput={(params) => <TextField {...params} size="small" placeholder="Select status" />}
                  getOptionLabel={(option) => (option === "Ok" ? "Pass" : "Fail")}
                />
              </Box>

              {/* Annotation Type */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Annotation Type
                </Typography>
                <Autocomplete
                  options={ANNOTATION_TYPE_OPTIONS}
                  value={filterState.annotationType}
                  onChange={(_, newValue) => setFilterState((prev) => ({ ...prev, annotationType: newValue }))}
                  renderInput={(params) => <TextField {...params} size="small" placeholder="Select type" />}
                  getOptionLabel={(option) => (option === "human" ? "Human" : "Continuous Eval")}
                />
              </Box>

              {/* Continuous Eval Run Status */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Continuous Eval Run Status
                </Typography>
                <Autocomplete
                  options={CONTINUOUS_EVAL_RUN_STATUS_OPTIONS}
                  value={filterState.continuousEvalRunStatus}
                  onChange={(_, newValue) => setFilterState((prev) => ({ ...prev, continuousEvalRunStatus: newValue }))}
                  renderInput={(params) => <TextField {...params} size="small" placeholder="Select status" />}
                  getOptionLabel={(option) => option.charAt(0).toUpperCase() + option.slice(1)}
                />
              </Box>

              {/* Continuous Eval Name */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Continuous Eval Name
                </Typography>
                <TextField
                  size="small"
                  fullWidth
                  value={filterState.continuousEvalName}
                  onChange={(e) => setFilterState((prev) => ({ ...prev, continuousEvalName: e.target.value }))}
                  placeholder="Enter continuous eval name"
                  slotProps={{
                    input: {
                      endAdornment: filterState.continuousEvalName && (
                        <IconButton
                          size="small"
                          onClick={() => setFilterState((prev) => ({ ...prev, continuousEvalName: "" }))}
                          sx={{ mr: -1 }}
                        >
                          <Close fontSize="small" />
                        </IconButton>
                      ),
                    },
                  }}
                />
              </Box>

              {/* Include Experiment Traces */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Include Experiment Traces
                </Typography>
                <Autocomplete
                  options={INCLUDE_EXPERIMENT_TRACES_OPTIONS}
                  value={filterState.includeExperimentTraces}
                  onChange={(_, newValue) => setFilterState((prev) => ({ ...prev, includeExperimentTraces: newValue }))}
                  renderInput={(params) => <TextField {...params} size="small" placeholder="Select option" />}
                  getOptionLabel={(option) => (option === "true" ? "Yes" : "No")}
                />
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
              <Button variant="contained" onClick={handleApplyFilters}>
                Apply Filters
              </Button>
            </Stack>
          </Box>
        </Paper>
      </Popover>
    </>
  );
};
