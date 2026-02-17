import Box from "@mui/material/Box";
import { useState, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";

import RagConfigDetailView from "./RagConfigDetailView";
import RagConfigVersionDrawer from "./RagConfigVersionDrawer";

import { useDeleteRagVersion } from "@/hooks/rag-search-settings/useDeleteRagVersion";
import { useLoadRagConfig } from "@/hooks/rag-search-settings/useLoadRagConfig";

interface RagConfigFullScreenViewProps {
  configId: string;
  initialVersion: number | null;
  onClose: () => void;
}

const RagConfigFullScreenView = ({ configId, initialVersion, onClose }: RagConfigFullScreenViewProps) => {
  const { id: taskId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [selectedVersion, setSelectedVersion] = useState<number | null>(initialVersion);

  const deleteMutation = useDeleteRagVersion();

  // Load the latest version to know the latest version number
  const { data: latestData, refetch: refetchLatest } = useLoadRagConfig(configId);
  const latestVersion = latestData?.config?.latest_version_number ?? null;

  const effectiveVersion = selectedVersion ?? latestVersion;

  // Load the effective version's data
  const { data: versionData, isLoading, error, refetch } = useLoadRagConfig(configId, effectiveVersion ?? undefined);

  const handleSelectVersion = useCallback(
    (version: number) => {
      setSelectedVersion(version);
      navigate(`/tasks/${taskId}/rag-configurations/${configId}/versions/${version}`);
    },
    [taskId, configId, navigate]
  );

  const handleDeleteVersion = useCallback(
    async (version: number) => {
      const wasSelectedVersion = version === effectiveVersion;

      await deleteMutation.mutateAsync({ configId, versionNumber: version });

      if (wasSelectedVersion) {
        // Reset selection so it falls back to the new latest after refetch
        setSelectedVersion(null);
        await refetchLatest();
      }
    },
    [effectiveVersion, configId, deleteMutation, refetchLatest]
  );

  const handleRefetch = useCallback(
    async (newVersion?: number) => {
      await Promise.all([refetch(), refetchLatest()]);

      if (newVersion !== undefined) {
        handleSelectVersion(newVersion);
      }
    },
    [refetch, refetchLatest, handleSelectVersion]
  );

  const configName = versionData?.config?.name ?? latestData?.config?.name ?? "Configuration";

  return (
    <Box sx={{ display: "flex", height: "100%", position: "relative" }}>
      <RagConfigVersionDrawer
        open={true}
        onClose={onClose}
        configId={configId}
        configName={configName}
        selectedVersion={effectiveVersion}
        latestVersion={latestVersion}
        onSelectVersion={handleSelectVersion}
        onDelete={handleDeleteVersion}
      />
      <Box
        sx={{
          flex: 1,
          height: "100%",
          overflow: "hidden",
          minWidth: 0,
        }}
      >
        <RagConfigDetailView
          config={versionData?.config ?? null}
          settings={versionData?.settings ?? null}
          collection={versionData?.collection ?? null}
          versionNumber={effectiveVersion}
          versionTags={versionData?.tags ?? []}
          latestVersion={latestVersion}
          isLoading={isLoading}
          error={error}
          onClose={onClose}
          onRefetch={handleRefetch}
        />
      </Box>
    </Box>
  );
};

export default RagConfigFullScreenView;
