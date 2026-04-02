import { TrendingUpOutlined, OpenInNewOutlined, BalanceOutlined, CloseOutlined, InfoOutlined } from "@mui/icons-material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import GeneratingTokensOutlinedIcon from "@mui/icons-material/GeneratingTokensOutlined";
import TollOutlinedIcon from "@mui/icons-material/TollOutlined";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  Paper,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { LineChart } from "@mui/x-charts/LineChart";
import React, { useState } from "react";

import { ChartCard } from "./task-overview/ChartCard";
import { METRIC_COLORS, formatCostAxisValue, formatNumber, formatPercentValue, formatXLabel } from "./task-overview/constants";
import { MetricCard } from "./task-overview/MetricCard";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useTask } from "@/hooks/useTask";
import { useTaskOverviewMetrics } from "@/hooks/useTaskOverviewMetrics";
import { formatCurrency, formatDateInTimezone } from "@/utils/formatters";
import { TimeInterval } from "@/utils/timeWindows";

type TimeRangeButton = "Day" | "Last 7 Days" | "MTD" | "YTD";

const timeIntervalMap: Record<TimeRangeButton, TimeInterval> = {
  Day: "day",
  "Last 7 Days": "week",
  MTD: "mtd",
  YTD: "ytd",
};

const timeRanges: TimeRangeButton[] = ["Day", "Last 7 Days", "MTD", "YTD"];

const getTimeRangeLabel = (button: TimeRangeButton): string => {
  const labels: Record<TimeRangeButton, string> = {
    Day: "Day",
    "Last 7 Days": "Last 7 Days",
    MTD: "MTD",
    YTD: "YTD",
  };
  return labels[button];
};

