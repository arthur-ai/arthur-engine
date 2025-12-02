import DeleteIcon from "@mui/icons-material/Delete";
import HistoryIcon from "@mui/icons-material/History";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TablePagination from "@mui/material/TablePagination";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import React, { useState } from "react";

import { ConfigVersionsDrawer } from "./ConfigVersionsDrawer";

import { useRagSearchSettings } from "@/hooks/rag-search-settings/useRagSearchSettings";
import { useTask } from "@/hooks/useTask";
import type { RagSearchSettingConfigurationResponse } from "@/lib/api-client/api-client";

interface ConfigurationsListViewProps {
  onConfigSelect: (configId: string, versionNumber?: number) => void;
  onConfigDelete: (configId: string) => void;
}

export const ConfigurationsListView: React.FC<ConfigurationsListViewProps> = ({ onConfigSelect, onConfigDelete }) => {
  const { task } = useTask();
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [versionsDrawerOpen, setVersionsDrawerOpen] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<RagSearchSettingConfigurationResponse | null>(null);

  // Fetch with filters
  const { data, isLoading } = useRagSearchSettings(task?.id, {
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

  const handleVersionLoad = (versionNumber: number) => {
    if (selectedConfig) {
      onConfigSelect(selectedConfig.id, versionNumber);
    }
  };

  return (
    <div className="flex-1 px-4 py-4">
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b">
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
          <div className="p-8 text-center text-gray-500">
            {searchQuery ? "No configurations match your search." : "No saved configurations yet. Create one from the Retrievals Playground."}
          </div>
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
                  <TableRow key={config.id} hover onClick={() => onConfigSelect(config.id)} sx={{ cursor: "pointer" }}>
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
      </div>

      {selectedConfig && (
        <ConfigVersionsDrawer
          open={versionsDrawerOpen}
          onClose={() => {
            setVersionsDrawerOpen(false);
            setSelectedConfig(null);
          }}
          config={selectedConfig}
          onVersionLoad={handleVersionLoad}
        />
      )}
    </div>
  );
};
