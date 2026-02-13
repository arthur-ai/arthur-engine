import { Add, Close, FilterList } from "@mui/icons-material";
import { Box, Button, Chip, IconButton, Paper, Popover, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useState } from "react";

import { useFilterStore } from "../../../stores/filter.store";
import type { IncomingFilter } from "../../filtering/mapper";
import { Operators } from "../../filtering/types";

interface FilterState {
  userIds: string[];
}

export const SessionsFilterModal = () => {
  const [anchorEl, setAnchorEl] = useState<HTMLButtonElement | null>(null);
  const setFilters = useFilterStore((state) => state.setFilters);
  const currentFilters = useFilterStore((state) => state.filters);

  const [filterState, setFilterState] = useState<FilterState>({
    userIds: [],
  });

  const [userIdInput, setUserIdInput] = useState("");
  const [pendingFilters, setPendingFilters] = useState<IncomingFilter[] | null>(null);

  const open = Boolean(anchorEl);

  // Populate filter state from currentFilters when modal opens
  useEffect(() => {
    if (open) {
      const newFilterState: FilterState = {
        userIds: [],
      };

      currentFilters.forEach((filter) => {
        if (filter.name === "user_ids") {
          newFilterState.userIds = Array.isArray(filter.value) ? filter.value : [];
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
      setFilters(pendingFilters);
      setPendingFilters(null);
    }
  };

  const handleAddUserId = (value: string) => {
    if (value.trim()) {
      setFilterState((prev) => ({
        ...prev,
        userIds: [...prev.userIds, value.trim()],
      }));
      setUserIdInput("");
    }
  };

  const handleRemoveUserId = (id: string) => {
    setFilterState((prev) => ({
      ...prev,
      userIds: prev.userIds.filter((item) => item !== id),
    }));
  };

  const handleApplyFilters = () => {
    const filters: IncomingFilter[] = [];

    if (filterState.userIds.length > 0) {
      filters.push({
        name: "user_ids",
        operator: Operators.IN,
        value: filterState.userIds,
      });
    }

    setPendingFilters(filters);
    handleClose();
  };

  const handleClearFilters = () => {
    setFilterState({
      userIds: [],
    });
    setFilters([]);
  };

  const hasActiveFilters = filterState.userIds.length > 0;

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
                        handleAddUserId(userIdInput);
                      }
                    }}
                    placeholder="Enter User ID"
                    autoComplete="off"
                    slotProps={{
                      htmlInput: {
                        "data-1p-ignore": true,
                      },
                    }}
                  />
                  <IconButton size="small" onClick={() => handleAddUserId(userIdInput)} disabled={!userIdInput.trim()} color="primary">
                    <Add />
                  </IconButton>
                </Stack>
                <Stack direction="row" flexWrap="wrap" gap={1}>
                  {filterState.userIds.map((id) => (
                    <Chip key={id} label={id} size="small" onDelete={() => handleRemoveUserId(id)} deleteIcon={<Close />} />
                  ))}
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
