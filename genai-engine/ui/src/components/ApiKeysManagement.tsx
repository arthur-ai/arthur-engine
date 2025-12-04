import { Delete, Warning, VpnKey, Add, Error } from "@mui/icons-material";
import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Alert,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  FormHelperText,
} from "@mui/material";
import React, { useState, useEffect } from "react";

import { useApi } from "@/hooks/useApi";
import { ApiKeyResponse, APIKeysRolesEnum } from "@/lib/api-client/api-client";

export const ApiKeysManagement: React.FC = () => {
  const api = useApi();
  const [apiKeys, setApiKeys] = useState<ApiKeyResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [permissionError, setPermissionError] = useState(false);

  const [deleteModal, setDeleteModal] = useState<{
    isOpen: boolean;
    apiKey: ApiKeyResponse | null;
  }>({ isOpen: false, apiKey: null });
  const [isDeleting, setIsDeleting] = useState(false);

  const [createModal, setCreateModal] = useState(false);
  const [selectedRole, setSelectedRole] = useState<APIKeysRolesEnum>("VALIDATION-USER");
  const [description, setDescription] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [showCreatedKeyModal, setShowCreatedKeyModal] = useState(false);
  const [copied, setCopied] = useState(false);

  const fetchApiKeys = async () => {
    if (!api) return;

    try {
      setIsLoading(true);
      setError(null);
      setPermissionError(false);

      const response = await api.auth.getAllActiveApiKeysAuthApiKeysGet();
      setApiKeys(response.data || []);
    } catch (err: any) {
      console.error("Failed to fetch API keys:", err);

      const status = err?.response?.status;
      const errorMessage = err?.response?.data?.detail || err?.message || "Unknown error";

      // Check if it's a permission error (403 or 401)
      if (status === 403 || status === 401) {
        setPermissionError(true);
        setError("You do not have permissions for this, please use an authorized API key or contact your administrator.");
      } else {
        // Show the actual error message from the API
        setError(`Failed to load API keys: ${errorMessage}`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (api) {
      fetchApiKeys();
    }
  }, [api]);

  const getRoleDisplayName = (role: string): string => {
    const displayNames: Record<string, string> = {
      "DEFAULT-RULE-ADMIN": "Default Rule Admin",
      "TASK-ADMIN": "Task Admin",
      "VALIDATION-USER": "Validation User",
      "ORG-AUDITOR": "Organization Auditor",
      "ORG-ADMIN": "Organization Admin",
    };
    return displayNames[role] || role;
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const handleDeleteClick = (apiKey: ApiKeyResponse) => {
    setDeleteModal({ isOpen: true, apiKey });
  };

  const handleDeleteConfirm = async () => {
    if (!deleteModal.apiKey || !api) return;

    try {
      setIsDeleting(true);
      setError(null);

      await api.auth.deactivateApiKeyAuthApiKeysDeactivateApiKeyIdDelete(deleteModal.apiKey.id);

      // Refresh the API keys list
      await fetchApiKeys();

      // Close modal
      setDeleteModal({ isOpen: false, apiKey: null });
    } catch (err: any) {
      console.error("Failed to delete API key:", err);

      const status = err?.response?.status;
      const errorMessage = err?.response?.data?.detail || err?.message || "Unknown error";

      // Check if it's a permission error
      if (status === 403 || status === 401) {
        setError("You do not have permissions for this, please use an authorized API key or contact your administrator.");
        setPermissionError(true);
      } else {
        setError(`Failed to delete API key: ${errorMessage}`);
      }
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteModal({ isOpen: false, apiKey: null });
  };

  const handleCreateClick = () => {
    setCreateModal(true);
    setSelectedRole("VALIDATION-USER");
    setDescription("");
  };

  const handleCreateConfirm = async () => {
    if (!api) return;

    try {
      setIsCreating(true);
      setError(null);

      const response = await api.auth.createApiKeyAuthApiKeysPost({
        roles: [selectedRole],
        description: description.trim() || null,
      });

      // Store the created key to show in a modal
      setCreatedKey(response.data.key || null);

      // Refresh the API keys list
      await fetchApiKeys();

      // Close create modal and show the created key modal
      setCreateModal(false);
      setShowCreatedKeyModal(true);
      setSelectedRole("VALIDATION-USER");
      setDescription("");
    } catch (err: any) {
      console.error("Failed to create API key:", err);

      const status = err?.response?.status;
      const errorMessage = err?.response?.data?.detail || err?.message || "Unknown error";

      // Check if it's a permission error
      if (status === 403 || status === 401) {
        setError("You do not have permissions for this, please use an authorized API key or contact your administrator.");
        setPermissionError(true);
      } else {
        setError(`Failed to create API key: ${errorMessage}`);
      }
    } finally {
      setIsCreating(false);
    }
  };

  const handleCreateCancel = () => {
    setCreateModal(false);
    setSelectedRole("VALIDATION-USER");
    setDescription("");
  };

  const handleCopyKey = () => {
    if (createdKey) {
      navigator.clipboard.writeText(createdKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleCloseCreatedKeyModal = () => {
    setShowCreatedKeyModal(false);
    setCreatedKey(null);
    setCopied(false);
  };

  if (isLoading) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: 256,
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (permissionError) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error">
          <Typography variant="h6">Permission Denied</Typography>
          <Typography>{error}</Typography>
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 3, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Box>
          <Typography variant="h5" component="h2" gutterBottom color="text.primary" fontWeight="bold">
            API Keys Management
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Create and manage API keys for accessing the GenAI Engine.
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<Add />} onClick={handleCreateClick}>
          Create New Key
        </Button>
      </Box>

      {error && !permissionError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Card>
        <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
          <TableContainer sx={{ maxHeight: "calc(100vh - 200px)", overflow: "auto" }}>
            <Table stickyHeader size="small" sx={{ width: "100%" }}>
              <TableHead>
                <TableRow>
                  <TableCell
                    sx={{
                      fontWeight: "bold",
                      backgroundColor: "grey.100",
                      width: "30%",
                    }}
                  >
                    Description
                  </TableCell>
                  <TableCell
                    sx={{
                      fontWeight: "bold",
                      backgroundColor: "grey.100",
                      width: "25%",
                    }}
                  >
                    Role
                  </TableCell>
                  <TableCell
                    sx={{
                      fontWeight: "bold",
                      backgroundColor: "grey.100",
                      width: "30%",
                    }}
                  >
                    Created At
                  </TableCell>
                  <TableCell
                    sx={{
                      fontWeight: "bold",
                      backgroundColor: "grey.100",
                      width: "15%",
                    }}
                    align="right"
                  >
                    Actions
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {apiKeys.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} align="center">
                      <Box sx={{ py: 4 }}>
                        <VpnKey sx={{ fontSize: 48, color: "grey.400", mb: 2 }} />
                        <Typography variant="body2" color="text.secondary">
                          No API keys found. Create your first key to get started.
                        </Typography>
                      </Box>
                    </TableCell>
                  </TableRow>
                ) : (
                  apiKeys.map((apiKey) => (
                    <TableRow key={apiKey.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">
                          {apiKey.description || "No description"}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          ID: {apiKey.id.substring(0, 8)}...
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {apiKey.roles && apiKey.roles.length > 0 ? apiKey.roles.map(getRoleDisplayName).join(", ") : "No role assigned"}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{formatDate(apiKey.created_at)}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <IconButton size="small" color="error" onClick={() => handleDeleteClick(apiKey)} title="Delete API key">
                          <Delete />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Create API Key Modal */}
      <Dialog open={createModal} onClose={handleCreateCancel} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ textAlign: "center", pb: 1 }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              mb: 2,
            }}
          >
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: "50%",
                bgcolor: "primary.light",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <VpnKey sx={{ color: "primary.main", fontSize: 24 }} />
            </Box>
          </Box>
          Create New API Key
        </DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="dense" required>
            <InputLabel id="role-select-label">Role</InputLabel>
            <Select
              labelId="role-select-label"
              id="role-select"
              value={selectedRole}
              label="Role"
              onChange={(e) => setSelectedRole(e.target.value as APIKeysRolesEnum)}
              disabled={isCreating}
            >
              <MenuItem value="VALIDATION-USER">Validation User</MenuItem>
              <MenuItem value="TASK-ADMIN">Task Admin</MenuItem>
              <MenuItem value="DEFAULT-RULE-ADMIN">Default Rule Admin</MenuItem>
              <MenuItem value="ORG-AUDITOR">Organization Auditor</MenuItem>
              <MenuItem value="ORG-ADMIN">Organization Admin</MenuItem>
            </Select>
            <FormHelperText>Select the role that will be assigned to this API key</FormHelperText>
          </FormControl>
          <TextField
            margin="dense"
            id="description"
            label="Description (Optional)"
            type="text"
            fullWidth
            variant="outlined"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Enter a description for this key..."
            disabled={isCreating}
            helperText="Add a description to help identify this key later"
          />
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={handleCreateCancel} disabled={isCreating} variant="outlined">
            Cancel
          </Button>
          <Button
            onClick={handleCreateConfirm}
            disabled={isCreating}
            variant="contained"
            startIcon={isCreating ? <CircularProgress size={16} /> : <Add />}
          >
            {isCreating ? "Creating..." : "Create Key"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Created Key Display Modal */}
      <Dialog open={showCreatedKeyModal} onClose={handleCloseCreatedKeyModal} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ textAlign: "center", pb: 1 }}>API Key Created Successfully</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mt: 2, mb: 3 }}>
            <Typography variant="body2">Make sure to copy your API key now. You won't be able to see it again!</Typography>
          </Alert>
          <Box
            sx={{
              backgroundColor: "grey.100",
              borderRadius: 2,
              p: 2.5,
              border: "1px solid",
              borderColor: "grey.300",
              fontFamily: "monospace",
              fontSize: "0.875rem",
              wordBreak: "break-all",
              textAlign: "left",
              lineHeight: 1.6,
            }}
          >
            {createdKey || ""}
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={handleCopyKey} variant="outlined" disabled={copied}>
            {copied ? "Copied!" : "Copy to Clipboard"}
          </Button>
          <Button onClick={handleCloseCreatedKeyModal} variant="contained">
            Done
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Modal */}
      <Dialog open={deleteModal.isOpen} onClose={handleDeleteCancel} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ pb: 1, display: "flex", alignItems: "center", gap: 1 }}>
          <Error sx={{ color: "error.main" }} />
          Delete API Key
        </DialogTitle>
        <DialogContent sx={{ mt: 2 }}>
          <Typography variant="body1" sx={{ mb: 2 }}>
            Are you sure you want to delete this API key? This action cannot be undone. Any applications using this key will lose access immediately.
          </Typography>
          {deleteModal.apiKey?.description && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Description:{" "}
              <Typography component="span" fontWeight="bold">
                {deleteModal.apiKey.description}
              </Typography>
            </Typography>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={handleDeleteCancel} disabled={isDeleting} variant="outlined">
            Cancel
          </Button>
          <Button
            onClick={handleDeleteConfirm}
            disabled={isDeleting}
            color="error"
            variant="contained"
            startIcon={isDeleting ? <CircularProgress size={16} /> : <Delete />}
          >
            {isDeleting ? "Deleting..." : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};
