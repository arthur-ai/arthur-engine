import { NewAgentExperimentFormData, newAgentExperimentFormOpts } from "../form";

import { AgenticExperimentDetail, CreateAgenticExperimentRequest } from "@/lib/api-client/api-client";

type FormData = typeof newAgentExperimentFormOpts.defaultValues;

export const mapFormToRequest = (form: FormData): CreateAgenticExperimentRequest => {
  return {
    name: form.name,
    description: form.description,
    dataset_ref: {
      id: form.datasetRef.id!,
      version: form.datasetRef.version!,
    },
    http_template: {
      endpoint_name: form.endpoint.name,
      endpoint_url: form.endpoint.url,
      headers: form.endpoint.headers,
      request_body: JSON.parse(form.endpoint.body),
    },
    eval_list: form.evals.map((e) => ({
      name: e.name,
      version: e.version,
      transform_id: e.transform_id,
      variable_mapping: e.variable_mapping,
    })),
    template_variable_mapping: form.templateVariableMapping,
    dataset_row_filter: form.datasetRowFilter,
    request_time_parameters: form.requestTimeParameters,
  };
};

export const mapTemplateToRequest = (template?: AgenticExperimentDetail): NewAgentExperimentFormData => {
  if (!template) {
    return newAgentExperimentFormOpts.defaultValues;
  }

  return {
    ...newAgentExperimentFormOpts.defaultValues,
    endpoint: {
      name: template.http_template.endpoint_name,
      url: template.http_template.endpoint_url,
      headers: template.http_template.headers ?? [],
      body: JSON.stringify(template.http_template.request_body),
    },
    datasetRef: {
      id: template.dataset_ref.id,
      version: template.dataset_ref.version,
    },
    evals: template.eval_list.map((e) => ({
      name: e.name,
      version: e.version,
      transform_id: e.transform_id,
      variable_mapping: e.variable_mapping,
    })),
    templateVariableMapping: template.template_variable_mapping,
    name: template.name,
    description: template.description ?? "",
    datasetRowFilter: template.dataset_row_filter ?? [],
  };
};
