import { Alert, Box, Button, TablePagination } from "@mui/material";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Navigate, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { ConfirmationModal } from "../common/ConfirmationModal";

import { ConfigureColumnsModal } from "./ConfigureColumnsModal";
import { DatasetHeader } from "./DatasetHeader";
import { DatasetLoadingState } from "./DatasetLoadingState";
import { DatasetTable } from "./DatasetTable";
import { EditRowModal } from "./EditRowModal";
import { FillColumnModal } from "./FillColumnModal";
import { ImportDatasetModal } from "./ImportDatasetModal";
import { SyntheticDataModal } from "./synthetic";
import { VersionDrawer } from "./VersionDrawer";

import { getContentHeight } from "@/constants/layout";
import {
  DatasetContextProvider,
  selectAddRowData,
  selectEditRowData,
  selectFilteredRows,
  selectHasUnsavedChanges,
  useDatasetContext,
} from "@/contexts/dataset";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { EVENT_NAMES, track } from "@/services/amplitude";
import type { ColumnDefaults } from "@/types/dataset";
import { fetchAllDatasetRows } from "@/utils/datasetApi";
import { exportDatasetToCSV } from "@/utils/datasetExport";

export const DatasetDetailView: React.FC = () => {
  const { datasetId } = useParams<{ datasetId: string }>();

  if (!datasetId) {
    return <Navigate to="/datasets" replace />;
  }

  return (
    <DatasetContextProvider datasetId={datasetId}>
      <DatasetDetailViewContent datasetId={datasetId} />
    </DatasetContextProvider>
  );
};

interface DatasetDetailViewContentProps {
  datasetId: string;
}

