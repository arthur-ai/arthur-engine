import { Collapsible } from "@base-ui/react/collapsible";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { Alert, AlertTitle, Box, Chip, Stack, Typography } from "@mui/material";

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
    <Collapsible.Root render={<Stack direction="column" spacing={1} />} defaultOpen>
      <Collapsible.Trigger className="group">
        <Stack direction="row" spacing={1} alignItems="center" sx={{ color: "text.primary" }}>
          <KeyboardArrowRightIcon fontSize="small" className="group-data-panel-open:rotate-90 transition-transform duration-75" />
          <Typography variant="body2" color="text.primary" fontWeight={700}>
            Error
          </Typography>
        </Stack>
      </Collapsible.Trigger>
      <Collapsible.Panel>
        <Alert severity="error" variant="outlined" sx={{ "& .MuiAlert-message": { width: "100%", overflow: "hidden" } }}>
          <AlertTitle sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
            <Typography component="span" variant="subtitle2" fontWeight={700}>
              {titleText}
            </Typography>
            <Chip label={code} size="small" color="error" variant="outlined" sx={{ fontFamily: "monospace", fontSize: 10 }} />
          </AlertTitle>
          {messageIsJsonObject ? (
            <Highlight code={JSON.stringify(parsedMessage, null, 2)} language="json" unwrapped />
          ) : (
            <Typography
              variant="body2"
              sx={{
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                fontFamily: "monospace",
                fontSize: 12,
              }}
            >
              {message}
            </Typography>
          )}
          {stacktrace && (
            <Box sx={{ mt: 1.5 }}>
              <Collapsible.Root render={<Stack direction="column" spacing={1} />}>
                <Collapsible.Trigger className="group">
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ color: "text.primary" }}>
                    <KeyboardArrowRightIcon fontSize="small" className="group-data-panel-open:rotate-90 transition-transform duration-75" />
                    <Typography variant="caption" color="text.primary" fontWeight={700}>
                      Stacktrace
                    </Typography>
                  </Stack>
                </Collapsible.Trigger>
                <Collapsible.Panel>
                  <Highlight code={stacktrace} language="none" />
                </Collapsible.Panel>
              </Collapsible.Root>
            </Box>
          )}
        </Alert>
      </Collapsible.Panel>
    </Collapsible.Root>
  );
};
