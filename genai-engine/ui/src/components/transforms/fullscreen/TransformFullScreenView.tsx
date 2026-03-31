import Box from "@mui/material/Box";
import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useRestoreTransformVersionMutation } from "../hooks/useRestoreTransformVersionMutation";
import { useTransformVersion } from "../hooks/useTransformVersion";
import { useTransformVersions } from "../hooks/useTransformVersions";
import RestoreTransformVersionDialog from "../RestoreTransformVersionDialog";
import { TraceTransform } from "../types";

import TransformDetailView from "./TransformDetailView";
import TransformVersionDrawer from "./TransformVersionDrawer";

import { useTransform } from "@/hooks/transforms/useTransform";

interface TransformFullScreenViewProps {
  transformId: string;
  initialVersionId?: string | null;
  editKey?: number;
  onClose: () => void;
  onEdit: (transform: TraceTransform) => void;
}

const TransformFullScreenView = ({ transformId, initialVersionId, editKey, onClose, onEdit }: TransformFullScreenViewProps) => {
  const { id: taskId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: transform } = useTransform(transformId);
  const { data: versions = [] } = useTransformVersions(transformId);

  // Determine latest version (highest version_number)
  const latestVersion = versions.length > 0 ? versions.reduce((a, b) => (a.version_number > b.version_number ? a : b)) : null;
  const latestVersionId = latestVersion?.id ?? null;

  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(initialVersionId ?? null);

  // Reset to latest version after a successful edit (skip initial render)
  const isFirstEditKeyRender = useRef(true);
  useEffect(() => {
    if (isFirstEditKeyRender.current) {
      isFirstEditKeyRender.current = false;
      return;
    }
    setSelectedVersionId(null);
    navigate(`/tasks/${taskId}/transforms/${transformId}`);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editKey]);
  const [pendingRestoreVersionId, setPendingRestoreVersionId] = useState<string | null>(null);
  const [pendingRestoreVersionNumber, setPendingRestoreVersionNumber] = useState<number | null>(null);

  // Default to latest version once versions are loaded
  useEffect(() => {
    if (selectedVersionId === null && latestVersionId !== null) {
      setSelectedVersionId(latestVersionId);
    }
  }, [latestVersionId, selectedVersionId]);

  // Fetch selected version data (only when not null)
  const {
    data: versionData = null,
    isLoading: isVersionLoading,
    error: versionError,
  } = useTransformVersion(transformId, selectedVersionId !== latestVersionId ? selectedVersionId : null);

  const restoreMutation = useRestoreTransformVersionMutation(transformId, () => {
    setPendingRestoreVersionId(null);
    setPendingRestoreVersionNumber(null);
    // After restore, navigate to the new latest version (reset selection)
    setSelectedVersionId(null);
    navigate(`/tasks/${taskId}/transforms/${transformId}`);
  });

  const handleSelectVersion = useCallback(
    (versionId: string) => {
      setSelectedVersionId(versionId);
      if (versionId === latestVersionId) {
        navigate(`/tasks/${taskId}/transforms/${transformId}`);
      } else {
        navigate(`/tasks/${taskId}/transforms/${transformId}/versions/${versionId}`);
      }
    },
    [taskId, transformId, latestVersionId, navigate]
  );

  const handleRestoreClick = useCallback((versionId: string, versionNumber: number) => {
    setPendingRestoreVersionId(versionId);
    setPendingRestoreVersionNumber(versionNumber);
  }, []);

  const handleRestoreClose = useCallback(() => {
    if (!restoreMutation.isPending) {
      setPendingRestoreVersionId(null);
      setPendingRestoreVersionNumber(null);
    }
  }, [restoreMutation.isPending]);

  const handleRestoreConfirm = useCallback(() => {
    if (!pendingRestoreVersionId) return;
    restoreMutation.mutate(pendingRestoreVersionId);
  }, [pendingRestoreVersionId, restoreMutation]);

  const handleEdit = useCallback(() => {
    if (transform) onEdit(transform);
  }, [transform, onEdit]);

  const isLatest = selectedVersionId === latestVersionId || selectedVersionId === null;

  // For latest version, we show the transform's own data (no need to fetch version snapshot)
  const displayVersionData = isLatest ? null : (versionData ?? null);

  return (
    <Box sx={{ display: "flex", height: "100%", position: "relative" }}>
      <TransformVersionDrawer
        transformId={transformId}
        transformName={transform?.name ?? ""}
        selectedVersionId={selectedVersionId}
        latestVersionId={latestVersionId}
        onSelectVersion={handleSelectVersion}
        onRestore={handleRestoreClick}
      />
      <Box sx={{ flex: 1, height: "100%", overflow: "hidden", minWidth: 0 }}>
        <TransformDetailView
          transform={transform ?? null}
          versionData={displayVersionData}
          isVersionLoading={!isLatest && isVersionLoading}
          versionError={!isLatest && versionError ? (versionError as Error) : null}
          isLatest={isLatest}
          onClose={onClose}
          onEdit={handleEdit}
          onRestore={handleRestoreClick}
        />
      </Box>

      <RestoreTransformVersionDialog
        open={!!pendingRestoreVersionId}
        versionNumber={pendingRestoreVersionNumber}
        onClose={handleRestoreClose}
        onConfirm={handleRestoreConfirm}
        isRestoring={restoreMutation.isPending}
      />
    </Box>
  );
};

export default TransformFullScreenView;