export const TaskOverview: React.FC = () => {
  const { task } = useTask();
  const { defaultCurrency, timezone, use24Hour, scopeUrl } = useDisplaySettings();
  const [selectedTimeRangeButton, setSelectedTimeRangeButton] = useState<TimeRangeButton>("Last 7 Days");
  const [taskDetailsOpen, setTaskDetailsOpen] = useState(false);

  const interval = timeIntervalMap[selectedTimeRangeButton];

  const {
    data: metrics,
    isLoading,
    error,
  } = useTaskOverviewMetrics({
    taskId: task?.id || "",
    interval,
  });

  if (!task) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: 256 }}>
        <CircularProgress />
      </Box>
    );
  }

  const displayLabel = getTimeRangeLabel(selectedTimeRangeButton);
  const xLabelFormat = metrics?.xLabelFormat || "date";
  const tickStep = metrics?.tickStep || 1;

  const timeSeriesData = metrics?.timeSeriesData || [];
  const xAxisLabels = timeSeriesData.map((d) => formatXLabel(new Date(d.timestamp), xLabelFormat, timezone));

  const tracesValues = timeSeriesData.map((d) => d.tracesCount);
  const tokensValues = timeSeriesData.map((d) => d.tokens);
  const costValues = timeSeriesData.map((d) => d.cost);
  const successRateValues = timeSeriesData.map((d) => d.successRate);

  const sharedXAxis = [
    {
      scaleType: "band" as const,
      data: xAxisLabels,
      tickLabelInterval: (_value: string, index: number) => index % tickStep === 0,
    },
  ];

  return (
    <Box sx={{ py: 3, px: 3, bgcolor: "background.default" }}>
      <Stack spacing={3} sx={{ maxWidth: 1400, mx: "auto" }}>
        {/* Header */}
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Box>
            <Typography variant="h5" fontWeight={600} color="text.primary">
              {task.name || "Task Overview"}
            </Typography>
            <Stack direction="row" alignItems="center" gap={0.5} sx={{ mt: 0.5 }}>
              <Typography variant="body2" color="text.secondary">
                Analyze key performance metrics at a glance
              </Typography>
              <Typography variant="body2" color="text.secondary">
                ·
              </Typography>
              <Button
                size="small"
                variant="text"
                startIcon={<InfoOutlined sx={{ fontSize: "14px !important" }} />}
                onClick={() => setTaskDetailsOpen(true)}
                sx={{
                  textTransform: "none",
                  color: "text.secondary",
                  fontSize: "0.875rem",
                  p: 0,
                  minWidth: 0,
                  lineHeight: "inherit",
                  "&:hover": { color: "text.primary", bgcolor: "transparent" },
                }}
              >
                Task Details
              </Button>
            </Stack>
          </Box>
          <ToggleButtonGroup
            size="small"
            value={selectedTimeRangeButton}
            exclusive
            onChange={(_e, value) => {
              if (value !== null) setSelectedTimeRangeButton(value);
            }}
          >
            {timeRanges.map((range) => (
              <ToggleButton key={range} value={range} sx={{ px: 1.5, py: 0.5, fontSize: "0.75rem" }}>
                {range}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Stack>

        {/* Task Details Modal */}
        <Dialog open={taskDetailsOpen} onClose={() => setTaskDetailsOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", pb: 1 }}>
            <Stack direction="row" alignItems="center" gap={1}>
              <Typography variant="subtitle1" fontWeight={600}>
                {task?.name || "Untitled Task"}
              </Typography>
              {task?.is_agentic && <Chip label="Agentic" size="small" color="primary" variant="outlined" />}
            </Stack>
            <IconButton size="small" onClick={() => setTaskDetailsOpen(false)} edge="end">
              <CloseOutlined fontSize="small" />
            </IconButton>
          </DialogTitle>
          <Divider />
          <DialogContent>
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 3, pt: 1 }}>
              <Box>
                <Typography variant="body2" color="text.secondary" fontWeight={500}>
                  Task ID
                </Typography>
                <Typography variant="body2" color="text.primary" sx={{ mt: 0.5, fontFamily: "monospace", wordBreak: "break-all" }}>
                  {task?.id}
                </Typography>
              </Box>

              {task?.is_agentic !== undefined && (
                <Box>
                  <Typography variant="body2" color="text.secondary" fontWeight={500}>
                    Type
                  </Typography>
                  <Typography variant="body2" color="text.primary" sx={{ mt: 0.5 }}>
                    {task.is_agentic ? "Agentic Task" : "Standard Task"}
                  </Typography>
                </Box>
              )}

              <Box>
                <Typography variant="body2" color="text.secondary" fontWeight={500}>
                  Created At
                </Typography>
                <Typography variant="body2" color="text.primary" sx={{ mt: 0.5 }}>
                  {task?.created_at ? formatDateInTimezone(task.created_at, timezone, { hour12: !use24Hour }) : "Not available"}
                </Typography>
              </Box>

              <Box>
                <Typography variant="body2" color="text.secondary" fontWeight={500}>
                  Updated At
                </Typography>
                <Typography variant="body2" color="text.primary" sx={{ mt: 0.5 }}>
                  {task?.updated_at ? formatDateInTimezone(task.updated_at, timezone, { hour12: !use24Hour }) : "Not available"}
                </Typography>
              </Box>
            </Box>
          </DialogContent>
        </Dialog>

        {/* Error state */}
        {error && <Alert severity="error">Failed to load metrics. Please try again.</Alert>}

        {/* Metric Cards */}
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(5, 1fr)" } }}>
          <MetricCard
            icon={<TrendingUpOutlined fontSize="inherit" />}
            label="Traces"
            value={formatNumber(metrics?.tracesCount || 0)}
            subLabel={`${displayLabel} total`}
            color={METRIC_COLORS.traces.main}
            bgColor={METRIC_COLORS.traces.light}
            darkBgColor={METRIC_COLORS.traces.dark}
            borderColor={METRIC_COLORS.traces.border}
            darkBorderColor={METRIC_COLORS.traces.darkBorder}
            isLoading={isLoading}
          />
          <MetricCard
            icon={<GeneratingTokensOutlinedIcon fontSize="inherit" />}
            label="Tokens"
            value={formatNumber(metrics?.totalTokens || 0)}
            subLabel={`${displayLabel} total`}
            color={METRIC_COLORS.tokens.main}
            bgColor={METRIC_COLORS.tokens.light}
            darkBgColor={METRIC_COLORS.tokens.dark}
            borderColor={METRIC_COLORS.tokens.border}
            darkBorderColor={METRIC_COLORS.tokens.darkBorder}
            isLoading={isLoading}
          />
          <MetricCard
            icon={<TollOutlinedIcon fontSize="inherit" />}
            label="Cost"
            value={formatCurrency(metrics?.totalCost ?? 0, defaultCurrency)}
            subLabel="est. spend"
            color={METRIC_COLORS.cost.main}
            bgColor={METRIC_COLORS.cost.light}
            darkBgColor={METRIC_COLORS.cost.dark}
            borderColor={METRIC_COLORS.cost.border}
            darkBorderColor={METRIC_COLORS.cost.darkBorder}
            isLoading={isLoading}
          />
          <MetricCard
            icon={<BalanceOutlined fontSize="inherit" />}
            label="Evals"
            value={formatNumber(metrics?.evalsCount || 0)}
            subLabel={`${displayLabel} total`}
            color={METRIC_COLORS.evals.main}
            bgColor={METRIC_COLORS.evals.light}
            darkBgColor={METRIC_COLORS.evals.dark}
            borderColor={METRIC_COLORS.evals.border}
            darkBorderColor={METRIC_COLORS.evals.darkBorder}
            isLoading={isLoading}
          />
          <MetricCard
            icon={<CheckCircleIcon fontSize="inherit" />}
            label="Success Rate"
            value={`${metrics?.successRate.toFixed(1) || 0}%`}
            subLabel="avg. rate"
            color={METRIC_COLORS.successRate.main}
            bgColor={METRIC_COLORS.successRate.light}
            darkBgColor={METRIC_COLORS.successRate.dark}
            borderColor={METRIC_COLORS.successRate.border}
            darkBorderColor={METRIC_COLORS.successRate.darkBorder}
            isLoading={isLoading}
          />
        </Box>

        {/* Charts */}
        <Box sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" } }}>
          <ChartCard icon={<TrendingUpOutlined fontSize="inherit" />} title="Traces" iconColor={METRIC_COLORS.traces.main} isLoading={isLoading}>
            {timeSeriesData.length > 0 ? (
              <LineChart
                height={256}
                xAxis={sharedXAxis}
                yAxis={[{ valueFormatter: (v: number) => formatNumber(v) }]}
                series={[
                  {
                    data: tracesValues,
                    color: METRIC_COLORS.traces.main,
                    area: true,
                    showMark: true,
                    label: "Traces",
                    valueFormatter: (v: number | null) => (v != null ? formatNumber(v) : ""),
                  },
                ]}
                grid={{ horizontal: true }}
                margin={{ left: 50, right: 20, top: 20, bottom: 30 }}
                hideLegend
                sx={{ "& .MuiAreaElement-root": { fillOpacity: 0.1 } }}
              />
            ) : (
              <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: 256 }}>
                <Typography variant="body2" color="text.secondary">
                  No data available
                </Typography>
              </Box>
            )}
          </ChartCard>

          <ChartCard
            icon={<GeneratingTokensOutlinedIcon fontSize="inherit" />}
            title="Tokens"
            iconColor={METRIC_COLORS.tokens.main}
            isLoading={isLoading}
          >
            {timeSeriesData.length > 0 ? (
              <BarChart
                height={256}
                xAxis={sharedXAxis}
                yAxis={[{ valueFormatter: (v: number) => formatNumber(v) }]}
                series={[
                  {
                    data: tokensValues,
                    color: METRIC_COLORS.tokens.main,
                    label: "Tokens",
                    valueFormatter: (v: number | null) => (v != null ? formatNumber(v) : ""),
                  },
                ]}
                grid={{ horizontal: true }}
                margin={{ left: 50, right: 20, top: 20, bottom: 30 }}
                borderRadius={4}
                hideLegend
              />
            ) : (
              <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: 256 }}>
                <Typography variant="body2" color="text.secondary">
                  No data available
                </Typography>
              </Box>
            )}
          </ChartCard>

          <ChartCard icon={<TollOutlinedIcon fontSize="inherit" />} title="Estimated Cost" iconColor={METRIC_COLORS.cost.main} isLoading={isLoading}>
            {timeSeriesData.length > 0 ? (
              <LineChart
                height={256}
                xAxis={sharedXAxis}
                yAxis={[{ valueFormatter: (v: number) => formatCostAxisValue(v, defaultCurrency) }]}
                series={[
                  {
                    data: costValues,
                    color: METRIC_COLORS.cost.main,
                    area: true,
                    showMark: true,
                    label: "Cost",
                    valueFormatter: (v: number | null) => (v != null ? formatCostAxisValue(v, defaultCurrency) : ""),
                  },
                ]}
                grid={{ horizontal: true }}
                margin={{ left: 60, right: 20, top: 20, bottom: 30 }}
                hideLegend
                sx={{ "& .MuiAreaElement-root": { fillOpacity: 0.1 } }}
              />
            ) : (
              <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: 256 }}>
                <Typography variant="body2" color="text.secondary">
                  No data available
                </Typography>
              </Box>
            )}
          </ChartCard>

          <ChartCard
            icon={<CheckCircleIcon fontSize="inherit" />}
            title="Success Rate"
            iconColor={METRIC_COLORS.successRate.main}
            isLoading={isLoading}
          >
            {timeSeriesData.length > 0 ? (
              <LineChart
                height={256}
                xAxis={sharedXAxis}
                yAxis={[{ valueFormatter: (v: number) => formatPercentValue(v) }]}
                series={[
                  {
                    data: successRateValues,
                    color: METRIC_COLORS.successRate.main,
                    area: true,
                    showMark: true,
                    label: "Success Rate",
                    valueFormatter: (v: number | null) => (v != null ? formatPercentValue(v) : ""),
                  },
                ]}
                grid={{ horizontal: true }}
                margin={{ left: 50, right: 20, top: 20, bottom: 30 }}
                hideLegend
                sx={{ "& .MuiAreaElement-root": { fillOpacity: 0.1 } }}
              />
            ) : (
              <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: 256 }}>
                <Typography variant="body2" color="text.secondary">
                  No data available
                </Typography>
              </Box>
            )}
          </ChartCard>
        </Box>

        {/* Bottom CTA Banner */}
        {scopeUrl && (
          <Paper variant="outlined" sx={{ p: 3, borderStyle: "dashed", borderWidth: 2, borderColor: "divider" }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Box>
                <Typography variant="subtitle1" fontWeight={500} color="text.secondary">
                  Need deeper analysis?
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  Create custom dashboards with advanced filters, breakdowns, and export options in the Arthur platform.
                </Typography>
              </Box>
              <Button
                variant="outlined"
                color="inherit"
                endIcon={<OpenInNewOutlined />}
                onClick={() => window.open(scopeUrl, "_blank", "noopener,noreferrer")}
                sx={{ whiteSpace: "nowrap" }}
              >
                Open in Arthur Platform
              </Button>
            </Stack>
          </Paper>
        )}
      </Stack>
    </Box>
  );
};
