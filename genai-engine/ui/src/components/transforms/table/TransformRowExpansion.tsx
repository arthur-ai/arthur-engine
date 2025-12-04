import { Box, Typography } from "@mui/material";

import { TransformRowExpansionProps } from "../types";

export const TransformRowExpansion: React.FC<TransformRowExpansionProps> = ({ transform }) => {
  return (
    <Box sx={{ p: 3, backgroundColor: "grey.50" }}>
      <Typography variant="subtitle2" fontWeight="medium" gutterBottom>
        Transform Definition
      </Typography>

      <Box sx={{ mb: 3 }}>
        <Typography variant="body2" fontWeight="medium" gutterBottom>
          Variable Mappings ({transform.definition.variables.length})
        </Typography>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          {transform.definition.variables.map((variable, idx) => (
            <Box
              key={idx}
              sx={{
                p: 2,
                backgroundColor: "background.paper",
                borderRadius: 1,
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <Typography variant="body2" fontWeight="medium">
                {variable.variable_name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Span: <code>{variable.span_name}</code> → Path: <code>{variable.attribute_path}</code>
              </Typography>
              {variable.fallback !== undefined && (
                <Typography variant="caption" color="text.secondary" display="block">
                  Fallback: {JSON.stringify(variable.fallback)}
                </Typography>
              )}
            </Box>
          ))}
        </Box>
      </Box>

      <Box>
        <Typography variant="body2" fontWeight="medium" gutterBottom>
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
  );
};
