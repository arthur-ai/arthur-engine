import { Storage } from "@mui/icons-material";
import { Box, Typography } from "@mui/material";

export const RagProvidersEmptyState = () => {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "300px",
        gap: 2,
        px: 3,
        py: 4,
      }}
    >
      <Storage sx={{ fontSize: 64, color: "text.secondary", opacity: 0.5 }} />
      <Typography variant="h6" color="text.secondary">
        No RAG Providers Yet
      </Typography>
      <Typography variant="body2" color="text.secondary" textAlign="center" sx={{ maxWidth: "400px" }}>
        Get started by creating your first RAG provider. Connect to your vector database to enable semantic search and retrieval-augmented generation
        for your tasks.
      </Typography>
      <Typography variant="caption" color="text.secondary" textAlign="center" sx={{ mt: 1 }}>
        Click the "Create Provider" button above to get started
      </Typography>
    </Box>
  );
};
