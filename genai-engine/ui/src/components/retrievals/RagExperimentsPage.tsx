import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import React, { useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";

import { CreateRagExperimentModal } from "./rag-experiment-modal";
import { RagExperimentHistorySidebar } from "./RagExperimentHistorySidebar";
import { RagExperimentsHeader } from "./RagExperimentsHeader";
import { RagPanelsProvider, useRagPanels } from "./RagPanelsContext";
import { RagSearchPanel } from "./RagSearchPanel";
import type { SearchMethod, SearchSettings } from "./types";
import { mapApiSettingsToLocal } from "./utils/ragSettingsUtils";

import { ConfirmationModal } from "@/components/common/ConfirmationModal";
import { RagProvidersModal } from "@/components/rag/RagProvidersModal";
import { getContentHeight } from "@/constants/layout";
import { useRagProviders } from "@/hooks/rag/useRagProviders";
import { useLoadRagConfigMutation } from "@/hooks/rag-search-settings/useLoadRagConfig";
import { useCreateRagExperiment } from "@/hooks/useRagExperiments";
import { useAttachNotebookToRagExperimentMutation } from "@/hooks/useRagNotebooks";
import { useTask } from "@/hooks/useTask";
import type { RagProviderCollectionResponse, RagSearchSettingConfigurationResponse, CreateRagExperimentRequest } from "@/lib/api-client/api-client";

const RagExperimentsContent: React.FC = () => {
  const { task } = useTask();
  const { id: taskId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const {
    state,
    updatePanelProvider,
    updatePanelCollection,
    updatePanelMethod,
    updatePanelSettings,
    updatePanelLoadedConfig,
    loadPanelConfig,
    removePanel,
    canRemovePanel,
    notebookId,
    notebook,
    isLoadingNotebook,
    notebookError,
    isDirty,
  } = useRagPanels();

  const [modalOpen, setModalOpen] = useState(false);
  const [experimentModalOpen, setExperimentModalOpen] = useState(false);
  const [historySidebarOpen, setHistorySidebarOpen] = useState(false);
  const [showUnsavedChangesModal, setShowUnsavedChangesModal] = useState(false);
  const pendingNavigationRef = useRef<string | null>(null);

  const navigateWithUnsavedCheck = useCallback(
    (path: string) => {
      if (isDirty) {
        pendingNavigationRef.current = path;
        setShowUnsavedChangesModal(true);
      } else {
        navigate(path);
      }
    },
    [isDirty, navigate]
  );

  const handleConfirmNavigation = useCallback(() => {
    setShowUnsavedChangesModal(false);
    if (pendingNavigationRef.current) {
      navigate(pendingNavigationRef.current);
      pendingNavigationRef.current = null;
    }
  }, [navigate]);

  const handleCancelNavigation = useCallback(() => {
    setShowUnsavedChangesModal(false);
    pendingNavigationRef.current = null;
  }, []);

  const createExperimentMutation = useCreateRagExperiment(task?.id);
  const attachNotebookMutation = useAttachNotebookToRagExperimentMutation();
  const [loadingPanelId, setLoadingPanelId] = useState<string | null>(null);
  const { providers, isLoading: isLoadingProviders, refetch: refetchProviders } = useRagProviders(task?.id);
  const loadConfigMutation = useLoadRagConfigMutation();

  const loadConfigForPanel = useCallback(
    (panelId: string, configId: string, versionNumber?: number) => {
      setLoadingPanelId(panelId);

      loadConfigMutation.mutate(
        { configId, versionNumber },
        {
          onSuccess: (data) => {
            const { config, settings, collection, searchKind } = data;
            const method: SearchMethod =
              searchKind === "hybrid_search" ? "hybrid" : searchKind === "vector_similarity_text_search" ? "nearText" : "bm25";

            loadPanelConfig({
              panelId,
              providerId: config.rag_provider_id || "",
              collection,
              method,
              settings: mapApiSettingsToLocal(settings),
              configId: config.id,
              configName: config.name,
              version: data.versionNumber,
            });
            setLoadingPanelId(null);
          },
          onError: () => {
            setLoadingPanelId(null);
          },
        }
      );
    },
    [loadConfigMutation, loadPanelConfig]
  );

  const handleManageProviders = useCallback(() => {
    setModalOpen(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setModalOpen(false);
    refetchProviders();
  }, [refetchProviders]);

  const handleOpenExperimentModal = useCallback(() => {
    setExperimentModalOpen(true);
  }, []);

  const handleCloseExperimentModal = useCallback(() => {
    setExperimentModalOpen(false);
  }, []);

  const handleCreateExperiment = useCallback(
    async (request: CreateRagExperimentRequest): Promise<{ id: string }> => {
      // Create the experiment
      const experiment = await createExperimentMutation.mutateAsync(request);

      // Attach notebook if we have one
      if (notebookId && experiment.id) {
        await attachNotebookMutation.mutateAsync({
          experimentId: experiment.id,
          notebookId,
        });
      }

      return { id: experiment.id };
    },
    [createExperimentMutation, attachNotebookMutation, notebookId]
  );

  const createPanelHandlers = useCallback(
    (panelId: string) => ({
      onProviderChange: (providerId: string) => updatePanelProvider(panelId, providerId),
      onCollectionChange: (collection: RagProviderCollectionResponse | null) => updatePanelCollection(panelId, collection),
      onMethodChange: (method: SearchMethod) => updatePanelMethod(panelId, method),
      onSettingsChange: (settings: SearchSettings) => updatePanelSettings(panelId, settings),
      onConfigSelect: (config: RagSearchSettingConfigurationResponse | null) => {
        if (config) {
          loadConfigForPanel(panelId, config.id);
        } else {
          updatePanelLoadedConfig(panelId, null, null, null);
        }
      },
      onVersionSelect: (version: number) => {
        const panel = state.panels.find((p) => p.id === panelId);
        if (panel?.loadedConfigId) {
          loadConfigForPanel(panelId, panel.loadedConfigId, version);
        }
      },
      onRemove: () => removePanel(panelId),
      onConfigSaved: (configId: string, configName: string, versionNumber: number) => {
        updatePanelLoadedConfig(panelId, configId, configName, versionNumber);
      },
    }),
    [
      updatePanelProvider,
      updatePanelCollection,
      updatePanelMethod,
      updatePanelSettings,
      updatePanelLoadedConfig,
      removePanel,
      state.panels,
      loadConfigForPanel,
    ]
  );

  if (notebookId && isLoadingNotebook) {
    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          height: getContentHeight(),
          gap: 2,
        }}
      >
        <CircularProgress />
        <Typography variant="body2" color="text.secondary">
          Loading notebook...
        </Typography>
      </Box>
    );
  }

  if (notebookId && !isLoadingNotebook && (notebookError || !notebook)) {
    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          height: getContentHeight(),
          gap: 2,
          p: 4,
        }}
      >
        <ErrorOutlineIcon sx={{ fontSize: 64, color: "text.secondary" }} />
        <Typography variant="h5" sx={{ fontWeight: 600, color: "text.primary" }}>
          Notebook Not Found
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ textAlign: "center", maxWidth: 400 }}>
          The notebook you're looking for doesn't exist or may have been deleted.
        </Typography>
        <Button variant="contained" onClick={() => navigateWithUnsavedCheck(`/tasks/${taskId}/rag`)} sx={{ mt: 2 }}>
          Back to RAG Notebooks
        </Button>
      </Box>
    );
  }

  return (
    <Box
      className="flex flex-col"
      sx={{ height: getContentHeight(), backgroundColor: (theme) => (theme.palette.mode === "dark" ? "background.default" : "#f1f5f9") }}
    >
      <RagExperimentsHeader
        onManageProviders={handleManageProviders}
        onRunExperiment={handleOpenExperimentModal}
        onToggleHistory={() => setHistorySidebarOpen((prev) => !prev)}
        notebookName={notebook?.name}
        notebookId={notebookId}
        notebookDescription={notebook?.description}
        hasNotebook={!!notebookId}
        historyOpen={historySidebarOpen}
      />

      <Box
        sx={{
          flex: 1,
          overflow: "auto",
          p: 2,
        }}
      >
        <Stack
          direction="row"
          spacing={2}
          sx={{
            height: "100%",
            minHeight: 0,
          }}
        >
          {state.panels.map((panel, index) => {
            const handlers = createPanelHandlers(panel.id);
            const isPanelLoadingConfig = loadingPanelId === panel.id && loadConfigMutation.isPending;

            return (
              <Box
                key={panel.id}
                sx={{
                  flex: 1,
                  minWidth: 400,
                  height: "100%",
                }}
              >
                <RagSearchPanel
                  panel={{ ...panel, isLoading: panel.isLoading || isPanelLoadingConfig }}
                  panelIndex={index}
                  providers={providers}
                  isLoadingProviders={isLoadingProviders}
                  canRemove={canRemovePanel}
                  sharedQuery={state.sharedQuery}
                  {...handlers}
                />
              </Box>
            );
          })}
        </Stack>
      </Box>

      {task && <RagProvidersModal open={modalOpen} onClose={handleCloseModal} taskId={task.id} />}

      <CreateRagExperimentModal
        open={experimentModalOpen}
        onClose={handleCloseExperimentModal}
        onSubmit={handleCreateExperiment}
        panels={state.panels}
      />

      <RagExperimentHistorySidebar open={historySidebarOpen} onClose={() => setHistorySidebarOpen(false)} notebookId={notebookId} />

      <ConfirmationModal
        open={showUnsavedChangesModal}
        onClose={handleCancelNavigation}
        onConfirm={handleConfirmNavigation}
        title="Unsaved Changes"
        message="You have unsaved changes. If you leave now, your changes will be lost. Are you sure you want to continue?"
        confirmText="Leave Without Saving"
        cancelText="Stay"
      />
    </Box>
  );
};

interface RagExperimentsPageProps {
  notebookId?: string | null;
}

export const RagExperimentsPage: React.FC<RagExperimentsPageProps> = ({ notebookId: propNotebookId }) => {
  const { task } = useTask();
  const { providers } = useRagProviders(task?.id);
  const { notebookId: urlNotebookId } = useParams<{ notebookId: string }>();
  const notebookId = propNotebookId ?? urlNotebookId ?? null;
  const defaultProviderId = providers.length > 0 ? providers[0].id : undefined;

  return (
    <RagPanelsProvider defaultProviderId={defaultProviderId} notebookId={notebookId}>
      <RagExperimentsContent />
    </RagPanelsProvider>
  );
};
