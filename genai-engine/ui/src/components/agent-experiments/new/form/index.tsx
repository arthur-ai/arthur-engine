import { formOptions } from "@tanstack/react-form";

import {
  AgenticEvalRefInput,
  HttpHeader,
  NewDatasetVersionRowColumnItemRequest,
  RequestTimeParameter,
  TemplateVariableMappingInput,
} from "@/lib/api-client/api-client";

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
    datasetRowFilter: [] as NewDatasetVersionRowColumnItemRequest[],
    requestTimeParameters: [] as RequestTimeParameter[],
  },
});

export type NewAgentExperimentFormData = typeof newAgentExperimentFormOpts.defaultValues;
