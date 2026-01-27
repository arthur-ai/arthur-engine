import { formOptions } from "@tanstack/react-form";

import {
  AgenticEvalRefInput,
  DatasetRefInput,
  HttpHeader,
  NewDatasetVersionRowColumnItemRequest,
  TemplateVariableMappingInput,
} from "@/lib/api-client/api-client";

export const agentNotebookStateFormOpts = formOptions({
  defaultValues: {
    endpoint: {
      name: "",
      url: "",
      headers: [] as HttpHeader[],
      body: "",
    },
    datasetRef: {
      id: null as string | null,
      version: null as number | null,
    } as DatasetRefInput,
    datasetRowFilter: [] as NewDatasetVersionRowColumnItemRequest[],
    templateVariableMapping: [] as TemplateVariableMappingInput[],
    evals: [] as AgenticEvalRefInput[],
  },
});

export type AgentNotebookStateFormData = typeof agentNotebookStateFormOpts.defaultValues;
