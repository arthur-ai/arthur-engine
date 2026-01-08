import { formOptions } from "@tanstack/react-form";

import { AgenticEvalRefInput, HttpHeader, TemplateVariableMappingInput } from "@/lib/api-client/api-client";

export const newAgentExperimentFormOpts = formOptions({
  defaultValues: {
    endpoint: {
      name: "",
      url: "",
      headers: [] as HttpHeader[],
      body: "",
    },
    name: "",
    description: "",
    datasetRef: {
      id: null as string | null,
      version: null as number | null,
    },
    evals: [] as AgenticEvalRefInput[],
    templateVariableMapping: [] as TemplateVariableMappingInput[],
  },
});

export type NewAgentExperimentFormData = typeof newAgentExperimentFormOpts.defaultValues;
