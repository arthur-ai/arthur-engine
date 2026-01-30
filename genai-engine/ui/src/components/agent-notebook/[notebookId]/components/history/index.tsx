import { Accordion } from "@base-ui/react/accordion";
import HistoryIcon from "@mui/icons-material/History";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { Box, Drawer, List, ListItemText, Skeleton, Stack, Typography, ListItemButton, LinearProgress, Button, TablePagination } from "@mui/material";
import { Suspense } from "react";
import { Link } from "react-router-dom";

import { useShowState } from "../../hooks/useShowState";
import { useSuspensePollAgenticNotebookHistory } from "../../hooks/useSuspensePollAgenticNotebookHistory";

import { StatusBadge } from "@/components/agent-experiments/components/status-badge";
import { formatRelativeTime } from "@/components/live-evals/[evalId]/utils";
import { usePagination } from "@/hooks/usePagination";
import { useTask } from "@/hooks/useTask";
import { useTrackOnMount } from "@/hooks/useTrackOnMount";
import { AgenticExperimentSummary } from "@/lib/api-client/api-client";
import { EVENT_NAMES } from "@/services/amplitude";

const DRAWER_WIDTH = 400;

type Props = {
  notebookId: string;
};

export const History = ({ notebookId }: Props) => {
  const [{ show }, setShow] = useShowState();

  return (
    <Drawer
      anchor="right"
      open={show === "history"}
      onClose={() => setShow(null)}
      slotProps={{
        paper: {
          sx: {
            width: DRAWER_WIDTH,
            overflow: "hidden",
            height: "100%",
          },
        },
      }}
    >
      <Stack p={2} sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Stack direction="row" alignItems="center" gap={1}>
          <HistoryIcon color="primary" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Experiment History
          </Typography>
        </Stack>
      </Stack>
      <Suspense fallback={<Skeleton variant="rectangular" height={100} sx={{ m: 2 }} />}>
        <HistoryContent notebookId={notebookId} />
      </Suspense>
    </Drawer>
  );
};

const HistoryContent = ({ notebookId }: { notebookId: string }) => {
  const [{ id }, setShow] = useShowState();
  const { page, rowsPerPage, handlePageChange, handleRowsPerPageChange } = usePagination(10);

  const { data } = useSuspensePollAgenticNotebookHistory(notebookId, { page, page_size: rowsPerPage });

  useTrackOnMount({ eventName: EVENT_NAMES.AGENT_NOTEBOOK_HISTORY_VIEW, eventProperties: { notebook_id: notebookId } });

  return (
    <>
      <div className="flex-1 overflow-y-auto">
        {data.data.length === 0 ? (
          <Stack alignItems="center" justifyContent="center" className="h-full p-6 text-center">
            <Typography variant="body2" color="text.secondary">
              No experiments yet
            </Typography>
            <Typography variant="caption" color="text.secondary" className="mt-1">
              Run your first experiment to see it here
            </Typography>
          </Stack>
        ) : (
          <Accordion.Root render={<List disablePadding />} value={[id]}>
            {data.data.map((item) => (
              <HistoryItem key={item.id} item={item} onOpenChange={(open) => setShow({ id: open ? item.id : "" })} />
            ))}
          </Accordion.Root>
        )}
      </div>

      {data.total_count > 0 && (
        <TablePagination
          component="div"
          count={data.total_count}
          page={page}
          onPageChange={handlePageChange}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={handleRowsPerPageChange}
          rowsPerPageOptions={[5, 10, 25, 50]}
          sx={{ borderTop: 1, borderColor: "divider" }}
        />
      )}
    </>
  );
};

const HistoryItem = ({ item, onOpenChange }: { item: AgenticExperimentSummary; onOpenChange: (open: boolean) => void }) => {
  const { task } = useTask();
  const isRunning = item.status === "running" || item.status === "queued";
  const progress = item.total_rows > 0 ? Math.round((item.completed_rows / item.total_rows) * 100) : 0;

  return (
    <Accordion.Item key={item.id} value={item.id} onOpenChange={onOpenChange} className="border-b border-gray-200">
      <Accordion.Header>
        <Accordion.Trigger render={<ListItemButton className="px-0" />}>
          <ListItemText
            primary={
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 500, flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>
                  {item.name}
                </Typography>
                <StatusBadge status={item.status} />
              </Box>
            }
            secondary={
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.5 }}>
                <Typography variant="caption" color="text.secondary">
                  {formatRelativeTime(item.created_at)}
                </Typography>
              </Box>
            }
          />
        </Accordion.Trigger>
      </Accordion.Header>
      <Accordion.Panel render={<Stack direction="column" gap={1} p={2} className="bg-gray-100 border-t border-gray-200" />}>
        {isRunning && (
          <Box mb={2}>
            <Stack mb={0.5}>
              <Typography variant="caption" color="text.secondary">
                Progress
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {item.completed_rows} / {item.total_rows} rows
              </Typography>
            </Stack>
            <LinearProgress variant="determinate" value={progress} sx={{ height: 6, borderRadius: 3 }} />
          </Box>
        )}
        <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, mb: 2 }}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Dataset
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              {item.dataset_name} v{item.dataset_version}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Total Rows
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              {item.total_rows}
            </Typography>
          </Box>
          {item.total_cost && (
            <Box>
              <Typography variant="caption" color="text.secondary">
                Total Cost
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                ${item.total_cost}
              </Typography>
            </Box>
          )}
        </Box>
        <Button
          component={Link}
          to={`/tasks/${task!.id}/agent-experiments/${item.id}`}
          variant="outlined"
          color="primary"
          startIcon={<OpenInNewIcon />}
          target="_blank"
        >
          View Details
        </Button>
      </Accordion.Panel>
    </Accordion.Item>
  );
};
