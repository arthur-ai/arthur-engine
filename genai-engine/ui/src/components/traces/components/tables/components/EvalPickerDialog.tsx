import { type IncomingFilter, TextOperators } from "@arthur/shared-components";
import LiveTvOutlinedIcon from "@mui/icons-material/LiveTvOutlined";
import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Radio,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { useContinuousEvals } from "@/components/live-evals/hooks/useContinuousEvals";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { usePagination } from "@/hooks/usePagination";
import { useTask } from "@/hooks/useTask";
import { formatDateInTimezone } from "@/utils/formatters";

const DEBOUNCE_MS = 300;

type EvalPickerDialogProps = {
  open: boolean;
  onClose: () => void;
  onSelect: (eval_: { id: string; name: string }) => void;
};

export const EvalPickerDialog = ({ open, onClose, onSelect }: EvalPickerDialogProps) => {
  const { task } = useTask();
  const { timezone, use24Hour } = useDisplaySettings();
  const pagination = usePagination(10);
  const [searchInput, setSearchInput] = useState("");
  const [filters, setFilters] = useState<IncomingFilter[]>([]);
  const [selected, setSelected] = useState<{ id: string; name: string } | null>(null);
  const debounceTimer = useRef<ReturnType<typeof setTimeout>>();

  const { data, isLoading } = useContinuousEvals({
    pagination: { page: pagination.page, page_size: pagination.rowsPerPage },
    filters,
  });

  // Debounced search: update filters after user stops typing
  useEffect(() => {
    debounceTimer.current = setTimeout(() => {
      const trimmed = searchInput.trim();
      if (trimmed) {
        setFilters([{ name: "name", operator: TextOperators.CONTAINS, value: trimmed }]);
      } else {
        setFilters([]);
      }
      pagination.resetPage();
    }, DEBOUNCE_MS);

    return () => clearTimeout(debounceTimer.current);
  }, [searchInput]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleClose = () => {
    setSearchInput("");
    setFilters([]);
    setSelected(null);
    pagination.resetPage();
    onClose();
  };

  const handleRun = () => {
    if (selected) {
      onSelect(selected);
      setSelected(null);
    }
  };

  const evals = data?.evals ?? [];
  const count = data?.count ?? 0;

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Select a Continuous Eval</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <TextField
            size="small"
            variant="outlined"
            placeholder="Search by name"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            sx={{ width: "100%" }}
          />

          {!isLoading && evals.length === 0 ? (
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                py: 6,
                textAlign: "center",
              }}
            >
              <LiveTvOutlinedIcon sx={{ fontSize: 48, color: "text.secondary", mb: 2 }} />
              <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                No continuous evals configured for this task
              </Typography>
              <Button variant="contained" size="small" component={Link} to={`/tasks/${task?.id}/continuous-evals/new`} onClick={handleClose}>
                Create Continuous Eval
              </Button>
            </Box>
          ) : (
            <>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell padding="checkbox" />
                      <TableCell sx={{ fontWeight: 600 }}>Name</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Evaluator</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Enabled</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Created</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {evals.map((eval_) => (
                      <TableRow
                        key={eval_.id}
                        hover
                        selected={selected?.id === eval_.id}
                        onClick={() => setSelected({ id: eval_.id, name: eval_.name })}
                        sx={{ cursor: "pointer" }}
                      >
                        <TableCell padding="checkbox">
                          <Radio checked={selected?.id === eval_.id} size="small" />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontWeight={500}>
                            {eval_.name}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {eval_.llm_eval_name}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={eval_.enabled ? "Enabled" : "Disabled"}
                            size="small"
                            color={eval_.enabled ? "success" : "default"}
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {formatDateInTimezone(eval_.created_at, timezone, { hour12: !use24Hour })}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              <TablePagination
                component="div"
                count={count}
                page={pagination.page}
                onPageChange={pagination.handlePageChange}
                rowsPerPage={pagination.rowsPerPage}
                onRowsPerPageChange={pagination.handleRowsPerPageChange}
                rowsPerPageOptions={[5, 10, 25]}
                sx={{ overflow: "visible" }}
              />
            </>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button variant="contained" onClick={handleRun} disabled={!selected}>
          Run
        </Button>
      </DialogActions>
    </Dialog>
  );
};
