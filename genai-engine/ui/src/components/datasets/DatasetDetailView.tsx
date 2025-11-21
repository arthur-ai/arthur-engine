import { Alert, Box, Button, Snackbar, TablePagination } from "@mui/material";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { ConfirmationModal } from "../common/ConfirmationModal";

import { ConfigureColumnsModal } from "./ConfigureColumnsModal";
import { DatasetHeader } from "./DatasetHeader";
import { DatasetLoadingState } from "./DatasetLoadingState";
import { DatasetTable } from "./DatasetTable";
import { EditRowModal } from "./EditRowModal";
import { ImportDatasetModal } from "./ImportDatasetModal";
import { VersionDrawer } from "./VersionDrawer";

import { MAX_DATASET_ROWS } from "@/constants/datasetConstants";
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
import useSnackbar from "@/hooks/useSnackbar";
import { useTask } from "@/hooks/useTask";
import { exportDatasetToCSV } from "@/utils/datasetExport";
import { convertFromApiFormat } from "@/utils/datasetRowUtils";
import { createEmptyRow } from "@/utils/datasetUtils";

export const DatasetDetailView: React.FC = () => {
  const { datasetId } = useParams<{ datasetId: string }>();
  const { task } = useTask();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();
  const [showUnsavedChangesModal, setShowUnsavedChangesModal] = useState(false);
  const [selectedVersionForSwitch, setSelectedVersionForSwitch] = useState<number | null>(null);

  const { dataset, isLoading: datasetLoading, error: datasetError } = useDataset(datasetId);
  const { latestVersion, isLoading: latestVersionLoading } = useDatasetLatestVersion(datasetId);

  const pagination = useDatasetPagination();

  // Get version from URL query param
  const versionFromUrl = searchParams.get("version");
  const initialVersion = versionFromUrl ? parseInt(versionFromUrl, 10) : undefined;

  const versionSelection = useDatasetVersionSelection(latestVersion?.version_number, () => {
    pagination.resetPage();
  });

  const {
    version: versionData,
    isLoading: versionLoading,
    error: versionError,
  } = useDatasetVersionData(datasetId, versionSelection.currentVersion, pagination.page, pagination.rowsPerPage);

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
      showSnackbar("Changes saved successfully!", "success");
    },
    (error) => {
      showSnackbar(error.message || "Failed to save changes. Please try again.", "error");
    }
  );

  const isLoading = datasetLoading || latestVersionLoading;
  const hasError = datasetError || !dataset;
  const totalRows = versionData?.total_count ?? localState.localRows.length;

  // Initialize version from URL on mount
  useEffect(() => {
    if (initialVersion && !isNaN(initialVersion)) {
      versionSelection.handleVersionSwitch(initialVersion);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on mount

  // Update URL when version selection changes
  useEffect(() => {
    if (versionSelection.selectedVersion !== undefined) {
      setSearchParams({ version: versionSelection.selectedVersion.toString() });
    } else {
      // Remove version param when showing latest version
      setSearchParams({});
    }
  }, [versionSelection.selectedVersion, setSearchParams]);

  const handleBack = useCallback(() => {
    if (localState.hasUnsavedChanges) {
      setShowUnsavedChangesModal(true);
    } else {
      navigate(`/tasks/${task?.id}/datasets`);
    }
  }, [localState.hasUnsavedChanges, navigate, task?.id]);

  const handleConfirmNavigation = useCallback(() => {
    navigate(`/tasks/${task?.id}/datasets`);
  }, [navigate, task?.id]);

  const handleManageTransforms = useCallback(() => {
    navigate(`/tasks/${task?.id}/datasets/${datasetId}/transforms`);
  }, [navigate, task?.id, datasetId]);

  const handleViewExperiments = useCallback(() => {
    navigate(`/tasks/${task?.id}/datasets/${datasetId}/experiments`);
  }, [navigate, task?.id, datasetId]);

  const handleVersionSwitch = useCallback(
    (versionNumber: number) => {
      if (localState.hasUnsavedChanges) {
        return;
      }
      versionSelection.handleVersionSwitch(versionNumber);
      setSelectedVersionForSwitch(null);
    },
    [localState.hasUnsavedChanges, versionSelection]
  );

  const handleConfirmVersionSwitch = useCallback(() => {
    if (selectedVersionForSwitch !== null) {
      versionSelection.handleVersionSwitch(selectedVersionForSwitch);
      localState.clearChanges();
      setSelectedVersionForSwitch(null);
    }
  }, [selectedVersionForSwitch, versionSelection, localState]);

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
      try {
        localState.addRow(rowData);
        modals.closeAddModal();
      } catch {
        showSnackbar(`Cannot add row: Maximum dataset size of ${MAX_DATASET_ROWS} rows reached.`, "error");
      }
    },
    [localState, modals, showSnackbar]
  );

  const handleConfigureColumns = useCallback(
    (columns: string[]) => {
      localState.setColumns(columns);
    },
    [localState]
  );

  const handleExport = useCallback(() => {
    if (!dataset || localState.localRows.length === 0) return;
    try {
      exportDatasetToCSV(dataset.name, localState.localRows);
      showSnackbar("Dataset exported successfully!", "success");
    } catch {
      showSnackbar("Failed to export dataset. Please try again.", "error");
    }
  }, [dataset, localState.localRows, showSnackbar]);

  const handleImportData = useCallback(
    (csvColumns: string[], csvRows: Record<string, string>[]) => {
      const existingColumnsSet = new Set(localState.localColumns);
      const newColumns = csvColumns.filter((col) => !existingColumnsSet.has(col));
      const mergedColumns = [...localState.localColumns, ...newColumns];

      if (newColumns.length > 0) {
        localState.setColumns(mergedColumns);
      }

      csvRows.forEach((rowData) => {
        const completeRowData: Record<string, unknown> = {};
        mergedColumns.forEach((col) => {
          completeRowData[col] = rowData[col] ?? "";
        });
        localState.addRow(completeRowData);
      });

      modals.closeImportModal();
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
          columnCount={localState.localColumns.length}
          rowCount={localState.localRows.length}
          onBack={handleBack}
          onSave={save.saveChanges}
          onConfigureColumns={modals.openConfigureColumns}
          onAddRow={modals.openAddModal}
          onExport={handleExport}
          onImport={modals.openImportModal}
          onOpenVersions={modals.openVersionDrawer}
          onManageTransforms={handleManageTransforms}
          onViewExperiments={handleViewExperiments}
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
                Click "Configure Columns" to get started.
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
          selectedVersionNumber={selectedVersionForSwitch}
          onVersionClick={setSelectedVersionForSwitch}
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

      <ConfigureColumnsModal
        open={modals.isConfigureColumnsOpen}
        onClose={modals.closeConfigureColumns}
        onSave={handleConfigureColumns}
        currentColumns={localState.localColumns}
      />

      <ImportDatasetModal
        open={modals.isImportModalOpen}
        onClose={modals.closeImportModal}
        onImport={handleImportData}
        currentRowCount={localState.localRows.length}
      />

      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>

      <ConfirmationModal
        open={showUnsavedChangesModal}
        onClose={() => setShowUnsavedChangesModal(false)}
        onConfirm={handleConfirmNavigation}
        title="Unsaved Changes"
        message="You have unsaved changes. If you leave now, your changes will be lost. Are you sure you want to continue?"
        confirmText="Leave Without Saving"
        cancelText="Stay"
      />

      <ConfirmationModal
        open={selectedVersionForSwitch !== null && localState.hasUnsavedChanges}
        onClose={() => setSelectedVersionForSwitch(null)}
        onConfirm={handleConfirmVersionSwitch}
        title="Unsaved Changes"
        message="You have unsaved changes in the current version. If you switch versions now, your changes will be lost. Are you sure you want to continue?"
        confirmText="Switch Version"
        cancelText="Cancel"
      />
    </Box>
  );
};
