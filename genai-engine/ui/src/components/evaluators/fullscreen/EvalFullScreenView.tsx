import Box from "@mui/material/Box";
import React, { useState, useEffect } from "react";

import { useEval } from "../hooks/useEval";
import { useEvalVersions } from "../hooks/useEvalVersions";
import type { EvalFullScreenViewProps } from "../types";

import EvalDetailView from "./EvalDetailView";
import EvalVersionDrawer from "./EvalVersionDrawer";

import { useTask } from "@/hooks/useTask";

const EvalFullScreenView = ({ evalName, initialVersion, onClose }: EvalFullScreenViewProps) => {
  const { task } = useTask();
  const [selectedVersion, setSelectedVersion] = useState<number | null>(initialVersion ?? null);

  // Fetch versions to get the latest if no version is selected
  const { versions } = useEvalVersions(task?.id, evalName, {
    sort: "desc",
    pageSize: 1,
  });

  useEffect(() => {
    if (selectedVersion === null && versions.length > 0) {
      setSelectedVersion(versions[0].version);
    }
  }, [versions, selectedVersion]);

  const { eval: evalData, isLoading, error } = useEval(task?.id, evalName, selectedVersion !== null ? selectedVersion.toString() : undefined);

  const handleSelectVersion = (version: number) => {
    setSelectedVersion(version);
  };

  return (
    <Box sx={{ display: "flex", height: "100%", position: "relative" }}>
      <EvalVersionDrawer
        open={true}
        onClose={onClose}
        taskId={task?.id ?? ""}
        evalName={evalName}
        selectedVersion={selectedVersion}
        onSelectVersion={handleSelectVersion}
      />
      <Box
        sx={{
          flex: 1,
          height: "100%",
          overflow: "hidden",
          minWidth: 0,
        }}
      >
        <EvalDetailView eval={evalData} isLoading={isLoading} error={error} evalName={evalName} version={selectedVersion} onClose={onClose} />
      </Box>
    </Box>
  );
};

export default EvalFullScreenView;
