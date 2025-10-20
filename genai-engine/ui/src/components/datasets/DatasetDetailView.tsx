import { Alert, Box, Button, TablePagination } from "@mui/material";
import React, { useCallback, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { AddColumnDialog } from "./AddColumnDialog";
import { DatasetHeader } from "./DatasetHeader";
import { DatasetLoadingState } from "./DatasetLoadingState";
import { DatasetTable } from "./DatasetTable";
import { EditRowModal } from "./EditRowModal";
import { VersionDrawer } from "./VersionDrawer";

import { getContentHeight } from "@/constants/layout";
import { useDatasetLocalState } from "@/hooks/datasets/useDatasetLocalState";
import { useDatasetModalState } from "@/hooks/datasets/useDatasetModalState";
import { useDatasetPagination } from "@/hooks/datasets/useDatasetPagination";
import { useDatasetSaveMutation } from "@/hooks/datasets/useDatasetSaveMutation";
import { useDatasetSearch } from "@/hooks/datasets/useDatasetSearch";
import { useDatasetSorting } from "@/hooks/datasets/useDatasetSorting";
import { useDatasetVersionSelection } from "@/hooks/datasets/useDatasetVersionSelection";
import { useDataset } from "@/hooks/useDataset";
import { useDatasetLatestVersion } from "@/hooks/useDatasetLatestVersion";
import { useDatasetVersionData } from "@/hooks/useDatasetVersionData";
import { useTask } from "@/hooks/useTask";
import { convertFromApiFormat } from "@/utils/datasetRowUtils";
import { createEmptyRow } from "@/utils/datasetUtils";

export const DatasetDetailView: React.FC = () => {
  const { datasetId } = useParams<{ datasetId: string }>();
  const { task } = useTask();
  const navigate = useNavigate();

  const {
    dataset,
    isLoading: datasetLoading,
    error: datasetError,
  } = useDataset(datasetId);
  const { latestVersion, isLoading: latestVersionLoading } =
    useDatasetLatestVersion(datasetId);

  const pagination = useDatasetPagination();

  const versionSelection = useDatasetVersionSelection(
    latestVersion?.version_number,
    () => {
      pagination.resetPage();
    }
  );

  const {
    version: versionData,
    isLoading: versionLoading,
    error: versionError,
  } = useDatasetVersionData(
    datasetId,
    versionSelection.currentVersion,
    pagination.page,
    pagination.rowsPerPage
  );

  const localState = useDatasetLocalState(versionData);

  const sorting = useDatasetSorting(localState.localRows);
  const search = useDatasetSearch(sorting.sortedRows);
  const modals = useDatasetModalState();

  const save = useDatasetSaveMutation(
    datasetId,
    localState.pendingChanges,
    localState.hasUnsavedChanges,
    () => {
      localState.clearChanges();
      versionSelection.resetToLatest();
    }
  );

  const isLoading = datasetLoading || latestVersionLoading;
  const hasError = datasetError || !dataset;
  const totalRows = versionData?.total_count ?? localState.localRows.length;

  const handleBack = useCallback(() => {
    navigate(`/tasks/${task?.id}/datasets`);
  }, [navigate, task?.id]);

  const handleVersionSwitch = useCallback(
    (versionNumber: number) => {
      versionSelection.handleVersionSwitch(versionNumber);
      localState.clearChanges();
    },
    [versionSelection, localState]
  );

  const handleUpdateRow = useCallback(
    async (rowData: Record<string, unknown>) => {
      if (!modals.editingRow) return;
      localState.updateRow(modals.editingRow.id, rowData);
      modals.closeEditModal();
    },
    [modals, localState]
  );

  const handleAddRowSubmit = useCallback(
    async (rowData: Record<string, unknown>) => {
      localState.addRow(rowData);
      modals.closeAddModal();
    },
    [localState, modals]
  );

  const handleAddColumn = useCallback(
    async (columnName: string) => {
      localState.addColumn(columnName);
      modals.closeAddColumnDialog();
    },
    [localState, modals]
  );

  const editRowData = useMemo(() => {
    if (!modals.editingRow) return {};

    const existingData = convertFromApiFormat(modals.editingRow);
    const allColumnsData = createEmptyRow(localState.localColumns);

    return { ...allColumnsData, ...existingData };
  }, [modals.editingRow, localState.localColumns]);

  const addRowData = useMemo(() => {
    return createEmptyRow(localState.localColumns);
  }, [localState.localColumns]);

  if (isLoading) {
    return <DatasetLoadingState type="full" />;
  }

  if (hasError) {
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
          {datasetError?.message || "Dataset not found"}
        </Alert>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        width: "100%",
        height: getContentHeight(),
        display: "flex",
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          flex: modals.isVersionDrawerOpen ? "1 1 auto" : "1 1 100%",
          transition: "flex 0.3s ease",
          display: "grid",
          gridTemplateRows: "auto 1fr auto",
          overflow: "hidden",
          minWidth: 0,
        }}
      >
        <DatasetHeader
          datasetName={dataset.name}
          description={dataset.description}
          hasUnsavedChanges={localState.hasUnsavedChanges}
          isSaving={save.isSaving}
          canSave={save.canSave}
          canAddRow={localState.localColumns.length > 0}
          onBack={handleBack}
          onSave={save.saveChanges}
          onAddColumn={modals.openAddColumnDialog}
          onAddRow={modals.openAddModal}
          onOpenVersions={modals.openVersionDrawer}
          searchValue={search.searchQuery}
          onSearchChange={search.setSearchQuery}
          onSearchClear={search.handleClearSearch}
        />

        {localState.localColumns.length === 0 ? (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flex: 1,
            }}
          >
            <Box sx={{ textAlign: "center", p: 3 }}>
              <Box
                sx={{
                  fontWeight: 600,
                  fontSize: "1.25rem",
                  color: "text.primary",
                  mb: 1,
                }}
              >
                No columns defined
              </Box>
              <Box sx={{ color: "text.secondary", mb: 2 }}>
                Start by adding columns to define your dataset structure.
                <br />
                Click "Add Column" to get started.
              </Box>
            </Box>
          </Box>
        ) : (
          <DatasetTable
            columns={localState.localColumns}
            rows={search.filteredRows}
            isLoading={versionLoading}
            error={versionError}
            sortColumn={sorting.sortColumn}
            sortDirection={sorting.sortDirection}
            onSort={sorting.handleSort}
            onEditRow={modals.openEditModal}
            onDeleteRow={localState.deleteRow}
            searchQuery={search.searchQuery}
          />
        )}

        {localState.localRows.length > 0 && (
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
              page={pagination.page}
              onPageChange={pagination.handlePageChange}
              rowsPerPage={pagination.rowsPerPage}
              onRowsPerPageChange={pagination.handleRowsPerPageChange}
              rowsPerPageOptions={[10, 25, 50, 100]}
            />
          </Box>
        )}
      </Box>

      {modals.isVersionDrawerOpen && task && datasetId && dataset && (
        <VersionDrawer
          taskId={task.id}
          datasetId={datasetId}
          datasetName={dataset.name}
          currentVersionNumber={versionSelection.currentVersion}
          latestVersionNumber={latestVersion?.version_number}
          onClose={modals.closeVersionDrawer}
          onVersionSelect={handleVersionSwitch}
        />
      )}

      {modals.editingRow && (
        <EditRowModal
          open={modals.isEditModalOpen}
          onClose={modals.closeEditModal}
          onSubmit={handleUpdateRow}
          rowData={editRowData}
          rowId={modals.editingRow.id}
          isLoading={false}
        />
      )}

      <EditRowModal
        open={modals.isAddModalOpen}
        onClose={modals.closeAddModal}
        onSubmit={handleAddRowSubmit}
        rowData={addRowData}
        rowId="new"
        isLoading={false}
      />

      <AddColumnDialog
        open={modals.isAddColumnDialogOpen}
        onClose={modals.closeAddColumnDialog}
        onSubmit={handleAddColumn}
        existingColumns={localState.localColumns}
        isLoading={false}
      />
    </Box>
  );
};