const DatasetDetailViewContent: React.FC<DatasetDetailViewContentProps> = ({ datasetId }) => {
  const { state, dispatch, queries, mutations, showSnackbar } = useDatasetContext();
  const { task } = useTask();
  const navigate = useNavigate();
  const api = useApi();
  const [searchParams, setSearchParams] = useSearchParams();
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    track(EVENT_NAMES.DATASET_DETAIL_OPENED, { dataset_id: datasetId, task_id: task?.id });
  }, [datasetId, task?.id]);

  const filteredRows = useMemo(() => selectFilteredRows(state), [state]);
  const hasUnsavedChanges = selectHasUnsavedChanges(state);
  const addRowData = useMemo(() => selectAddRowData(state), [state]);
  const editRowData = useMemo(() => selectEditRowData(state), [state]);

  const versionFromUrl = searchParams.get("version");

  useEffect(() => {
    if (versionFromUrl) {
      const version = parseInt(versionFromUrl, 10);
      if (!isNaN(version)) {
        dispatch({ type: "VERSION/SELECT", payload: version });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (state.selectedVersion !== undefined) {
      setSearchParams({ version: state.selectedVersion.toString() }, { replace: true });
    } else {
      setSearchParams({}, { replace: true });
    }
  }, [state.selectedVersion, setSearchParams]);

  const handleBack = useCallback(() => {
    if (hasUnsavedChanges) {
      dispatch({ type: "UI/SHOW_CONFIRMATION", payload: { type: "unsavedNavigation" } });
    } else {
      navigate(`/tasks/${task?.id}/datasets`);
    }
  }, [hasUnsavedChanges, navigate, task?.id, dispatch]);

  const handleConfirmNavigation = useCallback(() => {
    dispatch({ type: "UI/HIDE_CONFIRMATION" });
    navigate(`/tasks/${task?.id}/datasets`);
  }, [navigate, task?.id, dispatch]);

  const handleViewExperiments = useCallback(() => {
    track(EVENT_NAMES.DATASET_EXPERIMENTS_VIEWED, { dataset_id: datasetId, task_id: task?.id });
    navigate(`/tasks/${task?.id}/datasets/${datasetId}/experiments`);
  }, [navigate, task?.id, datasetId]);

  const handleVersionSwitch = useCallback(
    (versionNumber: number) => {
      if (hasUnsavedChanges) {
        dispatch({
          type: "UI/SHOW_CONFIRMATION",
          payload: { type: "unsavedVersionSwitch", targetVersion: versionNumber },
        });
        return;
      }
      track(EVENT_NAMES.DATASET_VERSION_SELECTED, { dataset_id: datasetId, task_id: task?.id });
      dispatch({ type: "VERSION/SELECT", payload: versionNumber });
    },
    [hasUnsavedChanges, dispatch, datasetId, task?.id]
  );

  const handleConfirmVersionSwitch = useCallback(() => {
    if (state.confirmation.targetVersion !== null) {
      track(EVENT_NAMES.DATASET_VERSION_SWITCH_CONFIRMED, { dataset_id: datasetId, task_id: task?.id });
      dispatch({ type: "VERSION/SELECT", payload: state.confirmation.targetVersion });
      dispatch({ type: "DATA/CLEAR_CHANGES" });
    }
    dispatch({ type: "UI/HIDE_CONFIRMATION" });
  }, [state.confirmation.targetVersion, dispatch, datasetId, task?.id]);

  const handleAddRow = useCallback(
    async (rowData: Record<string, unknown>) => {
      track(EVENT_NAMES.DATASET_ROW_ADDED, { dataset_id: datasetId, task_id: task?.id });
      dispatch({ type: "DATA/ADD_ROW", payload: rowData });
      dispatch({ type: "UI/TOGGLE_ADD_MODAL", payload: false });
    },
    [dispatch, datasetId, task?.id]
  );

  const handleUpdateRow = useCallback(
    async (rowData: Record<string, unknown>) => {
      if (!state.modals.edit.row) return;
      track(EVENT_NAMES.DATASET_ROW_UPDATED, { dataset_id: datasetId, task_id: task?.id });
      dispatch({ type: "DATA/UPDATE_ROW", payload: { id: state.modals.edit.row.id, data: rowData } });
      dispatch({ type: "UI/CLOSE_EDIT_MODAL" });
    },
    [state.modals.edit.row, dispatch, datasetId, task?.id]
  );

  const handleDeleteRow = useCallback(
    (id: string) => {
      track(EVENT_NAMES.DATASET_ROW_DELETED, { dataset_id: datasetId, task_id: task?.id });
      dispatch({ type: "DATA/DELETE_ROW", payload: id });
    },
    [dispatch, datasetId, task?.id]
  );

  const handleConfigureColumns = useCallback(
    async (columns: string[], newColumnDefaults: ColumnDefaults, applyToExisting: boolean) => {
      dispatch({ type: "DATA/SET_COLUMNS", payload: columns });

      if (queries.dataset && datasetId) {
        const existingMetadata = (queries.dataset.metadata as Record<string, unknown>) ?? {};
        await mutations.updateDataset.mutateAsync({
          name: queries.dataset.name,
          description: queries.dataset.description ?? undefined,
          metadata: {
            ...existingMetadata,
            columnDefaults: newColumnDefaults,
          },
        });

        if (applyToExisting && queries.totalRowCount > 0) {
          mutations.applyDefaults.mutate({ columnDefaults: newColumnDefaults });
        }
      }

      dispatch({ type: "UI/TOGGLE_CONFIGURE_MODAL", payload: false });
    },
    [dispatch, queries.dataset, queries.totalRowCount, datasetId, mutations]
  );

  const handleImportData = useCallback(
    (csvColumns: string[], csvRows: Record<string, string>[]) => {
      dispatch({ type: "DATA/IMPORT_ROWS", payload: { columns: csvColumns, rows: csvRows } });
      dispatch({ type: "UI/TOGGLE_IMPORT_MODAL", payload: false });
    },
    [dispatch]
  );

  const handleFillColumn = useCallback(
    (columnName: string) => {
      if (hasUnsavedChanges) {
        dispatch({
          type: "UI/SHOW_CONFIRMATION",
          payload: { type: "unsavedFillColumn", targetColumn: columnName },
        });
        return;
      }
      track(EVENT_NAMES.DATASET_FILL_COLUMN_OPENED, { dataset_id: datasetId, task_id: task?.id });
      dispatch({ type: "UI/OPEN_FILL_MODAL", payload: columnName });
    },
    [hasUnsavedChanges, dispatch, datasetId, task?.id]
  );

  const handleConfirmFillColumn = useCallback(() => {
    if (state.confirmation.targetColumn) {
      dispatch({ type: "DATA/CLEAR_CHANGES" });
      dispatch({ type: "UI/OPEN_FILL_MODAL", payload: state.confirmation.targetColumn });
    }
    dispatch({ type: "UI/HIDE_CONFIRMATION" });
  }, [state.confirmation.targetColumn, dispatch]);

  const handleFillColumnApply = useCallback(
    (value: string) => {
      if (state.modals.fill.columnName) {
        mutations.fillColumn.mutate({ columnName: state.modals.fill.columnName, value });
      }
    },
    [state.modals.fill.columnName, mutations.fillColumn]
  );

  const handleExport = useCallback(async () => {
    if (!queries.dataset || !api || !datasetId || queries.currentVersion === undefined || queries.totalRowCount === 0) {
      return;
    }

    track(EVENT_NAMES.DATASET_EXPORT_CLICKED, { dataset_id: datasetId, task_id: task?.id });
    setIsExporting(true);
    try {
      const allRows = await fetchAllDatasetRows(api, datasetId, queries.currentVersion);
      exportDatasetToCSV(queries.dataset.name, allRows);
      showSnackbar("Dataset exported successfully!", "success");
    } catch {
      showSnackbar("Failed to export dataset. Please try again.", "error");
    } finally {
      setIsExporting(false);
    }
  }, [queries.dataset, api, datasetId, queries.currentVersion, queries.totalRowCount, showSnackbar]);

  const handleAcceptSyntheticRows = useCallback(
    (rows: { data: { column_name: string; column_value: string }[] }[]) => {
      rows.forEach((row) => {
        const rowData: Record<string, unknown> = {};
        row.data.forEach((col) => {
          rowData[col.column_name] = col.column_value;
        });
        dispatch({ type: "DATA/ADD_ROW", payload: rowData });
      });
      dispatch({ type: "UI/TOGGLE_SYNTHETIC_MODAL", payload: false });
      showSnackbar(`Added ${rows.length} synthetic row${rows.length !== 1 ? "s" : ""}`, "success");
    },
    [dispatch, showSnackbar]
  );

  if (queries.isLoading && !queries.dataset) {
    return <DatasetLoadingState type="full" />;
  }

  if (!queries.dataset) {
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
          {queries.datasetError?.message || "Dataset not found"}
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
          flex: state.versionDrawerOpen ? "1 1 auto" : "1 1 100%",
          transition: "flex 0.3s ease",
          display: "grid",
          gridTemplateRows: "auto 1fr auto",
          overflow: "hidden",
          minWidth: 0,
        }}
      >
        <DatasetHeader
          datasetName={queries.dataset.name}
          description={queries.dataset.description}
          hasUnsavedChanges={hasUnsavedChanges}
          isSaving={mutations.save.isPending}
          isExporting={isExporting}
          canSave={hasUnsavedChanges && !mutations.save.isPending}
          canAddRow={state.columns.length > 0}
          columnCount={state.columns.length}
          rowCount={state.rows.length}
          totalRowCount={queries.totalRowCount}
          onBack={handleBack}
          onSave={() => mutations.save.mutate()}
          onConfigureColumns={() => {
            track(EVENT_NAMES.DATASET_COLUMNS_CONFIG_OPENED, { dataset_id: datasetId, task_id: task?.id });
            dispatch({ type: "UI/TOGGLE_CONFIGURE_MODAL", payload: true });
          }}
          onAddRow={() => dispatch({ type: "UI/TOGGLE_ADD_MODAL", payload: true })}
          onExport={handleExport}
          onImport={() => {
            track(EVENT_NAMES.DATASET_IMPORT_OPENED, { dataset_id: datasetId, task_id: task?.id });
            dispatch({ type: "UI/TOGGLE_IMPORT_MODAL", payload: true });
          }}
          onOpenVersions={() => {
            track(EVENT_NAMES.DATASET_VERSION_DRAWER_OPENED, { dataset_id: datasetId, task_id: task?.id });
            dispatch({ type: "UI/TOGGLE_VERSION_DRAWER", payload: true });
          }}
          onViewExperiments={handleViewExperiments}
          onGenerateSynthetic={() => dispatch({ type: "UI/TOGGLE_SYNTHETIC_MODAL", payload: true })}
          searchValue={state.searchQuery}
          onSearchChange={(q) => {
            track(EVENT_NAMES.DATASET_SEARCH_CHANGED, { dataset_id: datasetId, task_id: task?.id });
            dispatch({ type: "VIEW/SET_SEARCH", payload: q });
          }}
          onSearchClear={() => {
            track(EVENT_NAMES.DATASET_SEARCH_CHANGED, { dataset_id: datasetId, task_id: task?.id });
            dispatch({ type: "VIEW/SET_SEARCH", payload: "" });
          }}
        />

        {state.columns.length === 0 ? (
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
            datasetId={datasetId}
            columns={state.columns}
            rows={filteredRows}
            isLoading={queries.versionLoading}
            error={queries.versionError}
            sortColumn={state.sorting.column}
            sortDirection={state.sorting.direction}
            onSort={(col) => {
              track(EVENT_NAMES.DATASET_SORT_CHANGED, { dataset_id: datasetId, task_id: task?.id });
              dispatch({ type: "VIEW/TOGGLE_SORT", payload: col });
            }}
            onEditRow={(row) => dispatch({ type: "UI/OPEN_EDIT_MODAL", payload: row })}
            onDeleteRow={handleDeleteRow}
            onFillColumn={handleFillColumn}
            searchQuery={state.searchQuery}
          />
        )}

        {state.rows.length > 0 && (
          <Box
            sx={{
              borderTop: 1,
              borderColor: "divider",
              backgroundColor: "background.paper",
            }}
          >
            <TablePagination
              component="div"
              count={queries.totalRowCount}
              page={state.pagination.page}
              onPageChange={(_, p) => {
                track(EVENT_NAMES.DATASET_PAGINATION_CHANGED, { dataset_id: datasetId, task_id: task?.id });
                dispatch({ type: "VIEW/SET_PAGE", payload: p });
              }}
              rowsPerPage={state.pagination.rowsPerPage}
              onRowsPerPageChange={(e) => {
                track(EVENT_NAMES.DATASET_PAGINATION_CHANGED, { dataset_id: datasetId, task_id: task?.id });
                dispatch({ type: "VIEW/SET_ROWS_PER_PAGE", payload: parseInt(e.target.value, 10) });
              }}
              rowsPerPageOptions={[10, 25, 50, 100]}
            />
          </Box>
        )}
      </Box>

      {state.versionDrawerOpen && task && datasetId && queries.dataset && (
        <VersionDrawer
          taskId={task.id}
          datasetId={datasetId}
          datasetName={queries.dataset.name}
          currentVersionNumber={queries.currentVersion}
          latestVersionNumber={queries.latestVersion}
          selectedVersionNumber={state.confirmation.targetVersion}
          onVersionClick={(v) => dispatch({ type: "UI/SHOW_CONFIRMATION", payload: { type: "unsavedVersionSwitch", targetVersion: v } })}
          onClose={() => dispatch({ type: "UI/TOGGLE_VERSION_DRAWER", payload: false })}
          onVersionSelect={handleVersionSwitch}
        />
      )}

      {state.modals.edit.row && (
        <EditRowModal
          open={state.modals.edit.open}
          onClose={() => dispatch({ type: "UI/CLOSE_EDIT_MODAL" })}
          onSubmit={handleUpdateRow}
          rowData={editRowData}
          rowId={state.modals.edit.row.id}
          isLoading={false}
        />
      )}

      <EditRowModal
        open={state.modals.add}
        onClose={() => dispatch({ type: "UI/TOGGLE_ADD_MODAL", payload: false })}
        onSubmit={handleAddRow}
        rowData={addRowData}
        rowId="new"
        isLoading={false}
      />

      <ConfigureColumnsModal
        open={state.modals.configure}
        onClose={() => dispatch({ type: "UI/TOGGLE_CONFIGURE_MODAL", payload: false })}
        onSave={handleConfigureColumns}
        currentColumns={state.columns}
        currentColumnDefaults={state.columnDefaults}
        existingRowCount={queries.totalRowCount}
        datasetId={datasetId}
        taskId={task?.id}
      />

      <ImportDatasetModal
        open={state.modals.import}
        onClose={() => dispatch({ type: "UI/TOGGLE_IMPORT_MODAL", payload: false })}
        onImport={handleImportData}
        currentRowCount={state.rows.length}
        datasetId={datasetId}
        taskId={task?.id}
      />

      <FillColumnModal
        open={state.modals.fill.open}
        columnName={state.modals.fill.columnName ?? ""}
        totalRowCount={queries.totalRowCount}
        onClose={() => dispatch({ type: "UI/CLOSE_FILL_MODAL" })}
        onApply={handleFillColumnApply}
        isLoading={mutations.fillColumn.isPending}
      />

      {datasetId && queries.currentVersion !== undefined && (
        <SyntheticDataModal
          open={state.modals.synthetic}
          onClose={() => dispatch({ type: "UI/TOGGLE_SYNTHETIC_MODAL", payload: false })}
          columns={state.columns}
          existingRowsSample={state.rows.slice(0, 10)}
          datasetId={datasetId}
          versionNumber={queries.currentVersion}
          onAcceptRows={handleAcceptSyntheticRows}
        />
      )}

      <ConfirmationModal
        open={state.confirmation.type === "unsavedNavigation"}
        onClose={() => dispatch({ type: "UI/HIDE_CONFIRMATION" })}
        onConfirm={handleConfirmNavigation}
        title="Unsaved Changes"
        message="You have unsaved changes. If you leave now, your changes will be lost. Are you sure you want to continue?"
        confirmText="Leave Without Saving"
        cancelText="Stay"
      />

      <ConfirmationModal
        open={state.confirmation.type === "unsavedVersionSwitch" && hasUnsavedChanges}
        onClose={() => dispatch({ type: "UI/HIDE_CONFIRMATION" })}
        onConfirm={handleConfirmVersionSwitch}
        title="Unsaved Changes"
        message="You have unsaved changes in the current version. If you switch versions now, your changes will be lost. Are you sure you want to continue?"
        confirmText="Switch Version"
        cancelText="Cancel"
      />

      <ConfirmationModal
        open={state.confirmation.type === "unsavedFillColumn" && hasUnsavedChanges}
        onClose={() => dispatch({ type: "UI/HIDE_CONFIRMATION" })}
        onConfirm={handleConfirmFillColumn}
        title="Unsaved Changes"
        message="You have unsaved changes. Filling a column will discard your changes and update all rows on the server. Are you sure you want to continue?"
        confirmText="Discard & Fill Column"
        cancelText="Cancel"
      />
    </Box>
  );
};
