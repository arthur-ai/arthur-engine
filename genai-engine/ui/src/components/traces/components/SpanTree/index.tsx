import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { Accordion } from "@base-ui-components/react/accordion";
import AccessTimeOutlinedIcon from "@mui/icons-material/AccessTimeOutlined";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { Box } from "@mui/material";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useMemo } from "react";

import { useSelectionStore } from "../../stores/selection.store";
import { Bucket, Bucketer, makeBucketer, Thresholds } from "../../utils/duration";
import { getSpanDuration, getSpanType } from "../../utils/spans";

import { TypeChip } from "@/components/common/span/TypeChip";
import { NestedSpanWithMetricsResponse } from "@/lib/api";
import { formatDuration } from "@/utils/formatters";
import { BUCKET_COLORS, DurationCell } from "../../data/common";

type Props = {
  level?: number;
  spans: NestedSpanWithMetricsResponse[];
  ancestors?: Set<string>;
  thresholds?: Thresholds;
};

export const SpanTree = ({ level = 0, spans, ancestors = new Set(), thresholds }: Props) => {
  const selectedSpanId = useSelectionStore((state) => state.selection.span);
  const select = useSelectionStore((state) => state.select);

  const values = spans.map((span) => span.span_id);

  const bucketer = useMemo(() => (thresholds ? makeBucketer(thresholds.p50, thresholds.p90) : undefined), [thresholds]);

  return (
    <Accordion.Root defaultValue={values} keepMounted>
      {spans.map((span) => (
        <Accordion.Item
          value={span.span_id}
          key={span.span_id}
          data-selected={span.span_id === selectedSpanId ? "" : undefined}
          className="group data-selected:*:bg-gray-200"
          onClick={(e) => {
            e.stopPropagation();
            select("span", span.span_id);
          }}
        >
          <SpanTreeItem span={span} level={level} bucketer={bucketer} />
          <Accordion.Panel
            render={
              <Box className="h-(--accordion-panel-height) overflow-hidden text-base text-gray-600 transition-[height] ease-out data-ending-style:h-0 data-starting-style:h-0 data-open:rounded-b" />
            }
          >
            <SpanTree spans={span.children ?? []} level={level + 1} ancestors={new Set(ancestors).add(span.span_id)} thresholds={thresholds} />
          </Accordion.Panel>
        </Accordion.Item>
      ))}
    </Accordion.Root>
  );
};

const SpanTreeItem = ({ span, level, bucketer }: { span: NestedSpanWithMetricsResponse; level: number; bucketer: Bucketer }) => {
  const selectedSpanId = useSelectionStore((state) => state.selection.span);

  const isSelected = span.span_id === selectedSpanId;
  const hasChildren = span.children && span.children.length > 0;

  const chip = <TypeChip type={getSpanType(span) ?? OpenInferenceSpanKind.AGENT} active={isSelected} />;

  const duration = getSpanDuration(span);

  const bucket = duration ? bucketer!(duration) : "ok";

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
            {duration ? <DurationCell duration={duration} bucketer={bucketer} /> : null}
          </Stack>
        </Stack>
      </Accordion.Header>
    </>
  );
};
