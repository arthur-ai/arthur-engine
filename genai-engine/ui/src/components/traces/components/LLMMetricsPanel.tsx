import { Collapsible } from "@base-ui-components/react/collapsible";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { Box, Chip, Divider, Paper, Stack, Typography } from "@mui/material";
import { z } from "zod";

import type {
  MetricResultResponse,
  NestedSpanWithMetricsResponse,
} from "@/lib/api-client/api-client";

const RelevanceBlock = z.object({
  bert_f_score: z.number().nullable().optional(),
  reranker_relevance_score: z.number().nullable().optional(),
  llm_relevance_score: z.number().nullable().optional(),
  reason: z.string().nullable().optional(),
  refinement: z.string().nullable().optional(),
});

const ToolSelectionBlock = z.object({
  tool_selection: z.number().nullable().optional(),
  tool_selection_reason: z.string().nullable().optional(),
  tool_usage: z.number().nullable().optional(),
  tool_usage_reason: z.string().nullable().optional(),
});

const MetricDetailsSchema = z.object({
  query_relevance: RelevanceBlock.nullable().optional(),
  response_relevance: RelevanceBlock.nullable().optional(),
  tool_selection: ToolSelectionBlock.nullable().optional(),
});

export type MetricDetails = z.infer<typeof MetricDetailsSchema>;

type Props = {
  span: NestedSpanWithMetricsResponse;
};

export const LLMMetricsPanel = ({ span }: Props) => {
  const results = span.metric_results ?? [];

  if (!results.length) {
    return (
      <Paper variant="outlined">
        <Box p={1}>
          <Typography variant="body2" color="text.secondary">
            No metrics recorded for this span
          </Typography>
        </Box>
      </Paper>
    );
  }

  return (
    <Stack direction="column" spacing={1}>
      {results.map((r) => (
        <MetricCard key={r.id} result={r} />
      ))}
    </Stack>
  );
};

function safeParseDetails(details?: string | null): MetricDetails | null {
  if (!details) return null;
  try {
    const parsed = JSON.parse(details);
    const res = MetricDetailsSchema.safeParse(parsed);
    return res.success ? res.data : null;
  } catch {
    return null;
  }
}

function formatNumber(value: number | null | undefined, fractionDigits = 3) {
  if (value === null || value === undefined) return "N/A";
  return value.toFixed(fractionDigits);
}

function KV({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <Stack direction="row" alignItems="baseline" spacing={1}>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ minWidth: 160 }}
      >
        {label}
      </Typography>
      <Typography variant="body2" color="text.primary">
        {value}
      </Typography>
    </Stack>
  );
}

function renderQueryRelevance(details: MetricDetails) {
  const d = details.query_relevance ?? null;
  return (
    <Stack direction="column" spacing={1}>
      <KV
        label="LLM relevance score"
        value={formatNumber(d?.llm_relevance_score)}
      />
      <KV
        label="Reranker relevance score"
        value={formatNumber(d?.reranker_relevance_score)}
      />
      <KV label="BERT F-score" value={formatNumber(d?.bert_f_score)} />
      {d?.reason ? <KV label="Reason" value={d.reason} /> : null}
      {d?.refinement ? <KV label="Refinement" value={d.refinement} /> : null}
    </Stack>
  );
}

function renderResponseRelevance(details: MetricDetails) {
  const d = details.response_relevance ?? null;
  return (
    <Stack direction="column" spacing={1}>
      <KV
        label="LLM relevance score"
        value={formatNumber(d?.llm_relevance_score)}
      />
      <KV
        label="Reranker relevance score"
        value={formatNumber(d?.reranker_relevance_score)}
      />
      <KV label="BERT F-score" value={formatNumber(d?.bert_f_score)} />
      {d?.reason ? <KV label="Reason" value={d.reason} /> : null}
      {d?.refinement ? <KV label="Refinement" value={d.refinement} /> : null}
    </Stack>
  );
}

function renderToolSelection(details: MetricDetails) {
  const d = details.tool_selection ?? null;
  return (
    <Stack direction="column" spacing={1}>
      <KV label="Tool selection" value={formatNumber(d?.tool_selection, 2)} />
      {d?.tool_selection_reason ? (
        <KV label="Tool selection reason" value={d.tool_selection_reason} />
      ) : null}
      <KV label="Tool usage" value={formatNumber(d?.tool_usage, 2)} />
      {d?.tool_usage_reason ? (
        <KV label="Tool usage reason" value={d.tool_usage_reason} />
      ) : null}
    </Stack>
  );
}

function MetricCard({ result }: { result: MetricResultResponse }) {
  const parsed = safeParseDetails(result.details);
  if (!parsed) return null;

  let content: React.ReactNode = null;
  if (result.metric_type === "QueryRelevance") {
    content = renderQueryRelevance(parsed);
  } else if (result.metric_type === "ResponseRelevance") {
    content = renderResponseRelevance(parsed);
  } else if (result.metric_type === "ToolSelection") {
    content = renderToolSelection(parsed);
  }

  return (
    <Collapsible.Root
      defaultOpen
      render={
        <Paper
          variant="outlined"
          sx={{ display: "flex", flexDirection: "column", fontSize: "12px" }}
        />
      }
    >
      <Collapsible.Trigger className="group w-full flex flex-row">
        <Stack
          direction="row"
          gap={1}
          alignItems="center"
          p={1}
          sx={{ borderColor: "divider" }}
          className="group-data-panel-open:border-b w-full flex-1"
        >
          <KeyboardArrowRightIcon
            fontSize="small"
            className="group-data-panel-open:rotate-90 transition-transform duration-75"
          />
          <Chip size="small" label={result.metric_type} variant="outlined" />
          <Stack
            direction="row"
            gap={1.5}
            alignItems="center"
            className="ml-auto"
          >
            <Stack direction="row" spacing={0.5} alignItems="center">
              <AccessTimeIcon fontSize="inherit" sx={{ fontSize: 16 }} />
              <Typography variant="caption" color="text.secondary">
                {result.latency_ms}ms
              </Typography>
            </Stack>
            <Divider orientation="vertical" flexItem />
            <Typography variant="caption" color="text.secondary">
              ∑ {result.prompt_tokens + result.completion_tokens}
            </Typography>
          </Stack>
        </Stack>
      </Collapsible.Trigger>
      <Collapsible.Panel>
        <Box p={1}>
          {content ?? (
            <Typography variant="body2">No details available</Typography>
          )}
        </Box>
      </Collapsible.Panel>
    </Collapsible.Root>
  );
}
