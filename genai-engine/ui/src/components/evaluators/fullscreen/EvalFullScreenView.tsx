import Box from "@mui/material/Box";
import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useDeleteEvalVersionMutation } from "../hooks/useDeleteEvalVersionMutation";
import { useEval } from "../hooks/useEval";
import type { EvalFullScreenViewProps } from "../types";

import EvalDetailView from "./EvalDetailView";
import EvalVersionDrawer from "./EvalVersionDrawer";

import { useTask } from "@/hooks/useTask";

const EvalFullScreenView = ({ evalName, initialVersion, onClose }: EvalFullScreenViewProps) => {
  const { task } = useTask();
  const { id: taskId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [selectedVersion, setSelectedVersion] = useState<number | null>(initialVersion ?? null);

  // Fetch the latest non-deleted version from the backend by passing "latest" as the version
  const { eval: latestEval, refetch: refetchLatest } = useEval(task?.id, evalName, "latest");
  const latestVersion = latestEval?.version ?? null;

  const deleteMutation = useDeleteEvalVersionMutation(task?.id, evalName);

  // When no version is selected initially, use the latest non-deleted version
  useEffect(() => {
    if (selectedVersion === null && latestVersion !== null) {
      setSelectedVersion(latestVersion);
    }
  }, [latestVersion, selectedVersion]);

  const {
    eval: evalData,
    isLoading,
    error,
    refetch,
  } = useEval(task?.id, evalName, selectedVersion !== null ? selectedVersion.toString() : undefined);

  const handleSelectVersion = (version: number) => {
    setSelectedVersion(version);
    // Update URL to reflect the selected version
    navigate(`/tasks/${taskId}/evaluators/${evalName}/versions/${version}`);
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
      <EvalVersionDrawer
        open={true}
        onClose={onClose}
        taskId={task?.id ?? ""}
        evalName={evalName}
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
        <EvalDetailView
          evalData={evalData}
          isLoading={isLoading}
          error={error}
          evalName={evalName}
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

export default EvalFullScreenView;
