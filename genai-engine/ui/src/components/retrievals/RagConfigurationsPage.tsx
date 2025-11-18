import React from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ConfigurationsListView } from "./ConfigurationsListView";

import { useApi } from "@/hooks/useApi";

export const RagConfigurationsPage: React.FC = () => {
  const navigate = useNavigate();
  const { id: taskId } = useParams<{ id: string }>();
  const api = useApi();

  const handleConfigSelect = (configId: string, versionNumber?: number) => {
    const params = new URLSearchParams();
    params.set("configId", configId);
    if (versionNumber !== undefined) {
      params.set("version", versionNumber.toString());
    }
    navigate(`/tasks/${taskId}/playgrounds/retrievals?${params.toString()}`);
  };

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

  return <ConfigurationsListView onConfigSelect={handleConfigSelect} onConfigDelete={handleConfigDelete} />;
};

