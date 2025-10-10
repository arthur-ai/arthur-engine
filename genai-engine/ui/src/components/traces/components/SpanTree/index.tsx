import { Accordion } from "@base-ui-components/react/accordion";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { useTracesStore } from "../../store";
import { getSpanDuration } from "../../utils/spans";

import { NestedSpanWithMetricsResponse } from "@/lib/api";

type Props = {
  level?: number;
  spans: NestedSpanWithMetricsResponse[];
};

export const SpanTree = ({ level = 0, spans }: Props) => {
  const [, store] = useTracesStore();

  return (
    <Accordion.Root>
      {spans.map((span) => (
        <Accordion.Item
          key={span.span_id}
          onClick={(e) => {
            e.stopPropagation();

            store.send({
              type: "selectSpan",
              id: span.span_id,
            });
          }}
        >
          <SpanTreeItem span={span} level={level} />
          <Accordion.Panel className="h-[var(--accordion-panel-height)] overflow-hidden text-base text-gray-600 transition-[height] ease-out data-[ending-style]:h-0 data-[starting-style]:h-0">
            <SpanTree spans={span.children ?? []} level={level + 1} />
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

  return (
    <Accordion.Header
      render={
        <Stack
          direction="row"
          alignItems="center"
          spacing={1}
          sx={{
            pl: `${4 + level * 8}px`,
            py: 0.5,
            borderRadius: 1,
            border: "2px solid",
            borderColor: isSelected ? "primary.main" : "transparent",
            "&:hover": {
              backgroundColor: "grey.200",
            },
          }}
        />
      }
    >
      <Accordion.Trigger className="group">
        {span.children && span.children.length > 0 && (
          <KeyboardArrowDownIcon
            color="action"
            sx={{ outline: "none" }}
            fontSize="small"
            className="group-data-[panel-open]:rotate-180"
          />
        )}
      </Accordion.Trigger>
      <Stack
        direction="row"
        alignItems="center"
        spacing={0}
        sx={{
          position: "relative",
        }}
      >
        <Stack
          direction="column"
          alignItems="flex-start"
          spacing={-0.5}
          sx={{
            color: "text.secondary",
          }}
        >
          <Typography variant="body2" fontWeight={500}>
            {span.span_name}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {getSpanDuration(span)}ms
          </Typography>
        </Stack>
      </Stack>
    </Accordion.Header>
  );
};
