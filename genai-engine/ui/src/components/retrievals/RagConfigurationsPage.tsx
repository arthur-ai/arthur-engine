import React from "react";

import { ConfigurationsListView } from "./ConfigurationsListView";

import { useApi } from "@/hooks/useApi";

export const RagConfigurationsPage: React.FC = () => {
  const api = useApi();

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

  return <ConfigurationsListView onConfigDelete={handleConfigDelete} />;
};
