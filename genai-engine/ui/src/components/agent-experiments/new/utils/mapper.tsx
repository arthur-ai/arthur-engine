import { newAgentExperimentFormOpts } from "../form";

import { CreateAgenticExperimentRequest } from "@/lib/api-client/api-client";

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
  };
};
