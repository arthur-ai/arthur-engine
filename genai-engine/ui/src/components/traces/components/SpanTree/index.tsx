import { Accordion } from "@base-ui-components/react/accordion";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { Box } from "@mui/material";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { cloneElement } from "react";

import { useTracesHistoryStore } from "../../stores/history.store";
import { getSpanDuration, getSpanIcon } from "../../utils/spans";

import { NestedSpanWithMetricsResponse } from "@/lib/api";
import { cn } from "@/utils/cn";
import { useSelectionStore } from "../../stores/selection.store";

type Props = {
  level?: number;
  spans: NestedSpanWithMetricsResponse[];
  ancestors?: Set<string>;
};

export const SpanTree = ({
  level = 0,
  spans,
  ancestors = new Set(),
}: Props) => {
  const selectedSpanId = useSelectionStore((state) => state.selection.span);
  const select = useSelectionStore((state) => state.select);

  const values = spans.map((span) => span.span_id);

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
          <SpanTreeItem span={span} level={level} />
          <Accordion.Panel
            render={
              <Box className="h-(--accordion-panel-height) overflow-hidden text-base text-gray-600 transition-[height] ease-out data-ending-style:h-0 data-starting-style:h-0 data-open:rounded-b" />
            }
          >
            <SpanTree
              spans={span.children ?? []}
              level={level + 1}
              ancestors={new Set(ancestors).add(span.span_id)}
            />
          </Accordion.Panel>
        </Accordion.Item>
      ))}
    </Accordion.Root>
  );
};

const SpanTreeItem = ({
  span,
  level,
}: {
  span: NestedSpanWithMetricsResponse;
  level: number;
}) => {
  const selectedSpanId = useSelectionStore((state) => state.selection.span);

  const isSelected = span.span_id === selectedSpanId;
  const hasChildren = span.children && span.children.length > 0;

  const icon = cloneElement(getSpanIcon(span), {
    sx: {
      fontSize: 16,
    },
  });

  return (
    <Accordion.Header
      render={
        <Stack
          direction="row"
          alignItems="center"
          spacing={1}
          data-has-children={hasChildren ? "" : undefined}
          className="group-data-selected:rounded-t rounded-b group-data-selected:data-open:data-has-children:rounded-b-none transition-all duration-75"
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
            visibility:
              span.children && span.children.length > 0 ? "visible" : "hidden",
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
        {icon && (
          <div
            className={cn(
              "flex items-center justify-center p-1 border border-gray-300 rounded-full "
            )}
          >
            {icon}
          </div>
        )}
        <Stack direction="column" alignItems="flex-start" spacing={-0.5} ml={1}>
          <Typography variant="body2" fontWeight={500} fontSize={12}>
            {span.span_name}
          </Typography>
          <Typography variant="caption" color="inherit" fontSize={10}>
            {getSpanDuration(span)}ms
          </Typography>
        </Stack>
      </Stack>
    </Accordion.Header>
  );
};
