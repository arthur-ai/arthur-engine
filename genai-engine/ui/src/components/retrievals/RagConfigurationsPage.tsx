import { createSerializer, parseAsInteger, parseAsString } from "nuqs";
import React from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { ConfigurationsListView } from "./ConfigurationsListView";

import { useApi } from "@/hooks/useApi";

const configSerializer = createSerializer({
  configId: parseAsString,
  version: parseAsInteger,
});

export const RagConfigurationsPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { id: taskId } = useParams<{ id: string }>();
  const api = useApi();

  const handleConfigSelect = (configId: string, versionNumber?: number) => {
    const params = configSerializer({
      configId,
      version: versionNumber ?? null,
    });

    navigate({
      pathname: `/tasks/${taskId}/playgrounds/retrievals`,
      search: params,
      hash: location.hash,
    });
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
