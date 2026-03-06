import { CreateExperimentModalFormValues } from "../form";

import { CreatePromptExperimentRequest, EvalVariableMappingInput, PromptExperimentDetail } from "@/lib/api-client/api-client";

export function templateToFormData(template: PromptExperimentDetail): CreateExperimentModalFormValues {
  // Take the first saved prompt
  const { name } = template.prompt_configs.filter((p) => p.type === "saved").at(0) ?? {};

  // If there is a saved prompt, get the versions of that prompt
  const promptVersions = name
    ? template.prompt_configs
        .filter((p) => p.type === "saved")
        .filter((p) => p.name === name)
        .map((p) => p.version)
    : [];

  return {
    section: "info",
    info: {
      name: `${template.name} (Copy)`,
      description: template.description || "",
      prompt: {
        name: name ?? "",
        versions: promptVersions,
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
    promptVariableMappings: name
      ? template.prompt_variable_mapping.map((p) => ({
          target: p.variable_name,
          source: p.source.dataset_column.name,
        }))
      : [],
    evalVariableMappings: template.eval_list.map((e) => ({
      name: e.name,
      version: e.version,
      variables: e.variable_mapping.map(mapApiVariableMapping),
    })),
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
      variable_name: mapping.target,
      source: {
        type: "dataset_column",
        dataset_column: { name: mapping.source },
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

function mapApiVariableMapping(mapping: EvalVariableMappingInput): VariableMapping {
  if (mapping.source.type === "dataset_column") {
    return {
      name: mapping.variable_name,
      sourceType: "dataset_column",
      source: mapping.source.dataset_column.name,
    };
  }

  return {
    name: mapping.variable_name,
    sourceType: "experiment_output",
    source: "",
  };
}
