import { useStore } from "@tanstack/react-form";
import { useEffect, useRef } from "react";

import { agentNotebookStateFormOpts } from "../form";

import { extractVariablesFromText } from "@/components/agent-experiments/hooks/useExtractVariables";
import { withForm } from "@/components/traces/components/filtering/hooks/form";
import { HttpHeader, TemplateVariableMappingInput } from "@/lib/api-client/api-client";

function computeVars(endpoint: { body: string; headers: HttpHeader[] }): string[] {
  const bodyVars = extractVariablesFromText(endpoint.body);

  const headerVars = endpoint.headers.flatMap((h) => [...extractVariablesFromText(h.name), ...extractVariablesFromText(h.value)]);

  return Array.from(new Set([...bodyVars, ...headerVars])).sort();
}

function varsSignature(vars: string[]) {
  return vars.join("|"); // vars already sorted
}

function rebuildMapping(vars: string[], prev: TemplateVariableMappingInput[] | undefined): TemplateVariableMappingInput[] {
  const byVar = new Map((prev ?? []).map((r) => [r.variable_name, r]));
  return vars.map((v) => byVar.get(v) ?? { variable_name: v, source: { type: "dataset_column", dataset_column: { name: "" } } });
}

export const BodyVariableExtractor = withForm({
  ...agentNotebookStateFormOpts,
  render: function Render({ form }) {
    const lastSignature = useRef<string | null>(null);
    const endpoint = useStore(form.store, (state) => state.values.endpoint);

    useEffect(() => {
      const vars = computeVars(endpoint);
      const sig = varsSignature(vars);

      if (sig === lastSignature.current) return;
      lastSignature.current = sig;

      const prev = form.getFieldValue("templateVariableMapping") as TemplateVariableMappingInput[] | undefined;
      const next = rebuildMapping(vars, prev);

      form.setFieldValue("templateVariableMapping", next);
    }, [endpoint, form]);

    return null;
  },
});
