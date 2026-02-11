import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { Accordion } from "@base-ui/react/accordion";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { Box } from "@mui/material";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { getSpanDuration, getSpanType } from "../../utils/spans";
import { DurationCellWithBucket } from "../DurationCell";
import { SpanStatusBadge } from "../span-status-badge";

import { TypeChip } from "@/components/common/span/TypeChip";
import { NestedSpanWithMetricsResponse } from "@/lib/api";

type Props = {
  level?: number;
  spans: NestedSpanWithMetricsResponse[];
  ancestors?: Set<string>;
  selectedSpanId: string | null;
  onSelectSpan: (spanId: string | null) => void;
};

export const SpanTree = ({ level = 0, spans, ancestors = new Set(), selectedSpanId, onSelectSpan }: Props) => {
  const values = spans.map((span) => span.span_id);

  return (
    <Accordion.Root defaultValue={values} keepMounted>
      {spans.map((span) => (
        <Accordion.Item
          value={span.span_id}
          key={span.span_id}
          data-selected={span.span_id === selectedSpanId ? "" : undefined}
          className="group data-selected:*:bg-gray-200 data-selected:*:dark:bg-gray-700"
          onClick={(e) => {
            e.stopPropagation();
            onSelectSpan(span.span_id);
          }}
        >
          <SpanTreeItem span={span} level={level} selectedSpanId={selectedSpanId} />
          <Accordion.Panel
            render={
              <Box className="h-(--accordion-panel-height) text-base text-gray-600 dark:text-gray-400 transition-[height] ease-out data-ending-style:h-0 data-starting-style:h-0 data-open:rounded-b overflow-hidden" />
            }
          >
            <SpanTree
              spans={span.children ?? []}
              level={level + 1}
              ancestors={new Set(ancestors).add(span.span_id)}
              selectedSpanId={selectedSpanId}
              onSelectSpan={onSelectSpan}
            />
          </Accordion.Panel>
        </Accordion.Item>
      ))}
    </Accordion.Root>
  );
};

const SpanTreeItem = ({ span, level, selectedSpanId }: { span: NestedSpanWithMetricsResponse; level: number; selectedSpanId: string | null }) => {
  const isSelected = span.span_id === selectedSpanId;
  const hasChildren = span.children && span.children.length > 0;

  const chip = <TypeChip type={getSpanType(span) ?? OpenInferenceSpanKind.AGENT} active={isSelected} />;

  const duration = getSpanDuration(span);

  return (
    <>
      <Accordion.Header
        render={
          <Stack
            direction="row"
            alignItems="center"
            spacing={1}
            data-has-children={hasChildren ? "" : undefined}
            className="group-data-selected:rounded-t rounded-b group-data-selected:data-open:data-has-children:rounded-b-none transition-all duration-75 cursor-pointer select-none"
            sx={{
              "--offset-start": "4px",
              "--offset-multiply": 16,
              pl: `calc(var(--offset-start) + var(--offset-multiply) * ${level} * 1px)`,
              py: 0.5,
              backgroundColor: isSelected ? "primary.main" : "transparent",
              color: isSelected ? "primary.contrastText" : "text.primary",
            }}
          />
        }
      >
        <Accordion.Trigger className="group">
          <KeyboardArrowRightIcon
            color="inherit"
            sx={{
              outline: "none",
              visibility: span.children && span.children.length > 0 ? "visible" : "hidden",
            }}
            fontSize="small"
            className="group-data-panel-open:rotate-90"
          />
        </Accordion.Trigger>
        <Stack
          direction="row"
          alignItems="center"
          spacing={0}
          sx={{
            position: "relative",
            width: "100%",
            pr: 1,
          }}
        >
          {chip}
          <Stack direction="row" alignItems="center" justifyContent="space-between" flex={1} gap={0} ml={1}>
            <Typography variant="body2" fontWeight={500} fontSize={12}>
              {span.span_name}
            </Typography>
            <Stack direction="row" alignItems="center" gap={0.5}>
              {typeof duration === "number" ? <DurationCellWithBucket duration={duration} /> : null}
              <SpanStatusBadge status={span.status_code ?? "Unset"} disableLabel />
            </Stack>
          </Stack>
        </Stack>
      </Accordion.Header>
    </>
  );
};
