import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { Collapsible } from "@base-ui-components/react/collapsible";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { Chip } from "@mui/material";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import dayjs from "dayjs";
import { createContext, useContext } from "react";

import {
  getSpanDetailsStrategy,
  SpanDetailsStrategy,
} from "../data/details-strategy";
import { getSpanDuration } from "../utils/spans";

import { CopyableChip } from "@/components/common";
import { NestedSpanWithMetricsResponse } from "@/lib/api";

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
  const strategy = getSpanDetailsStrategy(
    span.span_kind as OpenInferenceSpanKind
  );

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
  const { span } = useSpanDetails();

  const duration = getSpanDuration(span);
  const start = dayjs(span.start_time);

  return (
    <Stack direction="column" spacing={1} justifyContent="center">
      <Stack
        direction="row"
        spacing={2}
        justifyContent="space-between"
        alignItems="center"
      >
        <Typography variant="h6" color="text.primary" fontWeight={700}>
          {span.span_name}
        </Typography>
        <CopyableChip label={span.span_id} sx={{ fontFamily: "monospace" }} />
      </Stack>
      <Stack direction="row" spacing={1}>
        <Typography variant="caption" color="text.secondary">
          {start.format("YYYY-MM-DD HH:mm:ss")}
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

  return (
    <Stack direction="column" spacing={2}>
      {strategy?.panels.map((panel) => (
        <Collapsible.Root
          render={<Stack direction="column" spacing={1} />}
          key={panel.label}
          defaultOpen={panel.defaultOpen}
        >
          <Collapsible.Trigger className="group">
            <Stack
              direction="row"
              spacing={1}
              alignItems="center"
              sx={{
                color: "text.primary",
              }}
            >
              <KeyboardArrowRightIcon
                fontSize="small"
                className="group-data-panel-open:rotate-90 transition-transform duration-75"
              />
              <Typography variant="body2" color="text.primary" fontWeight={700}>
                {panel.label}
              </Typography>
            </Stack>
          </Collapsible.Trigger>
          <Collapsible.Panel>{panel.render(span)}</Collapsible.Panel>
        </Collapsible.Root>
      ))}
    </Stack>
  );
};

export const SpanDetailsWidgets = () => {
  const { span, strategy } = useSpanDetails();

  return (
    <Stack direction="row" spacing={1}>
      {strategy.widgets.map((widget, index) => (
        <Chip
          key={index}
          variant="outlined"
          size="small"
          label={widget.render(span)}
        />
      ))}
    </Stack>
  );
};
