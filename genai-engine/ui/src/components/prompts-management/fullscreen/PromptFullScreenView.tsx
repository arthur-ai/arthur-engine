import Box from "@mui/material/Box";
import React, { useState, useEffect } from "react";

import { usePrompt } from "../hooks/usePrompt";
import { usePromptVersions } from "../hooks/usePromptVersions";
import { useDeletePromptVersionMutation } from "../hooks/useDeletePromptVersionMutation";
import type { PromptFullScreenViewProps } from "../types";

import PromptDetailView from "./PromptDetailView";
import PromptVersionDrawer from "./PromptVersionDrawer";

import { useTask } from "@/hooks/useTask";

const PromptFullScreenView = ({ promptName, initialVersion, onClose }: PromptFullScreenViewProps) => {
  const { task } = useTask();
  const [selectedVersion, setSelectedVersion] = useState<number | null>(initialVersion ?? null);

  // Fetch versions to get the latest if no version is selected
  const { versions } = usePromptVersions(task?.id, promptName, {
    sort: "desc",
    pageSize: 1,
  });

  const deleteMutation = useDeletePromptVersionMutation(task?.id, promptName);

  useEffect(() => {
    if (selectedVersion === null && versions.length > 0) {
      setSelectedVersion(versions[0].version);
    }
  }, [versions, selectedVersion]);

  const { prompt: promptData, isLoading, error } = usePrompt(task?.id, promptName, selectedVersion !== null ? selectedVersion.toString() : undefined);

  const handleSelectVersion = (version: number) => {
    setSelectedVersion(version);
  };

  return (
    <Box sx={{ display: "flex", height: "100%", position: "relative" }}>
      <PromptVersionDrawer
        open={true}
        onClose={onClose}
        taskId={task?.id ?? ""}
        promptName={promptName}
        selectedVersion={selectedVersion}
        onSelectVersion={handleSelectVersion}
        onDelete={deleteMutation.mutateAsync}
      />
      <Box
        sx={{
          flex: 1,
          height: "100%",
          overflow: "hidden",
          minWidth: 0,
        }}
      >
        <PromptDetailView promptData={promptData} isLoading={isLoading} error={error} promptName={promptName} version={selectedVersion} onClose={onClose} />
      </Box>
    </Box>
  );
};

export default PromptFullScreenView;
