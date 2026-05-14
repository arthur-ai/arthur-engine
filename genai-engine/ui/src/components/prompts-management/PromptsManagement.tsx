import AddIcon from "@mui/icons-material/Add";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import TablePagination from "@mui/material/TablePagination";
import Typography from "@mui/material/Typography";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

import PromptFullScreenView from "./fullscreen/PromptFullScreenView";
import { useDeletePromptMutation } from "./hooks/useDeletePromptMutation";
import { usePrompts } from "./hooks/usePrompts";
import PromptsManagementHeader from "./PromptsManagementHeader";
import PromptsTable from "./table/PromptsTable";
import TagFilterControls from "./table/TagFilterControls";

import { DATA_TOUR } from "@/components/onboarding/data-tour";
import { useCompleteStep } from "@/components/onboarding/hooks/useCompleteStep";
import { useStepAction } from "@/components/onboarding/hooks/useStepAction";
import { STEP_IDS } from "@/components/onboarding/steps";
import { getContentHeight } from "@/constants/layout";
import { useTask } from "@/hooks/useTask";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

interface PromptsManagementProps {
  onRegisterCreate?: (fn: () => void) => void;
}

const PromptsManagement: React.FC<PromptsManagementProps> = ({ onRegisterCreate }) => {
  const { task } = useTask();
  const { id: taskId, promptName: urlPromptName, version: urlVersion } = useParams<{ id: string; promptName?: string; version?: string }>();
  const navigate = useNavigate();
  const [fullScreenPrompt, setFullScreenPrompt] = useState<string | null>(null);
  const [sortColumn, setSortColumn] = useState<string | null>("latest_version_created_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  // Reset tag filters when navigating to a different task
  useEffect(() => {
    setSelectedTags([]);
  }, [task?.id]);

  // Sync fullScreenPrompt with URL parameter (one-way: URL -> state only)
  useEffect(() => {
    if (urlPromptName) {
      setFullScreenPrompt(urlPromptName);
    } else if (!urlPromptName && fullScreenPrompt) {
      setFullScreenPrompt(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlPromptName]);

  const filters = useMemo(
    () => ({
      page,
      pageSize,
      sort: sortDirection,
      tags: selectedTags.length > 0 ? selectedTags : null,
    }),
    [page, pageSize, sortDirection, selectedTags]
  );

  const { prompts, count, error, isLoading, refetch } = usePrompts(task?.id, filters);

  // Separate query with no tag filter to collect all available tags for the filter chips.
  // Uses a large page_size so tags from all prompts are discoverable regardless of pagination.
  const { prompts: allPromptsForTags } = usePrompts(task?.id, { pageSize: 5000, page: 0 });

  const { availableProductionTag, availableCustomTags } = useMemo(() => {
    const allTags = new Set<string>();
    allPromptsForTags.forEach((p) => (p.tags ?? []).forEach((t) => allTags.add(t)));
    const hasProduction = allTags.has("production");
    const customTags = Array.from(allTags)
      .filter((t) => t !== "production")
      .sort();
    return { availableProductionTag: hasProduction, availableCustomTags: customTags };
  }, [allPromptsForTags]);

  const handleTagToggle = useCallback((tag: string) => {
    setSelectedTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]));
    setPage(0);
  }, []);

  const handleClearTagFilters = useCallback(() => {
    setSelectedTags([]);
  }, []);

  const deleteMutation = useDeletePromptMutation(task?.id, () => {
    refetch();
  });

  const handleCreatePrompt = useCallback(() => {
    // Navigate to prompts playground
    window.location.href = `/tasks/${task?.id}/playgrounds/prompts`;
  }, [task?.id]);

  const onRegisterCreateRef = useRef(onRegisterCreate);
  useEffect(() => {
    onRegisterCreateRef.current?.(handleCreatePrompt);
  }, [handleCreatePrompt]);

  const completeEditPromptStep = useCompleteStep(STEP_IDS.EDIT_PROMPT);

  const handleExpandToFullScreen = useCallback(
    (promptName: string) => {
      setFullScreenPrompt(promptName);
      // Update URL to reflect the selected prompt
      navigate(`/tasks/${taskId}/prompts/${encodeURIComponent(promptName)}`);
      completeEditPromptStep();
    },
    [taskId, navigate, completeEditPromptStep]
  );

  useStepAction(STEP_IDS.EDIT_PROMPT, () => {
    if (prompts.length > 0) {
      handleExpandToFullScreen(prompts[0].name);
    }
  });

  const handleCloseFullScreen = useCallback(() => {
    setFullScreenPrompt(null);
    // Update URL to go back to the main prompts management view
    navigate(`/tasks/${taskId}/prompts-management`);
  }, [taskId, navigate]);

  const handleSort = useCallback(
    (column: string) => {
      if (sortColumn === column) {
        setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
      } else {
        setSortColumn(column);
        setSortDirection("desc");
      }
    },
    [sortColumn]
  );

  const handlePageChange = useCallback((_event: unknown, newPage: number) => {
    setPage(newPage);
  }, []);

  const handlePageSizeChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setPageSize(parseInt(event.target.value, 10));
    setPage(0);
  }, []);

  if (fullScreenPrompt) {
    const initialVersion = urlVersion ? parseInt(urlVersion, 10) : null;
    return (
      <Box sx={{ height: "100%", overflow: "hidden" }}>
        <PromptFullScreenView promptName={fullScreenPrompt} initialVersion={initialVersion} onClose={handleCloseFullScreen} />
      </Box>
    );
  }

  if (isLoading && prompts.length === 0) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: getContentHeight(),
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error && prompts.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" onClose={() => refetch()}>
          {error.message || "Failed to load prompts"}
        </Alert>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        width: "100%",
        height: getContentHeight(),
        display: "grid",
        gridTemplateRows: "auto auto 1fr",
        overflow: "hidden",
      }}
    >
      <Box>
        {!onRegisterCreate && <PromptsManagementHeader onCreatePrompt={handleCreatePrompt} />}
        <TagFilterControls
          availableProductionTag={availableProductionTag}
          availableCustomTags={availableCustomTags}
          selectedTags={selectedTags}
          onTagToggle={handleTagToggle}
          onClearAll={handleClearTagFilters}
        />
      </Box>

      {error && prompts.length > 0 && (
        <Box sx={{ px: 3, pt: 2 }}>
          <Alert severity="error">{error?.message || "An error occurred"}</Alert>
        </Box>
      )}

      <Box
        sx={{
          overflow: "auto",
          minHeight: 0,
        }}
      >
        {!isLoading && prompts.length === 0 ? (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              textAlign: "center",
              py: 8,
            }}
          >
            <DescriptionOutlinedIcon sx={{ fontSize: 64, color: "text.secondary", mb: 2 }} />
            <Typography variant="h5" gutterBottom sx={{ fontWeight: 500, color: "text.primary" }}>
              No prompts yet
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              Get started by creating your first prompt
            </Typography>
            <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={handleCreatePrompt} size="large">
              Prompt
            </Button>
          </Box>
        ) : (
          <Box data-tour={DATA_TOUR.PROMPTS_TABLE}>
            <PromptsTable
              prompts={prompts}
              sortColumn={sortColumn}
              sortDirection={sortDirection}
              onSort={handleSort}
              onExpandToFullScreen={handleExpandToFullScreen}
              onDelete={deleteMutation.mutateAsync}
            />
          </Box>
        )}
      </Box>

      {prompts.length > 0 && (
        <Box
          sx={{
            borderTop: 1,
            borderColor: "divider",
            backgroundColor: "background.paper",
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          <TablePagination
            component="div"
            count={count}
            page={page}
            onPageChange={handlePageChange}
            rowsPerPage={pageSize}
            onRowsPerPageChange={handlePageSizeChange}
            rowsPerPageOptions={PAGE_SIZE_OPTIONS}
          />
        </Box>
      )}
    </Box>
  );
};

export default PromptsManagement;
