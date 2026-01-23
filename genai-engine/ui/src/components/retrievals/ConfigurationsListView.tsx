import { Add, Storage } from "@mui/icons-material";
import DeleteIcon from "@mui/icons-material/Delete";
import HistoryIcon from "@mui/icons-material/History";
import { Stack } from "@mui/material";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TablePagination from "@mui/material/TablePagination";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import React, { useState } from "react";

import { ConfigVersionsDrawer } from "./ConfigVersionsDrawer";
import { CreateRagConfigurationModal } from "./CreateRagConfigurationModal";

import { useRagSearchSettings } from "@/hooks/rag-search-settings/useRagSearchSettings";
import { useTask } from "@/hooks/useTask";
import type { RagSearchSettingConfigurationResponse } from "@/lib/api-client/api-client";

interface ConfigurationsListViewProps {
  onConfigDelete: (configId: string) => void;
}

export const ConfigurationsListView: React.FC<ConfigurationsListViewProps> = ({ onConfigDelete }) => {
  const { task } = useTask();
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [versionsDrawerOpen, setVersionsDrawerOpen] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<RagSearchSettingConfigurationResponse | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);

  // Fetch with filters
  const { data, isLoading, refetch } = useRagSearchSettings(task?.id, {
    config_name: searchQuery,
    page,
    page_size: pageSize,
  });

  const configs = data?.rag_provider_setting_configurations ?? [];
  const count = data?.count ?? 0;

  const handleViewVersions = (config: RagSearchSettingConfigurationResponse) => {
    setSelectedConfig(config);
    setVersionsDrawerOpen(true);
  };

  const handleCreateSuccess = () => {
    refetch();
  };

  return (
    <div className="flex-1 px-4 py-4">
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b">
          <div className="flex justify-between items-center mb-3">
            <Box>
              <Typography variant="h5" className="font-semibold mb-1 text-gray-900">
                RAG Configurations
              </Typography>
              <Typography variant="body2" className="text-gray-600">
                Manage and organize your RAG search configurations
              </Typography>
            </Box>
            <Button variant="contained" startIcon={<Add />} onClick={() => setCreateModalOpen(true)} sx={{ whiteSpace: "nowrap" }}>
              Create Configuration
            </Button>
          </div>
          <TextField
            placeholder="Search configurations..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(0); // Reset to first page on search
            }}
            size="small"
            fullWidth
          />
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading configurations...</div>
        ) : configs.length === 0 ? (
          <Stack gap={2} alignItems="center" justifyContent="center" className="py-12 px-8 text-center">
            <Storage sx={{ fontSize: 48, color: "text.disabled" }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              {searchQuery ? "No configurations match your search" : "No RAG Configurations Yet"}
            </Typography>
            <Typography variant="body2" color="text.secondary" className="mb-4 text-center">
              {searchQuery
                ? "Try adjusting your search terms."
                : "RAG configurations define how to search your vector database collections. Create your first configuration to get started."}
            </Typography>
            {!searchQuery && (
              <Button variant="contained" startIcon={<Add />} onClick={() => setCreateModalOpen(true)}>
                Create Configuration
              </Button>
            )}
          </Stack>
        ) : (
          <>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell>Versions</TableCell>
                  <TableCell>Tags</TableCell>
                  <TableCell>Updated</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {configs.map((config) => (
                  <TableRow key={config.id} hover>
                    <TableCell>{config.name}</TableCell>
                    <TableCell>{config.description || "-"}</TableCell>
                    <TableCell>{config.latest_version_number}</TableCell>
                    <TableCell>
                      <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                        {config.all_possible_tags?.map((tag) => (
                          <Chip key={tag} label={tag} size="small" variant="outlined" />
                        ))}
                      </Box>
                    </TableCell>
                    <TableCell>{new Date(config.updated_at).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <IconButton size="small" onClick={() => handleViewVersions(config)} title="View versions">
                        <HistoryIcon />
                      </IconButton>
                      <IconButton size="small" onClick={() => onConfigDelete(config.id)} title="Delete configuration">
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <TablePagination
              component="div"
              count={count}
              page={page}
              onPageChange={(_e, newPage) => setPage(newPage)}
              rowsPerPage={pageSize}
              onRowsPerPageChange={(e) => {
                setPageSize(parseInt(e.target.value));
                setPage(0);
              }}
              rowsPerPageOptions={[10, 25, 50, 100]}
            />
          </>
        )}
      </div>

      {selectedConfig && (
        <ConfigVersionsDrawer
          open={versionsDrawerOpen}
          onClose={() => {
            setVersionsDrawerOpen(false);
            setSelectedConfig(null);
          }}
          config={selectedConfig}
        />
      )}

      {task && (
        <CreateRagConfigurationModal
          open={createModalOpen}
          onClose={() => setCreateModalOpen(false)}
          taskId={task.id}
          onSuccess={handleCreateSuccess}
        />
      )}
    </div>
  );
};
