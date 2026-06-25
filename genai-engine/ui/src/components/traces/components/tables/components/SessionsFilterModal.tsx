import { FilterList } from "@mui/icons-material";
import { Box, Button, Paper, Popover, Stack } from "@mui/material";
import { useEffect, useRef, useState } from "react";

import { useFilterStore } from "../../../stores/filter.store";
import type { IncomingFilter } from "../../filtering/mapper";
import { Operators } from "../../filtering/types";

import { ChipListField } from "./ChipListField";

interface FilterState {
  traceIds: string[];
  sessionIds: string[];
  userIds: string[];
}

const EMPTY_FILTER_STATE: FilterState = {
  traceIds: [],
  sessionIds: [],
  userIds: [],
};

const SESSION_FILTER_FIELDS = [
  { key: "traceIds", name: "trace_ids", label: "Trace ID", placeholder: "Enter Trace ID" },
  { key: "sessionIds", name: "session_ids", label: "Session ID", placeholder: "Enter Session ID" },
  { key: "userIds", name: "user_ids", label: "User ID", placeholder: "Enter User ID" },
] as const satisfies readonly { key: keyof FilterState; name: string; label: string; placeholder: string }[];

const FILTER_NAME_TO_KEY = new Map<string, keyof FilterState>(SESSION_FILTER_FIELDS.map((field) => [field.name, field.key]));

export const SessionsFilterModal = () => {
  const anchorElRef = useRef<HTMLButtonElement | null>(null);
  const [open, setOpen] = useState(false);
  const setFilters = useFilterStore((state) => state.setFilters);
  const currentFilters = useFilterStore((state) => state.filters);

  const [filterState, setFilterState] = useState<FilterState>(EMPTY_FILTER_STATE);
  const [pendingFilters, setPendingFilters] = useState<IncomingFilter[] | null>(null);

  // Populate filter state from currentFilters when modal opens
  useEffect(() => {
    if (open) {
      const newFilterState: FilterState = { ...EMPTY_FILTER_STATE };

      currentFilters.forEach((filter) => {
        const key = FILTER_NAME_TO_KEY.get(filter.name);
        if (key) {
          newFilterState[key] = Array.isArray(filter.value) ? filter.value : [filter.value];
        }
      });

      setFilterState(newFilterState);
    }
  }, [open, currentFilters]);

  const handleClose = () => {
    setOpen(false);
  };

  const handleExited = () => {
    if (pendingFilters) {
      setFilters(pendingFilters);
      setPendingFilters(null);
    }
  };

  const addId = (key: keyof FilterState, value: string) => {
    setFilterState((prev) => (prev[key].includes(value) ? prev : { ...prev, [key]: [...prev[key], value] }));
  };

  const removeId = (key: keyof FilterState, value: string) => {
    setFilterState((prev) => ({ ...prev, [key]: prev[key].filter((item) => item !== value) }));
  };

  const handleApplyFilters = () => {
    const filters: IncomingFilter[] = [];

    SESSION_FILTER_FIELDS.forEach((field) => {
      const value = filterState[field.key];
      if (value.length > 0) {
        filters.push({
          name: field.name,
          operator: Operators.IN,
          value,
        });
      }
    });

    setPendingFilters(filters);
    handleClose();
  };

  const handleClearFilters = () => {
    setFilterState(EMPTY_FILTER_STATE);
    setFilters([]);
  };

  const hasActiveFilters = Object.values(filterState).some((ids) => ids.length > 0);

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
              {SESSION_FILTER_FIELDS.map((field) => (
                <ChipListField
                  key={field.key}
                  label={field.label}
                  placeholder={field.placeholder}
                  values={filterState[field.key]}
                  onAdd={(value) => addId(field.key, value)}
                  onRemove={(value) => removeId(field.key, value)}
                />
              ))}
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
