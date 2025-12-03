import Box from "@mui/material/Box";
import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useDeletePromptVersionMutation } from "../hooks/useDeletePromptVersionMutation";
import { usePrompt } from "../hooks/usePrompt";
import type { PromptFullScreenViewProps } from "../types";

import PromptDetailView from "./PromptDetailView";
import PromptVersionDrawer from "./PromptVersionDrawer";

import { useTask } from "@/hooks/useTask";

const PromptFullScreenView = ({ promptName, initialVersion, onClose }: PromptFullScreenViewProps) => {
  const { task } = useTask();
  const { id: taskId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [selectedVersion, setSelectedVersion] = useState<number | null>(initialVersion ?? null);

  // Fetch the latest non-deleted version from the backend by passing "latest" as the version
  const { prompt: latestPrompt, refetch: refetchLatest } = usePrompt(task?.id, promptName, "latest");
  const latestVersion = latestPrompt?.version ?? null;

  const deleteMutation = useDeletePromptVersionMutation(task?.id, promptName);

  // When no version is selected initially, use the latest non-deleted version
  useEffect(() => {
    if (selectedVersion === null && latestVersion !== null) {
      setSelectedVersion(latestVersion);
    }
  }, [latestVersion, selectedVersion]);

  const {
    prompt: promptData,
    isLoading,
    error,
    refetch,
  } = usePrompt(task?.id, promptName, selectedVersion !== null ? selectedVersion.toString() : undefined);

  const handleSelectVersion = (version: number) => {
    setSelectedVersion(version);
    // Update URL to reflect the selected version
    navigate(`/tasks/${taskId}/prompts/${promptName}/versions/${version}`);
  };

  const handleDeleteVersion = async (version: number) => {
    const wasSelectedVersion = version === selectedVersion;

    // Delete the version
    await deleteMutation.mutateAsync(version);

    // If we just deleted the currently selected version, navigate to the new latest version
    if (wasSelectedVersion) {
      // Refetch the latest version to get the updated latest after deletion
      const refetchResult = await refetchLatest();
      const newLatestVersion = refetchResult.data?.version;

      if (newLatestVersion && newLatestVersion !== version) {
        handleSelectVersion(newLatestVersion);
      }
    }
  };

  return (
    <Box sx={{ display: "flex", height: "100%", position: "relative" }}>
      <PromptVersionDrawer
        open={true}
        onClose={onClose}
        taskId={task?.id ?? ""}
        promptName={promptName}
        selectedVersion={selectedVersion}
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
        <PromptDetailView
          promptData={promptData}
          isLoading={isLoading}
          error={error}
          promptName={promptName}
          version={selectedVersion}
          latestVersion={latestVersion}
          taskId={task?.id ?? ""}
          onClose={onClose}
          onRefetch={refetch}
        />
      </Box>
    </Box>
  );
};

export default PromptFullScreenView;
