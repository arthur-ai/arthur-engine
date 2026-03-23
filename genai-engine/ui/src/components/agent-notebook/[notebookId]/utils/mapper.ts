import { AgentNotebookStateFormData, agentNotebookStateFormOpts } from "../form";

import { AgenticNotebookStateResponse, CreateAgenticExperimentRequest, SetAgenticNotebookStateRequest } from "@/lib/api-client/api-client";

export const mapFormToRequest = (form: AgentNotebookStateFormData): SetAgenticNotebookStateRequest => {
  return {
    state: {
      http_template: {
        endpoint_name: form.endpoint.name,
        endpoint_url: form.endpoint.url,
        headers: form.endpoint.headers,
        request_body: form.endpoint.body,
      },
      dataset_ref: {
        id: form.datasetRef.id!,
        version: form.datasetRef.version!,
      },
      dataset_row_filter: form.datasetRowFilter,
      template_variable_mapping: form.templateVariableMapping,
      eval_list: form.evals,
    },
  };
};

export const mapTemplateToForm = (template?: AgenticNotebookStateResponse): AgentNotebookStateFormData => {
  if (!template) {
    return agentNotebookStateFormOpts.defaultValues;
  }

  return {
    endpoint: {
      name: template.http_template?.endpoint_name ?? "",
      url: template.http_template?.endpoint_url ?? "",
      headers: template.http_template?.headers ?? [],
      body: template.http_template?.request_body ?? "",
    },
    datasetRef: {
      id: template.dataset_ref?.id ?? "",
      version: template.dataset_ref?.version ?? 0,
    },
    datasetRowFilter: template.dataset_row_filter ?? [],
    templateVariableMapping: template.template_variable_mapping ?? [],
    evals: template.eval_list ?? [],
    requestTimeParameters: [],
  };
};

export const mapFormToCreateAgenticExperimentRequest = (form: AgentNotebookStateFormData) => {
  return {
    dataset_ref: {
      id: form.datasetRef.id!,
      version: form.datasetRef.version!,
    },
    eval_list: form.evals,
    http_template: {
      endpoint_name: form.endpoint.name,
      endpoint_url: form.endpoint.url,
      headers: form.endpoint.headers,
      request_body: form.endpoint.body,
    },
    template_variable_mapping: form.templateVariableMapping,
    request_time_parameters: form.requestTimeParameters,
  } as CreateAgenticExperimentRequest;
};
