import { Close, ExpandLess, ExpandMore, Save, Tune } from "@mui/icons-material";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import React, { useCallback, useEffect, useState } from "react";

import { RagConfigurationSelector } from "./RagConfigurationSelector";
import { RagConfigVersionSelector } from "./RagConfigVersionSelector";
import type { RagPanel } from "./ragPanelsReducer";
import { ResultsDisplay } from "./ResultsDisplay";
import { SaveRagConfigDialog } from "./SaveRagConfigDialog";
import { SearchSettings } from "./SearchSettings";
import type { SearchMethod, SearchSettings as SearchSettingsType } from "./types";

import { useRagCollections } from "@/hooks/rag/useRagCollections";
import { useTask } from "@/hooks/useTask";
import type {
  RagProviderCollectionResponse,
  RagProviderConfigurationResponse,
  RagSearchSettingConfigurationResponse,
} from "@/lib/api-client/api-client";

interface RagSearchPanelProps {
  panel: RagPanel;
  panelIndex: number;
  providers: RagProviderConfigurationResponse[];
  isLoadingProviders: boolean;
  canRemove: boolean;
  onProviderChange: (providerId: string) => void;
  onCollectionChange: (collection: RagProviderCollectionResponse | null) => void;
  onMethodChange: (method: SearchMethod) => void;
  onSettingsChange: (settings: SearchSettingsType) => void;
  onConfigSelect: (config: RagSearchSettingConfigurationResponse | null) => void;
  onVersionSelect: (version: number) => void;
  onRemove: () => void;
  sharedQuery: string;
  onConfigSaved?: (configId: string, configName: string, versionNumber: number) => void;
}

