import DownloadIcon from "@mui/icons-material/Download";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
} from "@mui/material";

import { DatasetTransform } from "./types";

interface TransformDetailsModalProps {
  open: boolean;
  onClose: () => void;
  transform: DatasetTransform | null;
}

export const TransformDetailsModal: React.FC<TransformDetailsModalProps> = ({
  open,
  onClose,
  transform,
}) => {
  if (!transform) return null;

  const handleDownload = () => {
    // Create the export object with name, description, and definition
    const exportData = {
      name: transform.name,
      description: transform.description,
      definition: transform.definition,
    };

    // Convert to JSON string
    const jsonString = JSON.stringify(exportData, null, 2);

    // Create a blob and download link
    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${transform.name.replace(/[^a-z0-9]/gi, "_").toLowerCase()}_transform.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Transform Details: {transform.name}</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 1 }}>
          {transform.description && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" fontWeight="medium" gutterBottom>
                Description
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {transform.description}
              </Typography>
            </Box>
          )}

          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" fontWeight="medium" gutterBottom>
              Column Mappings ({transform.definition.columns.length})
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1, mt: 1 }}>
              {transform.definition.columns.map((col, idx) => (
                <Box
                  key={idx}
                  sx={{
                    p: 2,
                    backgroundColor: "grey.50",
                    borderRadius: 1,
                    border: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <Typography variant="body2" fontWeight="medium">
                    {col.column_name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Span: <code>{col.span_name}</code> → Path: <code>{col.attribute_path}</code>
                  </Typography>
                  {col.fallback !== undefined && (
                    <Typography variant="caption" color="text.secondary" display="block">
                      Fallback: {JSON.stringify(col.fallback)}
                    </Typography>
                  )}
                </Box>
              ))}
            </Box>
          </Box>

          <Box>
            <Typography variant="subtitle2" fontWeight="medium" gutterBottom>
              Full JSON Definition
            </Typography>
            <pre
              style={{
                backgroundColor: "#ffffff",
                padding: 16,
                borderRadius: 4,
                overflow: "auto",
                maxHeight: 400,
                fontSize: 12,
                border: "1px solid #e0e0e0",
              }}
            >
              {JSON.stringify(transform.definition, null, 2)}
            </pre>
          </Box>
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleDownload} startIcon={<DownloadIcon />}>
          Download JSON
        </Button>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TransformDetailsModal;
