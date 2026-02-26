import { Collapsible } from "@base-ui/react/collapsible";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { Box, Chip, DialogContent, Paper, Stack, Typography } from "@mui/material";

import { StatusBadge } from "@/components/agent-experiments/components/status-badge";
import { CopyableChip } from "@/components/common";
import { Highlight } from "@/components/common/Highlight";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import type { AgenticTestCase, EvalExecution, InputVariable } from "@/lib/api-client/api-client";
import { formatCurrency } from "@/utils/formatters";
import { tryFormatJson } from "@/utils/llm";

type Props = {
  testCase: AgenticTestCase;
};

export const TestCaseDetails = ({ testCase }: Props) => {
  const { defaultCurrency } = useDisplaySettings();
  const { status, dataset_row_id, total_cost, template_input_variables, agentic_result } = testCase;
  const { request_url, request_headers, request_body, output, evals } = agentic_result;

  return (
    <DialogContent dividers className="space-y-6">
      <HeaderSection status={status} totalCost={total_cost} datasetRowId={dataset_row_id} defaultCurrency={defaultCurrency} />

      {template_input_variables.length > 0 && <InputVariablesSection variables={template_input_variables} />}

      <RequestSection url={request_url} headers={request_headers} body={request_body} />

      <ResponseSection output={output} />

      {evals.length > 0 && <EvaluationsSection evals={evals} />}
    </DialogContent>
  );
};

const HeaderSection = ({
  status,
  totalCost,
  datasetRowId,
  defaultCurrency,
}: {
  status: AgenticTestCase["status"];
  totalCost: string | null | undefined;
  datasetRowId: string;
  defaultCurrency: string;
}) => (
  <Stack direction="column" gap={2}>
    <Stack direction="row" gap={3} alignItems="center" flexWrap="wrap">
      <Stack direction="row" gap={1} alignItems="center">
        <Typography variant="body2" color="text.secondary">
          Status:
        </Typography>
        <StatusBadge status={status} />
      </Stack>

      <Stack direction="row" gap={1} alignItems="center">
        <Typography variant="body2" color="text.secondary">
          Total Cost:
        </Typography>
        <Typography variant="body2" fontWeight={600}>
          {totalCost ? formatCurrency(parseFloat(totalCost), defaultCurrency) : "N/A"}
        </Typography>
      </Stack>
    </Stack>

    <Stack direction="row" gap={1} alignItems="center">
      <Typography variant="body2" color="text.secondary">
        Dataset Row ID:
      </Typography>
      <CopyableChip label={datasetRowId} />
    </Stack>
  </Stack>
);

const InputVariablesSection = ({ variables }: { variables: InputVariable[] }) => (
  <Stack direction="column" gap={2}>
    <SectionTitle>Input Variables</SectionTitle>
    <Box className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {variables.map((variable) => (
        <VariableTile key={variable.variable_name} name={variable.variable_name} value={variable.value} />
      ))}
    </Box>
  </Stack>
);

const VariableTile = ({ name, value }: { name: string; value: string }) => (
  <Paper component={Stack} variant="outlined" p={1} className="max-h-[200px] overflow-hidden">
    <Typography variant="caption" color="text.secondary" fontWeight={600} className="uppercase">
      {name}
    </Typography>
    <Box className="overflow-y-auto h-full">
      <Typography variant="body2" className="mt-1 whitespace-pre-wrap wrap-break-word">
        {value}
      </Typography>
    </Box>
  </Paper>
);

const RequestSection = ({ url, headers, body }: { url: string; headers: Record<string, string>; body: string }) => (
  <Stack direction="column" gap={2}>
    <SectionTitle>Request</SectionTitle>

    <Stack direction="row" gap={1} alignItems="center">
      <Typography variant="body2" color="text.secondary" fontWeight={500}>
        URL:
      </Typography>
      <CopyableChip label={url} />
    </Stack>

    <CollapsibleSection label="Headers" defaultOpen={false}>
      <Paper variant="outlined" className="p-3">
        {Object.entries(headers).length > 0 ? (
          <Stack direction="column" gap={1}>
            {Object.entries(headers).map(([key, value]) => (
              <Stack key={key} direction="row" gap={1}>
                <Typography variant="body2" fontWeight={600} color="text.secondary">
                  {key}:
                </Typography>
                <Typography variant="body2" className="break-all">
                  {value}
                </Typography>
              </Stack>
            ))}
          </Stack>
        ) : (
          <Typography variant="body2" color="text.secondary" fontStyle="italic">
            No headers
          </Typography>
        )}
      </Paper>
    </CollapsibleSection>

    <CollapsibleSection label="Body" defaultOpen>
      <Highlight code={tryFormatJson(body)} language="json" />
    </CollapsibleSection>
  </Stack>
);

