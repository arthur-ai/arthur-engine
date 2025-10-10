import { Accordion } from "@base-ui-components/react/accordion";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import { Box } from "@mui/material";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { useTracesStore } from "../../store";
import { getSpanDuration } from "../../utils/spans";

import { NestedSpanWithMetricsResponse } from "@/lib/api";

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
  const [selectedSpanId, store] = useTracesStore(
    (state) => state.context.selectedSpanId
  );

  const values = spans.map((span) => span.span_id);

  return (
    <Accordion.Root defaultValue={values} keepMounted>
      {spans.map((span) => (
        <Accordion.Item
          value={span.span_id}
          key={span.span_id}
          data-selected={span.span_id === selectedSpanId ? "" : undefined}
          className="group"
          onClick={(e) => {
            e.stopPropagation();

            store.send({
              type: "selectSpan",
              id: span.span_id,
            });
          }}
        >
          <SpanTreeItem span={span} level={level} />
          <Accordion.Panel
            render={
              <Box className="h-[var(--accordion-panel-height)] overflow-hidden text-base text-gray-600 transition-[height] ease-out data-[ending-style]:h-0 data-[starting-style]:h-0 data-open:rounded-b group-data-selected:bg-gray-200" />
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
  const [selectedSpanId] = useTracesStore(
    (state) => state.context.selectedSpanId
  );

  const isSelected = span.span_id === selectedSpanId;
  const hasChildren = span.children && span.children.length > 0;

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
            pl: `${4 + level * 16}px`,
            py: 0.5,
            backgroundColor: isSelected ? "primary.main" : "transparent",
            color: isSelected ? "primary.contrastText" : "text.primary",
          }}
        />
      }
    >
      <Accordion.Trigger className="group">
        <KeyboardArrowDownIcon
          color="inherit"
          sx={{
            outline: "none",
            visibility:
              span.children && span.children.length > 0 ? "visible" : "hidden",
          }}
          fontSize="small"
          className="group-data-[panel-open]:rotate-180"
        />
      </Accordion.Trigger>
      <Stack
        direction="row"
        alignItems="center"
        spacing={0}
        sx={{
          position: "relative",
        }}
      >
        <Stack direction="column" alignItems="flex-start" spacing={-0.5}>
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
