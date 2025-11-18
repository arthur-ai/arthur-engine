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
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TransformDetailsModal;