const ResponseSection = ({ output }: { output: AgenticTestCase["agentic_result"]["output"] }) => {
  const statusCode = output?.status_code;
  const isSuccess = statusCode && statusCode >= 200 && statusCode < 300;

  return (
    <Stack direction="column" gap={2}>
      <SectionTitle>Response</SectionTitle>

      {output ? (
        <>
          <Stack direction="row" gap={3} alignItems="center" flexWrap="wrap">
            <Stack direction="row" gap={1} alignItems="center">
              <Typography variant="body2" color="text.secondary" fontWeight={500}>
                Status Code:
              </Typography>
              <Chip label={statusCode ?? "N/A"} size="small" color={isSuccess ? "success" : statusCode ? "error" : "default"} variant="outlined" />
            </Stack>

            {output.trace_id && (
              <Stack direction="row" gap={1} alignItems="center">
                <Typography variant="body2" color="text.secondary" fontWeight={500}>
                  Trace ID:
                </Typography>
                <CopyableChip label={output.trace_id} />
              </Stack>
            )}
          </Stack>

          <CollapsibleSection label="Response Body" defaultOpen>
            <Highlight code={tryFormatJson(output.response_body)} language="json" />
          </CollapsibleSection>
        </>
      ) : (
        <Paper variant="outlined" className="p-4">
          <Typography variant="body2" color="text.secondary" fontStyle="italic">
            No response available yet
          </Typography>
        </Paper>
      )}
    </Stack>
  );
};

const EvaluationsSection = ({ evals }: { evals: EvalExecution[] }) => (
  <Stack direction="column" gap={2}>
    <SectionTitle>Evaluations</SectionTitle>
    <Stack direction="column" gap={2}>
      {evals.map((evalItem, index) => (
        <EvalCard key={`${evalItem.eval_name}-${evalItem.eval_version}-${index}`} evalItem={evalItem} />
      ))}
    </Stack>
  </Stack>
);

const EvalCard = ({ evalItem }: { evalItem: EvalExecution }) => {
  const { defaultCurrency } = useDisplaySettings();
  const { eval_name, eval_version, eval_results, eval_input_variables } = evalItem;
  const hasResults = !!eval_results;
  const isPass = hasResults && eval_results.score === 1;

  return (
    <Paper variant="outlined" className="p-4">
      <Stack direction="column" gap={2}>
        <Stack direction="row" gap={2} alignItems="center" flexWrap="wrap">
          <Typography variant="body1" fontWeight={600}>
            {eval_name}
          </Typography>
          <Chip label={`v${eval_version}`} size="small" variant="outlined" />

          {hasResults ? (
            <>
              <Chip label={`Cost: ${formatCurrency(parseFloat(eval_results.cost), defaultCurrency)}`} size="small" variant="outlined" />
              <StatusBadge status={isPass ? "completed" : "failed"} />
            </>
          ) : (
            <StatusBadge status="running" />
          )}
        </Stack>

        {hasResults && eval_results.explanation && (
          <Paper variant="outlined" className="p-3 bg-gray-50 dark:bg-gray-800">
            <Typography variant="body2" color="text.secondary">
              <strong>Explanation:</strong> {eval_results.explanation}
            </Typography>
          </Paper>
        )}

        {eval_input_variables.length > 0 && (
          <CollapsibleSection label="Eval Input Variables" defaultOpen={false}>
            <Box className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {eval_input_variables.map((variable) => (
                <VariableTile key={variable.variable_name} name={variable.variable_name} value={variable.value} />
              ))}
            </Box>
          </CollapsibleSection>
        )}
      </Stack>
    </Paper>
  );
};

const SectionTitle = ({ children }: { children: React.ReactNode }) => (
  <Typography variant="subtitle1" fontWeight={700} color="text.primary">
    {children}
  </Typography>
);

const CollapsibleSection = ({ label, defaultOpen, children }: { label: string; defaultOpen: boolean; children: React.ReactNode }) => (
  <Collapsible.Root render={<Stack direction="column" gap={1} />} defaultOpen={defaultOpen}>
    <Collapsible.Trigger className="group cursor-pointer">
      <Stack direction="row" gap={1} alignItems="center" sx={{ color: "text.primary" }}>
        <KeyboardArrowRightIcon fontSize="small" className="group-data-panel-open:rotate-90 transition-transform duration-75" />
        <Typography variant="body2" color="text.primary" fontWeight={600}>
          {label}
        </Typography>
      </Stack>
    </Collapsible.Trigger>
    <Collapsible.Panel>{children}</Collapsible.Panel>
  </Collapsible.Root>
);
