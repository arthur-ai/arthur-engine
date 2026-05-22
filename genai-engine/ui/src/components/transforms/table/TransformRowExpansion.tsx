import { Box, Typography } from "@mui/material";

import { useTransformVersions } from "../hooks/useTransformVersions";
import { TransformRowExpansionProps } from "../types";

export const TransformRowExpansion: React.FC<TransformRowExpansionProps> = ({ transform }) => {
  const { data: versions = [] } = useTransformVersions(transform.id);
  const definition = versions[0]?.definition;

  return (
    <Box sx={{ p: 3, backgroundColor: "background.default" }}>
      <Typography variant="subtitle2" fontWeight="medium" gutterBottom>
        Transform Definition
      </Typography>

      <Box sx={{ mb: 3 }}>
        <Typography variant="body2" fontWeight="medium" gutterBottom>
          Variable Mappings ({definition?.variables.length ?? 0})
        </Typography>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          {(definition?.variables ?? []).map((variable, idx) => (
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
        <Box
          component="pre"
          sx={{
            backgroundColor: "background.paper",
            p: 2,
            borderRadius: 1,
            overflow: "auto",
            maxHeight: 400,
            fontSize: 12,
            border: 1,
            borderColor: "divider",
            m: 0,
          }}
        >
          {JSON.stringify(definition, null, 2)}
        </Box>
      </Box>
    </Box>
  );
};
