import { Collapsible } from "@base-ui/react/collapsible";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { Box, Chip, Paper, Stack, Typography } from "@mui/material";

import { getSpanErrorInfo } from "../utils/spans";

import { Highlight } from "@/components/common/Highlight";
import { NestedSpanWithMetricsResponse } from "@/lib/api";

type Props = {
  span: NestedSpanWithMetricsResponse;
};

const tryParseJson = (value: string): unknown => {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
};

export const SpanErrorPanel = ({ span }: Props) => {
  const errorInfo = getSpanErrorInfo(span);

  if (!errorInfo) return null;

  const { code, message, type, stacktrace } = errorInfo;
  const parsedMessage = tryParseJson(message);
  const messageIsJsonObject = parsedMessage !== null && typeof parsedMessage === "object";
  const titleText = type ?? "Error";

  return (
    <Paper variant="outlined" sx={{ borderColor: "error.main", p: 2 }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1, flexWrap: "wrap" }}>
        <Typography variant="subtitle2" fontWeight={700} color="error.main">
          {titleText}
        </Typography>
        <Chip label={code} size="small" color="error" variant="outlined" sx={{ fontFamily: "monospace", fontSize: 10 }} />
      </Stack>
      {messageIsJsonObject ? (
        <Highlight code={JSON.stringify(parsedMessage, null, 2)} language="json" unwrapped />
      ) : (
        <Typography
          component="pre"
          variant="body2"
          sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word", fontFamily: "monospace", fontSize: 12, m: 0 }}
        >
          {message}
        </Typography>
      )}
      {stacktrace && (
        <Box sx={{ mt: 1.5 }}>
          <Collapsible.Root render={<Stack direction="column" spacing={1} />}>
            <Collapsible.Trigger className="group">
              <Stack direction="row" spacing={1} alignItems="center" sx={{ color: "text.secondary" }}>
                <KeyboardArrowRightIcon fontSize="small" className="group-data-panel-open:rotate-90 transition-transform duration-75" />
                <Typography variant="caption" fontWeight={700}>
                  Stacktrace
                </Typography>
              </Stack>
            </Collapsible.Trigger>
            <Collapsible.Panel>
              <Highlight code={stacktrace} language="none" unwrapped />
            </Collapsible.Panel>
          </Collapsible.Root>
        </Box>
      )}
    </Paper>
  );
};
