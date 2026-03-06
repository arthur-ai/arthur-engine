import { CreateExperimentModalFormValues } from "../form";

import { CreatePromptExperimentRequest, EvalVariableMappingInput, PromptExperimentDetail } from "@/lib/api-client/api-client";

export function templateToFormData(template: PromptExperimentDetail): CreateExperimentModalFormValues {
  return {
    section: "info",
    info: {
      name: `${template.name} (Copy)`,
      description: template.description || "",
      prompt: {
        name: "",
        versions: [],
      },
      dataset: {
        id: template.dataset_ref.id,
        version: template.dataset_ref.version,
      },
      evaluators: template.eval_list.map((e) => ({
        name: e.name,
        version: e.version,
      })),
    },
    promptVariableMappings: [],
    evalVariableMappings: [],
  };
}

export function formDataToRequest(formData: CreateExperimentModalFormValues): CreatePromptExperimentRequest {
  return {
    dataset_ref: {
      id: formData.info.dataset.id!,
      version: formData.info.dataset.version!,
    },
    name: formData.info.name,
    description: formData.info.description,
    dataset_row_filter: [],
    prompt_configs: formData.info.prompt.versions.map((version) => ({
      type: "saved",
      name: formData.info.prompt.name,
      version,
    })),
    prompt_variable_mapping: formData.promptVariableMappings.map((mapping) => ({
      variable_name: mapping.source,
      source: {
        type: "dataset_column",
        dataset_column: { name: mapping.target },
      },
    })),
    eval_list: formData.evalVariableMappings.map((mapping) => ({
      name: mapping.name,
      version: mapping.version,
      variable_mapping: mapping.variables.map(mapVariableMapping),
    })),
  };
}

type VariableMapping = CreateExperimentModalFormValues["evalVariableMappings"][number]["variables"][number];

function mapVariableMapping(mapping: VariableMapping): EvalVariableMappingInput {
  if (mapping.sourceType === "dataset_column") {
    return {
      variable_name: mapping.name,
      source: {
        type: "dataset_column",
        dataset_column: { name: mapping.source },
      },
    };
  }

  return {
    variable_name: mapping.name,
    source: {
      type: "experiment_output",
      experiment_output: { json_path: null },
    },
  };
}
