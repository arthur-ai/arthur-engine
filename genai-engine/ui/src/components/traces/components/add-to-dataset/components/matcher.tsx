import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import { Box, Stack, Tooltip, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useMemo } from "react";

import { withFieldGroup } from "../../filtering/hooks/form";

import { useTransform } from "@/hooks/transforms/useTransform";
import { useDatasetLatestVersion } from "@/hooks/useDatasetLatestVersion";

type MatchStatus = "full-match" | "partial" | "no-match";

const STATUS_CONFIG: Record<MatchStatus, { backgroundColor: string; borderColor: string; color: string }> = {
  "full-match": { backgroundColor: "var(--color-green-50)", borderColor: "var(--color-green-200)", color: "var(--color-green-700)" },
  partial: { backgroundColor: "var(--color-amber-50)", borderColor: "var(--color-amber-200)", color: "var(--color-amber-700)" },
  "no-match": { backgroundColor: "var(--color-red-50)", borderColor: "var(--color-red-200)", color: "var(--color-red-700)" },
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

    const { matchingNames, unmatchedTransform } = useMemo(() => {
      const datasetNames = new Set(dataset?.column_names ?? []);
      const transformNames = transform?.definition.variables?.map((v) => v.variable_name) ?? [];
      const transformNamesSet = new Set(transformNames);

      const matching = [...datasetNames].filter((name) => transformNamesSet.has(name));
      const unmatchedFromTransform = transformNames.filter((name) => !datasetNames.has(name));

      return {
        matchingNames: matching,
        unmatchedTransform: unmatchedFromTransform,
      };
    }, [dataset?.column_names, transform?.definition.variables]);

    // We only show the matcher if a transform is selected
    if (!transformId) return null;

    const totalTransformVars = transform?.definition.variables?.length ?? 0;
    const matchCount = matchingNames.length;

    const matchStatus: MatchStatus =
      matchCount > 0 && unmatchedTransform.length === 0 ? "full-match" : matchCount === 0 && totalTransformVars > 0 ? "no-match" : "partial";

    const config = STATUS_CONFIG[matchStatus];

    return (
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          px: 2,
          py: 1,
          borderRadius: 1,
          "--background-color": config.backgroundColor,
          "--border-color": config.borderColor,
          "--color": config.color,
        }}
        className="bg-(--background-color) border-(--border-color) border"
      >
        {matchStatus === "full-match" ? (
          <CheckCircleOutlineIcon sx={{ fontSize: 20 }} className="text-(--color)" />
        ) : (
          <ErrorOutlineIcon sx={{ fontSize: 20 }} className="text-(--color)" />
        )}

        <Stack direction="row" gap={1} alignItems="center" flex={1}>
          <Typography variant="body2" color="text.secondary">
            Column match:
          </Typography>
          <Typography variant="body2" fontWeight={600} className="text-(--color)">
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
              className="bg-(--border-color) rounded-md"
              sx={{
                px: 0.5,
                py: 0,
                borderRadius: 1,
              }}
            >
              <Typography variant="caption" sx={{ cursor: "help", fontSize: 12 }} className="text-(--color)">
                +{unmatchedTransform.length} new
              </Typography>
            </Box>
          </Tooltip>
        )}
      </Box>
    );
  },
});
