import { Alert, Box, TablePagination } from "@mui/material";
import React, { useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { DatasetFormModal } from "./DatasetFormModal";
import { DatasetsEmptyState } from "./DatasetsEmptyState";
import { DatasetsErrorState } from "./DatasetsErrorState";
import { DatasetsLoadingState } from "./DatasetsLoadingState";
import { DatasetsSearchBar } from "./DatasetsSearchBar";
import { DatasetsTable } from "./DatasetsTable";
import { DatasetsViewHeader } from "./DatasetsViewHeader";

import { PAGE_SIZE_OPTIONS } from "@/constants/datasetConstants";
import { getContentHeight } from "@/constants/layout";
import { useCreateDatasetMutation } from "@/hooks/datasets/useCreateDatasetMutation";
import { useDatasetsModalState } from "@/hooks/datasets/useDatasetsModalState";
import { useDatasetsSearchQuery } from "@/hooks/datasets/useDatasetsSearchQuery";
import { useDatasetsSortingQuery } from "@/hooks/datasets/useDatasetsSortingQuery";
import { useDeleteDatasetMutation } from "@/hooks/datasets/useDeleteDatasetMutation";
import { useUpdateDatasetMutation } from "@/hooks/datasets/useUpdateDatasetMutation";
import { useDatasets } from "@/hooks/useDatasets";
import { usePagination } from "@/hooks/usePagination";
import { useTask } from "@/hooks/useTask";
import type { DatasetResponse, NewDatasetRequest } from "@/lib/api-client/api-client";
import { EVENT_NAMES, track } from "@/services/amplitude";

export const DatasetsView: React.FC = () => {
  const { task } = useTask();
  const navigate = useNavigate();

  const pagination = usePagination();
  const search = useDatasetsSearchQuery(pagination.resetPage);
  const sorting = useDatasetsSortingQuery();
  const modals = useDatasetsModalState();

  const filters = useMemo(
    () => ({
      searchQuery: search.debouncedSearchQuery,
      sortOrder: sorting.sortOrder,
      page: pagination.page,
      pageSize: pagination.rowsPerPage,
    }),
    [search.debouncedSearchQuery, sorting.sortOrder, pagination.page, pagination.rowsPerPage]
  );

  const { datasets, count, error, isLoading, refetch } = useDatasets(task?.id, filters);

  const createMutation = useCreateDatasetMutation(task?.id, (newDataset) => {
    modals.closeCreateModal();
    navigate(`/tasks/${task?.id}/datasets/${newDataset.id}`);
  });

  const updateMutation = useUpdateDatasetMutation(() => {
    modals.closeEditModal();
  });

  const deleteMutation = useDeleteDatasetMutation();

  const handleRowClick = useCallback(
    (dataset: DatasetResponse) => {
      track(EVENT_NAMES.DATASET_SELECTED, {
        dataset_id: dataset.id,
        task_id: task?.id,
      });
      navigate(`/tasks/${task?.id}/datasets/${dataset.id}`);
    },
    [navigate, task?.id]
  );

  const handleOpenCreate = useCallback(() => {
    track(EVENT_NAMES.DATASET_CREATE_OPENED, { task_id: task?.id });
    modals.openCreateModal();
  }, [modals, task?.id]);

  const handleCreateDataset = useCallback(
    async (formData: NewDatasetRequest) => {
      await createMutation.mutateAsync(formData);
    },
    [createMutation]
  );

  const handleUpdateDataset = useCallback(
    async (formData: NewDatasetRequest) => {
      if (!modals.editingDataset) return;
      await updateMutation.mutateAsync({
        ...formData,
        id: modals.editingDataset.id,
      });
    },
    [updateMutation, modals.editingDataset]
  );

  if (isLoading && datasets.length === 0) {
    return <DatasetsLoadingState />;
  }

  if (error && datasets.length === 0) {
    return <DatasetsErrorState error={error} onRetry={refetch} />;
  }

  return (
    <Box
      sx={{
        width: "100%",
        height: getContentHeight(),
        display: "grid",
        gridTemplateRows: "auto auto auto 1fr auto",
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          px: 3,
          pt: 3,
          pb: 2,
          borderBottom: 1,
          borderColor: "divider",
          backgroundColor: "background.paper",
        }}
      >
        <DatasetsViewHeader onCreateDataset={handleOpenCreate} />
      </Box>
      <Box
        sx={{
          px: 3,
          pt: 2,
          pb: 2,
          borderBottom: 1,
          borderColor: "divider",
          backgroundColor: "background.paper",
        }}
      >
        <DatasetsSearchBar
          value={search.searchQuery}
          onChange={(value) => {
            track(EVENT_NAMES.DATASET_SEARCH_CHANGED, { task_id: task?.id });
            search.setSearchQuery(value);
          }}
        />
      </Box>

      {error && datasets.length > 0 && (
        <Box sx={{ px: 3, pt: 2 }}>
          <Alert severity="error">{error.message || "An error occurred"}</Alert>
        </Box>
      )}

      <Box
        sx={{
          overflow: "auto",
          minHeight: 0,
        }}
      >
        {!isLoading && datasets.length === 0 ? (
          <DatasetsEmptyState
            type={search.debouncedSearchQuery ? "no-results" : "no-datasets"}
            onCreateDataset={!search.debouncedSearchQuery ? handleOpenCreate : undefined}
          />
        ) : (
          <DatasetsTable
            datasets={datasets}
            sortOrder={sorting.sortOrder}
            onSort={() => {
              track(EVENT_NAMES.DATASET_SORT_CHANGED, { task_id: task?.id });
              sorting.handleSort();
            }}
            onRowClick={handleRowClick}
            onEdit={(dataset) => {
              track(EVENT_NAMES.DATASET_EDIT_OPENED, { dataset_id: dataset.id, task_id: task?.id });
              modals.openEditModal(dataset);
            }}
            onDelete={deleteMutation.mutateAsync}
          />
        )}
      </Box>

      {datasets.length > 0 && (
        <Box
          sx={{
            borderTop: 1,
            borderColor: "divider",
            backgroundColor: "background.paper",
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          <TablePagination
            component="div"
            count={count}
            page={pagination.page}
            onPageChange={(event, page) => {
              track(EVENT_NAMES.DATASET_PAGINATION_CHANGED, { task_id: task?.id });
              pagination.handlePageChange(event, page);
            }}
            rowsPerPage={pagination.rowsPerPage}
            onRowsPerPageChange={(event: React.ChangeEvent<HTMLInputElement>) => {
              track(EVENT_NAMES.DATASET_PAGINATION_CHANGED, { task_id: task?.id });
              pagination.handleRowsPerPageChange(event);
            }}
            rowsPerPageOptions={PAGE_SIZE_OPTIONS}
          />
        </Box>
      )}

      <DatasetFormModal
        open={modals.isCreateModalOpen}
        onClose={modals.closeCreateModal}
        onSubmit={handleCreateDataset}
        isLoading={createMutation.isPending}
        mode="create"
      />

      <DatasetFormModal
        open={modals.isEditModalOpen}
        onClose={modals.closeEditModal}
        onSubmit={handleUpdateDataset}
        isLoading={updateMutation.isPending}
        mode="edit"
        datasetId={modals.editingDataset?.id}
        initialData={
          modals.editingDataset
            ? {
                name: modals.editingDataset.name,
                description: modals.editingDataset.description || "",
              }
            : undefined
        }
      />
    </Box>
  );
};
