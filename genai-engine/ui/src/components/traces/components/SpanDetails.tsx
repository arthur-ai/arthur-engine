import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import dayjs from "dayjs";

import { getSpanDetailsStrategy } from "../data/details-strategy";
import { getSpanDuration } from "../utils/spans";

import { CopyableChip } from "@/components/common";
import { NestedSpanWithMetricsResponse } from "@/lib/api";

type Props = {
  span: NestedSpanWithMetricsResponse;
};

export const SpanDetails = ({ span }: Props) => {
  const duration = getSpanDuration(span);
  const start = dayjs(span.start_time);

  const strategy = getSpanDetailsStrategy(
    span.span_kind as OpenInferenceSpanKind
  );

  return (
    <Stack direction="column" spacing={1} sx={{ px: 4, py: 2 }}>
      <Stack
        direction="row"
        spacing={2}
        justifyContent="space-between"
        alignItems="center"
      >
        <Stack direction="column" spacing={0}>
          <Typography variant="body2" color="text.secondary">
            Span Details
          </Typography>
          <Typography variant="h6" color="text.primary" fontWeight={700}>
            {span.span_name}
          </Typography>
        </Stack>
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

      <Stack direction="row" spacing={1}>
        {strategy?.widgets?.map((widget) => (
          <Chip
            key={widget.render.toString()}
            variant="outlined"
            size="small"
            label={widget.render(span)}
          />
        ))}
      </Stack>

      <Stack direction="column" spacing={2}>
        {strategy?.panels.map((panel) => (
          <Stack key={panel.label} direction="column" spacing={1}>
            <Typography variant="body2" color="text.primary" fontWeight={700}>
              {panel.label}
            </Typography>
            {panel.render(span)}
          </Stack>
        ))}
      </Stack>
    </Stack>
  );
};
