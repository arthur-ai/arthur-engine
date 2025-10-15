import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Button,
  TextField,
  InputAdornment,
  CircularProgress,
  Alert,
  TablePagination,
  Typography,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import AddIcon from "@mui/icons-material/Add";
import FolderOpenIcon from "@mui/icons-material/FolderOpen";
import { useTask } from "@/hooks/useTask";
import {
  Dataset,
  DatasetFormData,
  SortField,
  SortOrder,
} from "@/types/dataset";
import {
  fetchDatasets,
  createDataset,
  deleteDataset,
} from "@/services/mockDatasetService";
import { CreateDatasetModal } from "./CreateDatasetModal";
import { DatasetsTable } from "./DatasetsTable";

export const DatasetsView: React.FC = () => {
  const { task } = useTask();
  const navigate = useNavigate();

  // State
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState("");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [totalCount, setTotalCount] = useState(0);
  const [sortBy, setSortBy] = useState<SortField>("lastModified");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
      setPage(0); // Reset to first page on search
    }, 500);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Fetch datasets
  const loadDatasets = useCallback(async () => {
    if (!task) {
      setError("Task not available");
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const result = await fetchDatasets(task.id, {
        searchQuery: debouncedSearchQuery,
        sortBy,
        sortOrder,
        page,
        pageSize,
      });

      setDatasets(result.datasets);
      setTotalCount(result.total);
    } catch (err) {
      console.error("Failed to fetch datasets:", err);
      setError("Failed to load datasets. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [task, debouncedSearchQuery, sortBy, sortOrder, page, pageSize]);

  useEffect(() => {
    loadDatasets();
  }, [loadDatasets]);

  // Handlers
  const handleSort = useCallback(
    (field: SortField) => {
      if (sortBy === field) {
        setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
      } else {
        setSortBy(field);
        setSortOrder("asc");
      }
      setPage(0);
    },
    [sortBy]
  );

  const handlePageChange = useCallback((_event: unknown, newPage: number) => {
    setPage(newPage);
  }, []);

  const handlePageSizeChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setPageSize(parseInt(event.target.value, 10));
      setPage(0);
    },
    []
  );

  const handleRowClick = useCallback(
    (dataset: Dataset) => {
      navigate(`/tasks/${task?.id}/datasets/${dataset.id}`);
    },
    [navigate, task?.id]
  );

  const handleDeleteDataset = useCallback(
    async (datasetId: string) => {
      if (!task) return;

      try {
        await deleteDataset(task.id, datasetId);
        // Reload datasets after successful deletion
        await loadDatasets();
      } catch (err) {
        console.error("Failed to delete dataset:", err);
        setError("Failed to delete dataset. Please try again.");
      }
    },
    [task, loadDatasets]
  );

  const handleCreateDataset = useCallback(
    async (formData: DatasetFormData) => {
      if (!task) return;

      try {
        setIsCreating(true);
        const newDataset = await createDataset(task.id, formData);
        setIsCreateModalOpen(false);

        // Navigate to the newly created dataset
        navigate(`/tasks/${task.id}/datasets/${newDataset.id}`);
      } catch (err) {
        console.error("Failed to create dataset:", err);
        setError("Failed to create dataset. Please try again.");
        throw err;
      } finally {
        setIsCreating(false);
      }
    },
    [task, navigate]
  );

  const handleRetry = useCallback(() => {
    loadDatasets();
  }, [loadDatasets]);

  // Render loading state
  if (loading && datasets.length === 0) {
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

  // Render error state
  if (error && datasets.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={handleRetry}>
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      </Box>
    );
  }

  // Render empty state
  if (!loading && datasets.length === 0 && !debouncedSearchQuery) {
    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "400px",
          textAlign: "center",
          p: 3,
        }}
      >
        <FolderOpenIcon sx={{ fontSize: 64, color: "text.secondary", mb: 2 }} />
        <Typography variant="h5" gutterBottom sx={{ fontWeight: 500 }}>
          No datasets yet
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Get started by creating your first dataset
        </Typography>
        <Button
          variant="contained"
          color="primary"
          startIcon={<AddIcon />}
          onClick={() => setIsCreateModalOpen(true)}
          size="large"
        >
          Create Dataset
        </Button>
      </Box>
    );
  }

  // Render main content
  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Box>
          <Typography
            variant="h5"
            sx={{ fontWeight: 600, mb: 0.5, color: "text.primary" }}
          >
            Datasets
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Manage and organize your training and evaluation datasets
          </Typography>
        </Box>
        <Button
          variant="contained"
          color="primary"
          startIcon={<AddIcon />}
          onClick={() => setIsCreateModalOpen(true)}
        >
          Create Dataset
        </Button>
      </Box>

      {/* Search Bar */}
      <Box sx={{ mb: 3 }}>
        <TextField
          fullWidth
          placeholder="Search datasets by name..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          variant="outlined"
          size="small"
        />
      </Box>

      {/* Error Alert (when there's data) */}
      {error && datasets.length > 0 && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* No Search Results */}
      {!loading && datasets.length === 0 && debouncedSearchQuery && (
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "300px",
            textAlign: "center",
          }}
        >
          <SearchIcon sx={{ fontSize: 64, color: "text.secondary", mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            No datasets found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Try adjusting your search query
          </Typography>
        </Box>
      )}

      {/* Table */}
      {datasets.length > 0 && (
        <>
          <DatasetsTable
            datasets={datasets}
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSort={handleSort}
            onRowClick={handleRowClick}
            onDelete={handleDeleteDataset}
          />

          {/* Pagination */}
          <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 2 }}>
            <TablePagination
              component="div"
              count={totalCount}
              page={page}
              onPageChange={handlePageChange}
              rowsPerPage={pageSize}
              onRowsPerPageChange={handlePageSizeChange}
              rowsPerPageOptions={[5, 10, 25, 50]}
            />
          </Box>
        </>
      )}

      {/* Create Dataset Modal */}
      <CreateDatasetModal
        open={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateDataset}
        isLoading={isCreating}
      />
    </Box>
  );
};
