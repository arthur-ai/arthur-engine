import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { Collapsible } from "@base-ui-components/react/collapsible";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { Button, Paper } from "@mui/material";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { createContext, Fragment, useContext } from "react";
import { useNavigate } from "react-router-dom";

import { getSpanDetailsStrategy, SpanDetailsStrategy } from "../data/details-strategy";
import { useTracesHistoryStore } from "../stores/history.store";
import { getSpanDuration, isSpanOfType } from "../utils/spans";

import { CopyableChip } from "@/components/common";
import { Tabs } from "@/components/ui/Tabs";
import { NestedSpanWithMetricsResponse } from "@/lib/api";
import { formatDate } from "@/utils/formatters";

const SpanDetailsContext = createContext<{
  span: NestedSpanWithMetricsResponse;
  strategy: Exclude<SpanDetailsStrategy, undefined>;
} | null>(null);

const useSpanDetails = () => {
  const context = useContext(SpanDetailsContext);
  if (!context) {
    throw new Error("useSpanDetails must be used within a SpanDetailsProvider");
  }
  return context;
};

type Props = {
  span: NestedSpanWithMetricsResponse;
  children: React.ReactNode;
};

export const SpanDetails = ({ span, children }: Props) => {
  const strategy = getSpanDetailsStrategy(span.span_kind as OpenInferenceSpanKind);

  if (!strategy) {
    return null;
  }

  return (
    <SpanDetailsContext.Provider value={{ span, strategy }}>
      <Stack direction="column" spacing={1}>
        {children}
      </Stack>
    </SpanDetailsContext.Provider>
  );
};

export const SpanDetailsHeader = () => {
  const push = useTracesHistoryStore((state) => state.push);
  const navigate = useNavigate();
  const { span } = useSpanDetails();

  const duration = getSpanDuration(span);
  const start = new Date(span.start_time);
  const isLLM = isSpanOfType(span, OpenInferenceSpanKind.LLM);

  const onOpenSpanDrawer = () => {
    push({
      type: "span",
      id: span.span_id,
    });
  };

  const handleOpenInPlayground = () => {
    if (span.task_id) {
      navigate(`/tasks/${span.task_id}/playgrounds/prompts?spanId=${span.span_id}`);
    }
  };

  return (
    <Stack direction="column" spacing={1} justifyContent="center">
      <Stack direction="row" spacing={2} justifyContent="space-between" alignItems="center">
        <Stack
          component="button"
          direction="row"
          spacing={1}
          alignItems="center"
          color="primary.main"
          className="group cursor-pointer"
          onClick={onOpenSpanDrawer}
        >
          <Typography variant="h6" fontWeight={700} className="group-hover:underline">
            {span.span_name}
          </Typography>
        </Stack>
        <Stack direction="row" spacing={1} alignItems="center">
          {isLLM && (
            <Button variant="outlined" size="small" onClick={handleOpenInPlayground} disabled={!span.task_id} startIcon={<OpenInNewIcon />}>
              Open in Playground
            </Button>
          )}
          <CopyableChip label={span.span_id} sx={{ fontFamily: "monospace" }} />
        </Stack>
      </Stack>
      <Stack direction="row" spacing={1}>
        <Typography variant="caption" color="text.secondary">
          {formatDate(start)}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {duration}ms
        </Typography>
      </Stack>
    </Stack>
  );
};

export const SpanDetailsPanels = () => {
  const { span, strategy } = useSpanDetails();

  const tabs = strategy?.tabs;

  return (
    <Stack direction="column" spacing={2}>
      <Tabs.Root defaultValue="formatted">
        <Tabs.List>
          <Tabs.Tab value="formatted">Formatted</Tabs.Tab>
          {tabs?.map((tab) => (
            <Tabs.Tab key={tab.label} value={tab.label}>
              {tab.label}
            </Tabs.Tab>
          ))}
          <Tabs.Indicator />
        </Tabs.List>
        <Tabs.Panel value="formatted" render={<Stack direction="column" gap={1} />}>
          {strategy?.panels.map((panel) => (
            <Collapsible.Root render={<Stack direction="column" spacing={1} />} key={panel.label} defaultOpen={panel.defaultOpen}>
              <Collapsible.Trigger className="group">
                <Stack
                  direction="row"
                  spacing={1}
                  alignItems="center"
                  sx={{
                    color: "text.primary",
                  }}
                >
                  <KeyboardArrowRightIcon fontSize="small" className="group-data-panel-open:rotate-90 transition-transform duration-75" />
                  <Typography variant="body2" color="text.primary" fontWeight={700}>
                    {panel.label}
                  </Typography>
                </Stack>
              </Collapsible.Trigger>
              <Collapsible.Panel>{panel.render(span)}</Collapsible.Panel>
            </Collapsible.Root>
          ))}
        </Tabs.Panel>
        {tabs?.map((tab) => (
          <Tabs.Panel key={tab.label} value={tab.label}>
            {tab.render(span)}
          </Tabs.Panel>
        ))}
      </Tabs.Root>
    </Stack>
  );
};

export const SpanDetailsWidgets = () => {
  const { span, strategy } = useSpanDetails();

  return (
    <Stack direction="row" gap={1} flexWrap="wrap" alignItems="center">
      {strategy.widgets.map((widget, index) =>
        widget.wrapped ? (
          <Paper key={index} variant="outlined" sx={{ px: 1, py: 0.5 }}>
            {widget.render(span)}
          </Paper>
        ) : (
          <Fragment key={index}>{widget.render(span)}</Fragment>
        )
      )}
    </Stack>
  );
};
