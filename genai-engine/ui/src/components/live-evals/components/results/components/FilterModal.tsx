import { Add, Close, FilterList } from "@mui/icons-material";
import { Autocomplete, Box, Button, Chip, IconButton, Paper, Popover, Stack, TextField, Typography } from "@mui/material";
import { DatePicker } from "@mui/x-date-pickers";
import { Dayjs } from "dayjs";
import { useState } from "react";

import type { IncomingFilter } from "@arthur/shared-components";
import { EnumOperators, Operators } from "@arthur/shared-components";
import { useFilterStore } from "@/components/traces/stores/filter.store";

interface FilterState {
  runStatus: string | null;
  annotationScore: string | null;
  continuousEvalIds: string[];
  traceIds: string[];
  annotationIds: string[];
  createdBefore: Dayjs | null;
  createdAfter: Dayjs | null;
}

const RUN_STATUS_OPTIONS = ["pending", "passed", "failed", "skipped", "error", "running"];
const ANNOTATION_SCORE_OPTIONS = ["0", "1"];

export const FilterModal = () => {
  const [anchorEl, setAnchorEl] = useState<HTMLButtonElement | null>(null);
  const setFilters = useFilterStore((state) => state.setFilters);

  const [filterState, setFilterState] = useState<FilterState>({
    runStatus: null,
    annotationScore: null,
    continuousEvalIds: [],
    traceIds: [],
    annotationIds: [],
    createdBefore: null,
    createdAfter: null,
  });

  const [continuousEvalIdInput, setContinuousEvalIdInput] = useState("");
  const [traceIdInput, setTraceIdInput] = useState("");
  const [annotationIdInput, setAnnotationIdInput] = useState("");
  const [pendingFilters, setPendingFilters] = useState<IncomingFilter[] | null>(null);

  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleExited = () => {
    if (pendingFilters) {
      setFilters(pendingFilters);
      setPendingFilters(null);
    }
  };

  const handleAddContinuousEvalId = () => {
    if (continuousEvalIdInput.trim()) {
      setFilterState((prev) => ({
        ...prev,
        continuousEvalIds: [...prev.continuousEvalIds, continuousEvalIdInput.trim()],
      }));
      setContinuousEvalIdInput("");
    }
  };

  const handleAddTraceId = () => {
    if (traceIdInput.trim()) {
      setFilterState((prev) => ({
        ...prev,
        traceIds: [...prev.traceIds, traceIdInput.trim()],
      }));
      setTraceIdInput("");
    }
  };

  const handleAddAnnotationId = () => {
    if (annotationIdInput.trim()) {
      setFilterState((prev) => ({
        ...prev,
        annotationIds: [...prev.annotationIds, annotationIdInput.trim()],
      }));
      setAnnotationIdInput("");
    }
  };

  const handleRemoveContinuousEvalId = (id: string) => {
    setFilterState((prev) => ({
      ...prev,
      continuousEvalIds: prev.continuousEvalIds.filter((item) => item !== id),
    }));
  };

  const handleRemoveTraceId = (id: string) => {
    setFilterState((prev) => ({
      ...prev,
      traceIds: prev.traceIds.filter((item) => item !== id),
    }));
  };

  const handleRemoveAnnotationId = (id: string) => {
    setFilterState((prev) => ({
      ...prev,
      annotationIds: prev.annotationIds.filter((item) => item !== id),
    }));
  };

  const handleApplyFilters = () => {
    const filters: IncomingFilter[] = [];

    if (filterState.runStatus) {
      filters.push({
        name: "run_status",
        operator: EnumOperators.EQUALS,
        value: filterState.runStatus,
      });
    }

    if (filterState.annotationScore !== null) {
      filters.push({
        name: "annotation_score",
        operator: EnumOperators.EQUALS,
        value: filterState.annotationScore,
      });
    }

    if (filterState.continuousEvalIds.length > 0) {
      filters.push({
        name: "continuous_eval_id",
        operator: Operators.IN,
        value: filterState.continuousEvalIds,
      });
    }

    if (filterState.traceIds.length > 0) {
      filters.push({
        name: "trace_id",
        operator: Operators.IN,
        value: filterState.traceIds,
      });
    }

    if (filterState.annotationIds.length > 0) {
      filters.push({
        name: "id",
        operator: Operators.IN,
        value: filterState.annotationIds,
      });
    }

    if (filterState.createdBefore) {
      filters.push({
        name: "created_at",
        operator: Operators.LESS_THAN,
        value: filterState.createdBefore.format("YYYY-MM-DD"),
      });
    }

    if (filterState.createdAfter) {
      filters.push({
        name: "created_at",
        operator: Operators.GREATER_THAN,
        value: filterState.createdAfter.format("YYYY-MM-DD"),
      });
    }

    // Store filters to apply after modal closes
    setPendingFilters(filters);
    handleClose();
  };

  const handleClearFilters = () => {
    setFilterState({
      runStatus: null,
      annotationScore: null,
      continuousEvalIds: [],
      traceIds: [],
      annotationIds: [],
      createdBefore: null,
      createdAfter: null,
    });
    setFilters([]);
  };

  const hasActiveFilters =
    filterState.runStatus ||
    filterState.annotationScore ||
    filterState.continuousEvalIds.length > 0 ||
    filterState.traceIds.length > 0 ||
    filterState.annotationIds.length > 0 ||
    filterState.createdBefore ||
    filterState.createdAfter;

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
              {/* Run Status */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Run Status
                </Typography>
                <Autocomplete
                  options={RUN_STATUS_OPTIONS}
                  value={filterState.runStatus}
                  onChange={(_, newValue) => setFilterState((prev) => ({ ...prev, runStatus: newValue }))}
                  renderInput={(params) => <TextField {...params} size="small" placeholder="Select status" />}
                  getOptionLabel={(option) => option.charAt(0).toUpperCase() + option.slice(1)}
                />
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
                />
              </Box>

              {/* Continuous Eval ID */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Continuous Eval ID
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                  <TextField
                    size="small"
                    fullWidth
                    value={continuousEvalIdInput}
                    onChange={(e) => setContinuousEvalIdInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddContinuousEvalId();
                      }
                    }}
                    placeholder="Enter ID"
                  />
                  <IconButton size="small" onClick={handleAddContinuousEvalId} disabled={!continuousEvalIdInput.trim()} color="primary">
                    <Add />
                  </IconButton>
                </Stack>
                <Stack direction="row" flexWrap="wrap" gap={1}>
                  {filterState.continuousEvalIds.map((id) => (
                    <Chip key={id} label={id} size="small" onDelete={() => handleRemoveContinuousEvalId(id)} deleteIcon={<Close />} />
                  ))}
                </Stack>
              </Box>

              {/* Trace ID */}
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
                        handleAddTraceId();
                      }
                    }}
                    placeholder="Enter ID"
                  />
                  <IconButton size="small" onClick={handleAddTraceId} disabled={!traceIdInput.trim()} color="primary">
                    <Add />
                  </IconButton>
                </Stack>
                <Stack direction="row" flexWrap="wrap" gap={1}>
                  {filterState.traceIds.map((id) => (
                    <Chip key={id} label={id} size="small" onDelete={() => handleRemoveTraceId(id)} deleteIcon={<Close />} />
                  ))}
                </Stack>
              </Box>

              {/* Annotation ID */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Annotation ID
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                  <TextField
                    size="small"
                    fullWidth
                    value={annotationIdInput}
                    onChange={(e) => setAnnotationIdInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddAnnotationId();
                      }
                    }}
                    placeholder="Enter ID"
                  />
                  <IconButton size="small" onClick={handleAddAnnotationId} disabled={!annotationIdInput.trim()} color="primary">
                    <Add />
                  </IconButton>
                </Stack>
                <Stack direction="row" flexWrap="wrap" gap={1}>
                  {filterState.annotationIds.map((id) => (
                    <Chip key={id} label={id} size="small" onDelete={() => handleRemoveAnnotationId(id)} deleteIcon={<Close />} />
                  ))}
                </Stack>
              </Box>

              {/* Created Date Range */}
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                  Created
                </Typography>
                <Stack spacing={2}>
                  <Box>
                    <Typography variant="caption" sx={{ mb: 0.5, display: "block" }}>
                      Created After
                    </Typography>
                    <DatePicker
                      value={filterState.createdAfter}
                      onChange={(newValue) => setFilterState((prev) => ({ ...prev, createdAfter: newValue }))}
                      slotProps={{
                        textField: {
                          size: "small",
                          fullWidth: true,
                        },
                        field: {
                          clearable: true,
                        },
                      }}
                    />
                  </Box>
                  <Box>
                    <Typography variant="caption" sx={{ mb: 0.5, display: "block" }}>
                      Created Before
                    </Typography>
                    <DatePicker
                      value={filterState.createdBefore}
                      onChange={(newValue) => setFilterState((prev) => ({ ...prev, createdBefore: newValue }))}
                      slotProps={{
                        textField: {
                          size: "small",
                          fullWidth: true,
                        },
                        field: {
                          clearable: true,
                        },
                      }}
                    />
                  </Box>
                </Stack>
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
