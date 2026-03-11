import { Collapsible } from "@base-ui/react/collapsible";
import ConstructionIcon from "@mui/icons-material/Construction";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { Alert, IconButton, Link, Paper, Snackbar, Stack, Typography } from "@mui/material";

import { TracesEmptyState } from "../TracesEmptyState";

import { Highlight } from "@/components/common/Highlight";
import { useCopy } from "@/hooks/useCopy";
import useSnackbar from "@/hooks/useSnackbar";
import { NestedSpanWithMetricsResponse } from "@/lib/api";
import { getToolDefinition, getTools, tryFormatJson } from "@/utils/llm";

type Props = {
  span: NestedSpanWithMetricsResponse;
};

export const ToolsTab = ({ span }: Props) => {
  const tools = isSpanWithLlmAttrs(span) ? getTools(span).map(getToolDefinition) : [];
  const snackbar = useSnackbar({ duration: "short" });
  const { handleCopy } = useCopy({
    onCopy: () => {
      snackbar.showSnackbar("Tool schema copied to clipboard!", "success");
    },
    onError: () => {
      snackbar.showSnackbar("Failed to copy tool schema to clipboard", "error");
    },
  });

  if (tools.length === 0) {
    return (
      <TracesEmptyState title="No tools found">
        <Typography variant="body2" color="text.secondary" textAlign="center">
          The LLM didn&apos;t have any tools available, or the tracing instrumentation is not capturing the tools the LLM has access to.
        </Typography>
        <Typography variant="body2" color="text.secondary" textAlign="center">
          To fix this, review your tracing setup and ensure it includes the tool definitions in the span attributes when instrumenting LLM calls. See
          the{" "}
          <Link href="https://docs.arthur.ai/docs/get-started-with-tracing" target="_blank" rel="noopener">
            tracing documentation
          </Link>{" "}
          for more details.
        </Typography>
      </TracesEmptyState>
    );
  }

  return (
    <>
      <Stack direction="column" spacing={1} p={1}>
        {tools.map((tool) => (
          <Collapsible.Root className="bg-blue-600! border-blue-800!" render={<Paper variant="outlined" />}>
            <Collapsible.Trigger className="group w-full flex flex-row gap-2 p-2 items-center data-panel-open:border-b border-blue-800 text-white">
              <KeyboardArrowRightIcon fontSize="small" className="group-data-panel-open:rotate-90 transition-transform duration-75" />
              <ConstructionIcon sx={{ fontSize: 16 }} />
              <Typography variant="body2" fontWeight={800}>
                {tool.name}
              </Typography>
              <IconButton
                color="inherit"
                size="small"
                sx={{ ml: "auto" }}
                onClick={(e) => {
                  e.stopPropagation();
                  handleCopy(tryFormatJson(tool));
                }}
              >
                <ContentCopyIcon sx={{ fontSize: 16 }} />
              </IconButton>
            </Collapsible.Trigger>
            <Collapsible.Panel className="p-2">
              <Highlight code={tryFormatJson(tool)} language="json" />
            </Collapsible.Panel>
          </Collapsible.Root>
        ))}
      </Stack>

      <Snackbar {...snackbar.snackbarProps}>
        <Alert {...snackbar.alertProps} />
      </Snackbar>
    </>
  );
};

type SpanWithLlmAttrs = Parameters<typeof getTools>[0];

// TODO: Export this to shared-components
export function isSpanWithLlmAttrs(span: NestedSpanWithMetricsResponse): span is NestedSpanWithMetricsResponse & SpanWithLlmAttrs {
  return "raw_data" in span && "attributes" in span.raw_data;
}
