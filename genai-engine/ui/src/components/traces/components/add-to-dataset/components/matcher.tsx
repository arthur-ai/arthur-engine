import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import { Box, Stack, Tooltip, Typography } from "@mui/material";
import { alpha, Theme } from "@mui/material/styles";
import { useStore } from "@tanstack/react-form";

import { withFieldGroup } from "../../filtering/hooks/form";
import { MatchStatus, useMatchingVariables } from "../hooks/useMatchingVariables";

import { useTransform } from "@/hooks/transforms/useTransform";
import { useDatasetLatestVersion } from "@/hooks/useDatasetLatestVersion";

const getStatusConfig = (theme: Theme, status: MatchStatus) => {
  const palette = {
    "full-match": theme.palette.success,
    partial: theme.palette.warning,
    "no-match": theme.palette.error,
  }[status];

  return {
    backgroundColor: alpha(palette.main, 0.12),
    borderColor: alpha(palette.main, 0.4),
    color: palette.main,
  };
};

export const Matcher = withFieldGroup({
  defaultValues: {} as {
    dataset: string;
    transform: string;
  },
  render: function Render({ group }) {
    const datasetId = useStore(group.store, (state) => state.values.dataset);
    const transformId = useStore(group.store, (state) => (state.values.transform === "manual" ? null : state.values.transform));

    const { latestVersion: dataset } = useDatasetLatestVersion(datasetId);
    const { data: transform } = useTransform(transformId ?? undefined);

    const { matchingNames, unmatchedTransform, matchStatus, matchCount } = useMatchingVariables({
      columnNames: dataset?.column_names ?? [],
      variables: transform?.definition.variables ?? [],
    });

    // We only show the matcher if a transform is selected
    if (!transformId) return null;

    const totalTransformVars = transform?.definition.variables?.length ?? 0;

    return (
      <Box
        sx={(theme) => {
          const config = getStatusConfig(theme, matchStatus);
          return {
            display: "flex",
            alignItems: "center",
            gap: 1.5,
            px: 2,
            py: 1,
            borderRadius: 1,
            backgroundColor: config.backgroundColor,
            border: `1px solid ${config.borderColor}`,
          };
        }}
      >
        {matchStatus === "full-match" ? (
          <CheckCircleOutlineIcon sx={(theme) => ({ fontSize: 20, color: getStatusConfig(theme, matchStatus).color })} />
        ) : (
          <ErrorOutlineIcon sx={(theme) => ({ fontSize: 20, color: getStatusConfig(theme, matchStatus).color })} />
        )}

        <Stack direction="row" gap={1} alignItems="center" flex={1}>
          <Typography variant="body2" color="text.secondary">
            Column match:
          </Typography>
          <Typography variant="body2" fontWeight={600} sx={(theme) => ({ color: getStatusConfig(theme, matchStatus).color })}>
            {matchCount} of {totalTransformVars}
          </Typography>

          {matchCount > 0 && (
            <Tooltip
              title={
                <Stack gap={0.5}>
                  <Typography variant="caption" fontWeight={600}>
                    Matched columns:
                  </Typography>
                  {matchingNames.map((name) => (
                    <Typography key={name} variant="caption">
                      • {name}
                    </Typography>
                  ))}
                </Stack>
              }
              arrow
            >
              <Typography
                variant="caption"
                sx={{
                  color: "text.secondary",
                  cursor: "help",
                  textDecoration: "underline",
                  textDecorationStyle: "dotted",
                }}
              >
                ({matchingNames.join(", ")})
              </Typography>
            </Tooltip>
          )}
        </Stack>

        {unmatchedTransform.length > 0 && (
          <Tooltip
            title={
              <Stack gap={0.5}>
                <Typography variant="caption" fontWeight={600}>
                  New columns to add:
                </Typography>
                {unmatchedTransform.map((name) => (
                  <Typography key={name} variant="caption">
                    • {name}
                  </Typography>
                ))}
              </Stack>
            }
            arrow
          >
            <Box
              sx={(theme) => {
                const config = getStatusConfig(theme, matchStatus);
                return {
                  px: 0.5,
                  py: 0,
                  borderRadius: 1,
                  backgroundColor: alpha(theme.palette.mode === "dark" ? config.color : config.borderColor, 0.3),
                  color: config.color,
                };
              }}
            >
              <Typography variant="caption" sx={{ cursor: "help", fontSize: 12 }}>
                +{unmatchedTransform.length} new
              </Typography>
            </Box>
          </Tooltip>
        )}
      </Box>
    );
  },
});