export const RagSearchPanel: React.FC<RagSearchPanelProps> = ({
  panel,
  panelIndex,
  providers,
  isLoadingProviders,
  canRemove,
  onProviderChange,
  onCollectionChange,
  onMethodChange,
  onSettingsChange,
  onConfigSelect,
  onVersionSelect,
  onRemove,
  sharedQuery,
  onConfigSaved,
}) => {
  const { task } = useTask();

  // Config expansion state - starts expanded if no results
  const [configExpanded, setConfigExpanded] = useState(!panel.results);
  const [settingsExpanded, setSettingsExpanded] = useState(true);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);

  // Auto-collapse config when results arrive
  useEffect(() => {
    if (panel.results && panel.results.objects.length > 0) {
      setConfigExpanded(false);
    }
  }, [panel.results]);

  // Fetch collections for this panel's provider
  const { collections, isLoading: isLoadingCollections } = useRagCollections(panel.providerId || undefined);

  useEffect(() => {
    if (!panel.providerId || isLoadingCollections || collections.length === 0) return;

    const currentCollectionValid = panel.collection && collections.some((c) => c.identifier === panel.collection?.identifier);
    if (!currentCollectionValid) {
      onCollectionChange(collections[0]);
    }
  }, [panel.providerId, collections, isLoadingCollections, panel.collection, onCollectionChange]);

  const handleProviderChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      onProviderChange(e.target.value);
    },
    [onProviderChange]
  );

  const handleCollectionChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const collection = collections.find((c) => c.identifier === e.target.value);
      onCollectionChange(collection || null);
    },
    [collections, onCollectionChange]
  );

  const handleMethodChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      onMethodChange(e.target.value as SearchMethod);
    },
    [onMethodChange]
  );

  const isExecuting = panel.isLoading;
  const isReady = Boolean(panel.providerId && panel.collection);

  return (
    <Paper
      elevation={2}
      className="h-full flex flex-col overflow-hidden"
      sx={{
        backgroundColor: "background.default",
        borderRadius: 2,
      }}
    >
      <Box
        sx={{
          px: 2,
          py: 1,
          borderBottom: 1,
          borderColor: "divider",
          backgroundColor: "background.paper",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Tooltip title={isReady ? "Ready to run" : "Not configured"}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                backgroundColor: isReady ? "success.main" : "text.disabled",
                flexShrink: 0,
              }}
            />
          </Tooltip>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, color: "text.primary" }}>
            Panel {panelIndex + 1}
          </Typography>
          {panel.loadedConfigName && (
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              — {panel.loadedConfigName} v{panel.loadedVersion}
            </Typography>
          )}
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          <Tooltip title="Save configuration">
            <span>
              <IconButton
                size="small"
                onClick={() => setSaveDialogOpen(true)}
                disabled={!panel.providerId || !panel.collection}
                sx={{ color: "text.secondary" }}
              >
                <Save fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip title={configExpanded ? "Hide configuration" : "Show configuration"}>
            <IconButton
              size="small"
              onClick={() => setConfigExpanded(!configExpanded)}
              sx={{ color: configExpanded ? "primary.main" : "text.secondary" }}
            >
              <Tune fontSize="small" />
            </IconButton>
          </Tooltip>
          {canRemove && (
            <IconButton size="small" onClick={onRemove} title="Remove panel" sx={{ color: "text.secondary" }}>
              <Close fontSize="small" />
            </IconButton>
          )}
        </Box>
      </Box>

      <Box sx={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column" }}>
        <Collapse in={configExpanded}>
          <Box sx={{ p: 2, backgroundColor: "background.paper", borderBottom: 1, borderColor: "divider" }}>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
              <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                <Box sx={{ flex: 1 }}>
                  <RagConfigurationSelector currentConfigId={panel.loadedConfigId} onConfigSelect={onConfigSelect} />
                </Box>
                <Box sx={{ flex: 1 }}>
                  <RagConfigVersionSelector configId={panel.loadedConfigId} currentVersion={panel.loadedVersion} onVersionSelect={onVersionSelect} />
                </Box>
              </Box>

              <Box sx={{ display: "flex", gap: 1 }}>
                <Box sx={{ flex: 1 }}>
                  <label htmlFor={`provider-${panel.id}`} className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Provider
                  </label>
                  {isLoadingProviders ? (
                    <Box sx={{ px: 1, py: 0.75, border: 1, borderColor: "divider", borderRadius: 1, fontSize: "0.875rem", color: "text.secondary" }}>
                      Loading...
                    </Box>
                  ) : (
                    <select
                      id={`provider-${panel.id}`}
                      value={panel.providerId}
                      onChange={handleProviderChange}
                      className="w-full px-2 py-1.5 border border-gray-300 dark:border-gray-600 rounded text-sm text-gray-900 dark:text-gray-100 dark:bg-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      disabled={isExecuting || providers.length === 0}
                    >
                      <option value="">{providers.length === 0 ? "No providers" : "Select provider"}</option>
                      {providers.map((provider) => (
                        <option key={provider.id} value={provider.id}>
                          {provider.name}
                        </option>
                      ))}
                    </select>
                  )}
                </Box>

                {panel.providerId && (
                  <Box sx={{ flex: 1 }}>
                    <label htmlFor={`collection-${panel.id}`} className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Collection
                    </label>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <select
                        id={`collection-${panel.id}`}
                        value={panel.collection?.identifier || ""}
                        onChange={handleCollectionChange}
                        className="flex-1 px-2 py-1.5 border border-gray-300 dark:border-gray-600 rounded text-sm text-gray-900 dark:text-gray-100 dark:bg-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        disabled={isExecuting || isLoadingCollections}
                      >
                        {isLoadingCollections ? (
                          <option value="">Loading...</option>
                        ) : collections.length === 0 ? (
                          <option value="">No collections</option>
                        ) : (
                          collections.map((collection) => (
                            <option key={collection.identifier} value={collection.identifier}>
                              {collection.identifier}
                            </option>
                          ))
                        )}
                      </select>
                      {isLoadingCollections && <CircularProgress size={16} />}
                    </Box>
                  </Box>
                )}
              </Box>

              {panel.providerId && (
                <Box>
                  <label htmlFor={`method-${panel.id}`} className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Search Method
                  </label>
                  <select
                    id={`method-${panel.id}`}
                    value={panel.method}
                    onChange={handleMethodChange}
                    className="w-full px-2 py-1.5 border border-gray-300 dark:border-gray-600 rounded text-sm text-gray-900 dark:text-gray-100 dark:bg-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    disabled={isExecuting}
                  >
                    <option value="nearText">Near Text (Vector)</option>
                    <option value="bm25">BM25 (Keyword)</option>
                    <option value="hybrid">Hybrid</option>
                  </select>
                </Box>
              )}

              {panel.providerId && (
                <Box>
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      cursor: "pointer",
                      py: 0.5,
                    }}
                    onClick={() => setSettingsExpanded(!settingsExpanded)}
                  >
                    <Typography variant="caption" sx={{ fontWeight: 600, color: "text.secondary" }}>
                      SEARCH SETTINGS
                    </Typography>
                    {settingsExpanded ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}
                  </Box>
                  <Collapse in={settingsExpanded}>
                    <Box sx={{ pt: 1 }}>
                      <SearchSettings
                        searchMethod={panel.method}
                        settings={panel.settings}
                        onSettingsChange={onSettingsChange}
                        isExecuting={isExecuting}
                      />
                    </Box>
                  </Collapse>
                </Box>
              )}
            </Box>
          </Box>
        </Collapse>

        {!configExpanded && panel.providerId && (
          <Box
            sx={{
              px: 2,
              py: 1,
              backgroundColor: "background.paper",
              borderBottom: 1,
              borderColor: "divider",
              display: "flex",
              alignItems: "center",
              gap: 1,
              flexWrap: "wrap",
            }}
          >
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              {providers.find((p) => p.id === panel.providerId)?.name || "Provider"}
            </Typography>
            <Typography variant="caption" sx={{ color: "text.disabled" }}>
              •
            </Typography>
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              {panel.collection?.identifier || "Collection"}
            </Typography>
            <Typography variant="caption" sx={{ color: "text.disabled" }}>
              •
            </Typography>
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              {panel.method === "nearText" ? "Vector" : panel.method === "bm25" ? "Keyword" : "Hybrid"}
            </Typography>
          </Box>
        )}

        <Box sx={{ flex: 1, p: 2, minHeight: 0, overflow: "auto" }}>
          {panel.isLoading ? (
            <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", py: 4 }}>
              <CircularProgress size={32} />
            </Box>
          ) : (
            <ResultsDisplay results={panel.results} isLoading={panel.isLoading} error={panel.error} query={sharedQuery} searchMethod={panel.method} />
          )}
        </Box>
      </Box>

      {panel.collection && panel.providerId && task && (
        <SaveRagConfigDialog
          open={saveDialogOpen}
          setOpen={setSaveDialogOpen}
          currentConfigName={panel.loadedConfigName}
          currentProviderId={panel.providerId}
          selectedCollection={panel.collection}
          searchMethod={panel.method}
          settings={panel.settings}
          taskId={task.id}
          onSaveSuccess={(configId, configName, versionNumber) => {
            if (onConfigSaved) {
              onConfigSaved(configId, configName, versionNumber);
            }
          }}
        />
      )}
    </Paper>
  );
};
