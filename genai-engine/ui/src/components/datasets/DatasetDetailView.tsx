import AddIcon from "@mui/icons-material/Add";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ClearIcon from "@mui/icons-material/Clear";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import HistoryIcon from "@mui/icons-material/History";
import SearchIcon from "@mui/icons-material/Search";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  IconButton,
  InputAdornment,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";

import { EditRowModal } from "./EditRowModal";
import { VersionDrawer } from "./VersionDrawer";

import { useTask } from "@/hooks/useTask";
import {
  deleteDatasetRow,
  getDataset,
  updateDatasetRow,
} from "@/services/mockDatasetService";
import { Dataset } from "@/types/dataset";

// Mock data structure for rows
interface DatasetRow {
  id: string;
  row_data: Record<string, unknown>;
}

export const DatasetDetailView: React.FC = () => {
  const { datasetId } = useParams<{ datasetId: string }>();
  const { task } = useTask();
  const navigate = useNavigate();

  // Dataset metadata
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Rows data
  const [rows, setRows] = useState<DatasetRow[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [rowsLoading, setRowsLoading] = useState(false);
  const [rowsError, setRowsError] = useState<string | null>(null);

  // Filters and pagination
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState("");
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [totalRows, setTotalRows] = useState(0);

  // Sorting
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  // Row editing
  const [editingRow, setEditingRow] = useState<DatasetRow | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [deletingRowId, setDeletingRowId] = useState<string | null>(null);

  // Add row
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newRowData, setNewRowData] = useState<Record<string, unknown>>({});
  const [isAdding, setIsAdding] = useState(false);

  // Version drawer
  const [isVersionDrawerOpen, setIsVersionDrawerOpen] = useState(false);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
      setPage(0); // Reset to first page on search
    }, 500);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Load dataset metadata
  useEffect(() => {
    const loadDataset = async () => {
      if (!task || !datasetId) {
        setError("Task or dataset ID not available");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const data = await getDataset(task.id, datasetId);

        if (!data) {
          setError("Dataset not found");
        } else {
          setDataset(data);
        }
      } catch (err) {
        console.error("Failed to fetch dataset:", err);
        setError("Failed to load dataset details");
      } finally {
        setLoading(false);
      }
    };

    loadDataset();
  }, [task, datasetId]);

  // Load dataset rows (mock data for now)
  const loadRows = useCallback(async () => {
    if (!dataset) return;

    try {
      setRowsLoading(true);
      setRowsError(null);

      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 300));

      // Generate mock rows with dynamic columns
      const mockColumns = [
        "name",
        "email",
        "age",
        "city",
        "status",
        "created_at",
      ];
      const mockRows: DatasetRow[] = Array.from(
        {
          length: Math.min(rowsPerPage, dataset.rowCount - page * rowsPerPage),
        },
        (_, i) => ({
          id: `row-${page * rowsPerPage + i + 1}`,
          row_data: {
            name: `User ${page * rowsPerPage + i + 1}`,
            email: `user${page * rowsPerPage + i + 1}@example.com`,
            age: 20 + Math.floor(Math.random() * 50),
            city: ["New York", "London", "Tokyo", "Paris", "Berlin"][
              Math.floor(Math.random() * 5)
            ],
            status: ["active", "inactive", "pending"][
              Math.floor(Math.random() * 3)
            ],
            created_at: new Date(
              Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000
            ).toISOString(),
          },
        })
      );

      // Filter by search query if present
      let filteredRows = mockRows;
      if (debouncedSearchQuery) {
        const query = debouncedSearchQuery.toLowerCase();
        filteredRows = mockRows.filter((row) =>
          JSON.stringify(row.row_data).toLowerCase().includes(query)
        );
      }

      setRows(filteredRows);
      setColumns(mockColumns);
      setTotalRows(dataset.rowCount);
    } catch (err) {
      console.error("Failed to fetch rows:", err);
      setRowsError("Failed to load dataset rows");
    } finally {
      setRowsLoading(false);
    }
  }, [dataset, page, rowsPerPage, debouncedSearchQuery]);

  useEffect(() => {
    if (dataset) {
      loadRows();
    }
  }, [dataset, loadRows]);

  // Sorting logic
  const sortedRows = useMemo(() => {
    if (!sortColumn) return rows;

    return [...rows].sort((a, b) => {
      const aVal = a.row_data[sortColumn];
      const bVal = b.row_data[sortColumn];

      // Handle null/undefined
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      // Type-specific comparison
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortDirection === "asc" ? aVal - bVal : bVal - aVal;
      }

      // String comparison
      const comparison = String(aVal).localeCompare(String(bVal));
      return sortDirection === "asc" ? comparison : -comparison;
    });
  }, [rows, sortColumn, sortDirection]);

  const handleSort = useCallback(
    (column: string) => {
      if (sortColumn === column) {
        setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
      } else {
        setSortColumn(column);
        setSortDirection("asc");
      }
    },
    [sortColumn]
  );

  const handleBack = useCallback(() => {
    navigate(`/tasks/${task?.id}/datasets`);
  }, [navigate, task?.id]);

  const handlePageChange = useCallback((_event: unknown, newPage: number) => {
    setPage(newPage);
  }, []);

  const handleRowsPerPageChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setRowsPerPage(parseInt(event.target.value, 10));
      setPage(0);
    },
    []
  );

  const handleClearSearch = useCallback(() => {
    setSearchQuery("");
  }, []);

  const handleEditRow = useCallback((row: DatasetRow) => {
    setEditingRow(row);
    setIsEditModalOpen(true);
  }, []);

  const handleUpdateRow = useCallback(
    async (rowData: Record<string, unknown>) => {
      if (!task || !datasetId || !editingRow) return;

      try {
        setIsUpdating(true);
        await updateDatasetRow(task.id, datasetId, editingRow.id, rowData);
        setIsEditModalOpen(false);
        setEditingRow(null);

        // Reload rows
        await loadRows();
      } catch (err) {
        console.error("Failed to update row:", err);
        throw err;
      } finally {
        setIsUpdating(false);
      }
    },
    [task, datasetId, editingRow, loadRows]
  );

  const handleDeleteRow = useCallback(
    async (rowId: string) => {
      if (!task || !datasetId) return;

      const confirmed = window.confirm(
        "Are you sure you want to delete this row? This action cannot be undone."
      );
      if (!confirmed) return;

      try {
        setDeletingRowId(rowId);
        await deleteDatasetRow(task.id, datasetId, rowId);

        // Reload dataset metadata and rows
        const updatedDataset = await getDataset(task.id, datasetId);
        if (updatedDataset) {
          setDataset(updatedDataset);
        }
        await loadRows();
      } catch (err) {
        console.error("Failed to delete row:", err);
      } finally {
        setDeletingRowId(null);
      }
    },
    [task, datasetId, loadRows]
  );

  const handleAddRow = useCallback(() => {
    // Initialize with columns from existing data
    const initialData: Record<string, unknown> = {};
    columns.forEach((col) => {
      initialData[col] = "";
    });
    setNewRowData(initialData);
    setIsAddModalOpen(true);
  }, [columns]);

  const handleAddRowSubmit = useCallback(
    async (rowData: Record<string, unknown>) => {
      if (!task || !datasetId) return;
      try {
        setIsAdding(true);
        // TODO: Implement addDatasetRow in mock service
        console.log("Adding new row:", rowData);
        setIsAddModalOpen(false);
        setNewRowData({});
        await loadRows(); // Reload rows after add
      } catch (err) {
        console.error("Failed to add row:", err);
        throw err;
      } finally {
        setIsAdding(false);
      }
    },
    [task, datasetId, loadRows]
  );

  const renderCellValue = useCallback((value: unknown): string => {
    if (value === null || value === undefined) return "-";
    if (typeof value === "boolean") return value ? "✓" : "✗";
    if (typeof value === "object") return JSON.stringify(value);
    if (typeof value === "string" && value.length > 50) {
      return value.substring(0, 50) + "...";
    }
    return String(value);
  }, []);

  const formatValue = useCallback((value: unknown): string => {
    if (value === null || value === undefined) return "-";
    if (typeof value === "boolean") return value ? "true" : "false";
    if (typeof value === "object") return JSON.stringify(value, null, 2);
    return String(value);
  }, []);

  // Loading state
  if (loading) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: "400px",
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  // Error state
  if (error || !dataset) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={handleBack}>
              Back to Datasets
            </Button>
          }
        >
          {error || "Dataset not found"}
        </Alert>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        width: "100%",
        height: "calc(100vh - 90px)",
        display: "flex",
        overflow: "hidden",
      }}
    >
      {/* Main Content - shrinks when drawer opens */}
      <Box
        sx={{
          flex: isVersionDrawerOpen ? "1 1 auto" : "1 1 100%",
          transition: "flex 0.3s ease",
          display: "grid",
          gridTemplateRows: "auto 1fr auto",
          overflow: "hidden",
          minWidth: 0,
        }}
      >
        {/* Compact Header */}
        <Box
          sx={{
            px: 3,
            py: 2,
            borderBottom: 1,
            borderColor: "divider",
            backgroundColor: "background.paper",
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
            <IconButton size="small" onClick={handleBack}>
              <ArrowBackIcon />
            </IconButton>
            <Typography
              variant="h6"
              sx={{ fontWeight: 600, flexGrow: 1, color: "text.primary" }}
            >
              {dataset.name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {totalRows.toLocaleString()} rows
            </Typography>
            <Button
              variant="contained"
              size="small"
              startIcon={<AddIcon />}
              onClick={handleAddRow}
              sx={{ ml: 1 }}
            >
              Add Row
            </Button>
            <Button
              variant="outlined"
              size="small"
              startIcon={<HistoryIcon />}
              onClick={() => setIsVersionDrawerOpen(true)}
              sx={{ ml: 1 }}
            >
              Versions
            </Button>
          </Box>

          {/* Description - if available */}
          {dataset.description && (
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ mb: 2, ml: 6 }}
            >
              {dataset.description}
            </Typography>
          )}

          {/* Search Bar */}
          <TextField
            fullWidth
            placeholder="Search across all columns..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            size="small"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
              endAdornment: searchQuery && (
                <InputAdornment position="end">
                  <IconButton size="small" onClick={handleClearSearch}>
                    <ClearIcon fontSize="small" />
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
        </Box>

        {/* Data Table - Scrollable */}
        <Box
          sx={{
            overflow: "auto",
            minHeight: 0,
            backgroundColor: "background.paper",
          }}
        >
          {rowsLoading ? (
            <Box
              sx={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                height: "100%",
              }}
            >
              <CircularProgress />
            </Box>
          ) : rowsError ? (
            <Box sx={{ p: 3 }}>
              <Alert
                severity="error"
                action={
                  <Button color="inherit" size="small" onClick={loadRows}>
                    Retry
                  </Button>
                }
              >
                {rowsError}
              </Alert>
            </Box>
          ) : rows.length === 0 ? (
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                textAlign: "center",
              }}
            >
              <Typography variant="h6" color="text.secondary" gutterBottom>
                {debouncedSearchQuery ? "No matching rows" : "No data yet"}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {debouncedSearchQuery
                  ? "Try adjusting your search query"
                  : "Add rows to get started"}
              </Typography>
            </Box>
          ) : (
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell
                    sx={{
                      fontWeight: 600,
                      minWidth: 100,
                      backgroundColor: "grey.100",
                    }}
                  >
                    Row ID
                  </TableCell>
                  {columns.map((column) => (
                    <TableCell
                      key={column}
                      sx={{
                        fontWeight: 600,
                        minWidth: 150,
                        backgroundColor: "grey.100",
                      }}
                    >
                      <TableSortLabel
                        active={sortColumn === column}
                        direction={
                          sortColumn === column ? sortDirection : "asc"
                        }
                        onClick={() => handleSort(column)}
                      >
                        {column}
                      </TableSortLabel>
                    </TableCell>
                  ))}
                  <TableCell
                    sx={{
                      fontWeight: 600,
                      minWidth: 100,
                      backgroundColor: "grey.100",
                      textAlign: "center",
                    }}
                  >
                    Actions
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sortedRows.map((row) => (
                  <TableRow key={row.id} hover>
                    <TableCell
                      sx={{
                        fontFamily: "monospace",
                        fontSize: "0.75rem",
                        color: "text.secondary",
                      }}
                    >
                      {row.id}
                    </TableCell>
                    {columns.map((column) => {
                      const value = row.row_data[column];
                      const displayValue = renderCellValue(value);
                      const fullValue = formatValue(value);

                      return (
                        <TableCell key={column}>
                          {displayValue.length > 50 ? (
                            <Tooltip title={fullValue} arrow>
                              <span>{displayValue}</span>
                            </Tooltip>
                          ) : (
                            displayValue
                          )}
                        </TableCell>
                      );
                    })}
                    <TableCell sx={{ textAlign: "center" }}>
                      <Box
                        sx={{
                          display: "flex",
                          gap: 0.5,
                          justifyContent: "center",
                        }}
                      >
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleEditRow(row);
                          }}
                          disabled={deletingRowId === row.id}
                          sx={{ color: "primary.main" }}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteRow(row.id);
                          }}
                          disabled={deletingRowId !== null}
                          sx={{ color: "error.main" }}
                        >
                          {deletingRowId === row.id ? (
                            <CircularProgress size={16} />
                          ) : (
                            <DeleteIcon fontSize="small" />
                          )}
                        </IconButton>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Box>

        {/* Pagination - Fixed at bottom */}
        {rows.length > 0 && (
          <Box
            sx={{
              borderTop: 1,
              borderColor: "divider",
              backgroundColor: "background.paper",
            }}
          >
            <TablePagination
              component="div"
              count={totalRows}
              page={page}
              onPageChange={handlePageChange}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={handleRowsPerPageChange}
              rowsPerPageOptions={[10, 25, 50, 100]}
            />
          </Box>
        )}

        {/* Edit Row Modal */}
        {editingRow && (
          <EditRowModal
            open={isEditModalOpen}
            onClose={() => {
              setIsEditModalOpen(false);
              setEditingRow(null);
            }}
            onSubmit={handleUpdateRow}
            rowData={editingRow.row_data}
            rowId={editingRow.id}
            isLoading={isUpdating}
          />
        )}

        {/* Add Row Modal */}
        <EditRowModal
          open={isAddModalOpen}
          onClose={() => {
            setIsAddModalOpen(false);
            setNewRowData({});
          }}
          onSubmit={handleAddRowSubmit}
          rowData={newRowData}
          rowId="new"
          isLoading={isAdding}
        />
      </Box>

      {/* Version Drawer - conditionally rendered */}
      {isVersionDrawerOpen && task && datasetId && dataset && (
        <VersionDrawer
          taskId={task.id}
          datasetId={datasetId}
          datasetName={dataset.name}
          onClose={() => setIsVersionDrawerOpen(false)}
        />
      )}
    </Box>
  );
};
