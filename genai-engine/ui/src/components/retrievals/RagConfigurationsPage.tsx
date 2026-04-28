import Box from "@mui/material/Box";
import React, { useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ConfigurationsListView } from "./ConfigurationsListView";
import RagConfigFullScreenView from "./fullscreen/RagConfigFullScreenView";

import { getContentHeight } from "@/constants/layout";
import { useApi } from "@/hooks/useApi";

interface RagConfigurationsPageProps {
  onRegisterCreate?: (fn: () => void) => void;
}

export const RagConfigurationsPage: React.FC<RagConfigurationsPageProps> = ({ onRegisterCreate }) => {
  const api = useApi();
  const {
    id: taskId,
    configId: urlConfigId,
    version: urlVersion,
  } = useParams<{
    id: string;
    configId?: string;
    version?: string;
  }>();
  const navigate = useNavigate();

  const handleConfigClick = useCallback(
    (configId: string) => {
      navigate(`/tasks/${taskId}/rag-configurations/${configId}`);
    },
    [taskId, navigate]
  );

  const handleCloseFullScreen = useCallback(() => {
    navigate(`/tasks/${taskId}/rag?tab=rag-configurations`);
  }, [taskId, navigate]);

  const handleConfigDelete = async (configId: string) => {
    if (!api) return;

    if (window.confirm("Are you sure you want to delete this configuration? This will delete all versions.")) {
      try {
        await api.api.deleteRagSearchSetting(configId);
      } catch (error) {
        console.error("Failed to delete configuration:", error);
        alert(error instanceof Error ? error.message : "Failed to delete configuration");
      }
    }
  };

  if (urlConfigId) {
    const initialVersion = urlVersion ? parseInt(urlVersion, 10) : null;
    return (
      <Box sx={{ height: getContentHeight(), overflow: "hidden" }}>
        <RagConfigFullScreenView configId={urlConfigId} initialVersion={initialVersion} onClose={handleCloseFullScreen} />
      </Box>
    );
  }

  return <ConfigurationsListView onConfigDelete={handleConfigDelete} onConfigClick={handleConfigClick} onRegisterCreate={onRegisterCreate} />;
};
