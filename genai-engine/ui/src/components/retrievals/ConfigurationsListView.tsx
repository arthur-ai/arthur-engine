import { Add } from "@mui/icons-material";
import DeleteIcon from "@mui/icons-material/Delete";
import HistoryIcon from "@mui/icons-material/History";
import SearchIcon from "@mui/icons-material/Search";
import StorageOutlinedIcon from "@mui/icons-material/StorageOutlined";
import { InputAdornment } from "@mui/material";
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
  onConfigClick?: (configId: string) => void;
}

export const ConfigurationsListView: React.FC<ConfigurationsListViewProps> = ({ onConfigDelete, onConfigClick }) => {
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
    <div className="flex-1">
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          gap: 2,
          px: 3,
          pt: 3,
          pb: 2,
          borderBottom: 1,
          borderColor: "divider",
          backgroundColor: "background.paper",
        }}
      >
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Box>
            <Typography variant="h5" fontWeight={600} color="text.primary">
              RAG Configurations
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Manage your RAG provider configurations
            </Typography>
          </Box>
          <Button variant="contained" startIcon={<Add />} onClick={() => setCreateModalOpen(true)} sx={{ whiteSpace: "nowrap" }}>
            Configuration
          </Button>
        </Box>
        <TextField
          placeholder="Search configurations..."
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setPage(0);
          }}
          size="small"
          fullWidth
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            },
          }}
        />
      </Box>

      <Box>
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading configurations...</div>
        ) : configs.length === 0 ? (
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
            <StorageOutlinedIcon sx={{ fontSize: 64, color: "text.secondary", mb: 2 }} />
            <Typography variant="h5" gutterBottom sx={{ fontWeight: 500, color: "text.primary" }}>
              {searchQuery ? "No configurations found" : "No RAG configurations yet"}
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              {searchQuery ? "Try adjusting your search terms" : "Get started by creating your first RAG configuration"}
            </Typography>
            {!searchQuery && (
              <Button variant="contained" color="primary" startIcon={<Add />} onClick={() => setCreateModalOpen(true)} size="large">
                Configuration
              </Button>
            )}
          </Box>
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
                  <TableRow key={config.id} hover onClick={() => onConfigClick?.(config.id)} sx={{ cursor: onConfigClick ? "pointer" : "default" }}>
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
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleViewVersions(config);
                        }}
                        title="View versions"
                      >
                        <HistoryIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          onConfigDelete(config.id);
                        }}
                        title="Delete configuration"
                      >
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
      </Box>

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
