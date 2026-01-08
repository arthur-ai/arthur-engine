import { useForm } from "@tanstack/react-form";
import { useState, useMemo, useCallback, useEffect } from "react";
import { z } from "zod";

import type { RagPanel } from "../ragPanelsReducer";

import type { RagConfigSelection, EvaluatorSelection, FormValues, EvalVariableMappings } from "./types";

import { useRagSearchSettings } from "@/hooks/rag-search-settings/useRagSearchSettings";
import { useApi } from "@/hooks/useApi";
import type {
  DatasetResponse,
  DatasetVersionMetadataResponse,
  LLMGetAllMetadataResponse,
  LLMVersionResponse,
  CreateRagExperimentRequest,
  SavedRagConfigInput,
  UnsavedRagConfig,
  DatasetColumnVariableSource,
  EvalRefInput,
  RagSearchSettingConfigurationVersionResponse,
  WeaviateHybridSearchSettingsConfigurationRequest,
  WeaviateKeywordSearchSettingsConfigurationRequest,
  WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest,
} from "@/lib/api-client/api-client";

const ragConfigSchema = z.object({
  type: z.enum(["saved", "unsaved"]),
  panelId: z.string(),
  displayName: z.string(),
  setting_configuration_id: z.string().optional(),
  version: z.number().optional(),
  rag_provider_id: z.string().optional(),
  settings: z.unknown().optional(),
});

const evaluatorSchema = z.object({
  name: z.string().min(1),
  version: z.number().min(1),
});

const step1Schema = z.object({
  name: z.string().min(1, "Experiment name is required"),
  description: z.string().optional(),
  ragConfigs: z.array(ragConfigSchema).min(1, "At least one RAG configuration is required"),
  datasetId: z.string().min(1, "Dataset is required"),
  datasetVersion: z.union([z.number().min(1), z.literal("")]).refine((val) => val !== "", "Dataset version is required"),
  evaluators: z.array(evaluatorSchema).min(1, "At least one evaluator is required"),
});

const INITIAL_FORM_VALUES: FormValues = {
  name: "",
  description: "",
  ragConfigs: [],
  datasetId: "",
  datasetName: "",
  datasetVersion: "",
  evaluators: [],
  queryColumn: "",
  evalVariableMappings: [],
  datasetRowFilter: [],
};

function buildUnsavedSettings(panel: RagPanel): UnsavedRagConfig["settings"] {
  const baseSettings = {
    collection_name: panel.collection?.identifier || "",
    limit: panel.settings.limit,
    include_vector: panel.settings.includeVector,
    return_properties: panel.settings.includeMetadata ? undefined : [],
    return_metadata: ["distance", "certainty", "score", "explain_score"] as ("distance" | "certainty" | "score" | "explain_score")[],
  };

  if (panel.method === "nearText") {
    return {
      search_kind: "vector_similarity_text_search",
      ...baseSettings,
      certainty: 1 - panel.settings.distance,
    } as WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest;
  } else if (panel.method === "bm25") {
    return {
      search_kind: "keyword_search",
      ...baseSettings,
    } as WeaviateKeywordSearchSettingsConfigurationRequest;
  } else {
    return {
      search_kind: "hybrid_search",
      ...baseSettings,
      alpha: panel.settings.alpha,
      max_vector_distance: panel.settings.distance,
    } as WeaviateHybridSearchSettingsConfigurationRequest;
  }
}

export function useRagExperimentForm(taskId: string | undefined, panels: RagPanel[] = [], open: boolean) {
  const api = useApi();

  const isSavedConfigsMode = panels.length === 0;

  const form = useForm({
    defaultValues: INITIAL_FORM_VALUES,
    onSubmit: async () => {
      // Submit is handled externally
    },
  });

  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [currentEvalIndex, setCurrentEvalIndex] = useState(0);

  const [datasets, setDatasets] = useState<DatasetResponse[]>([]);
  const [datasetVersions, setDatasetVersions] = useState<DatasetVersionMetadataResponse[]>([]);
  const [datasetColumns, setDatasetColumns] = useState<string[]>([]);
  const [loadingDatasets, setLoadingDatasets] = useState(false);
  const [loadingDatasetVersions, setLoadingDatasetVersions] = useState(false);

  const [evaluators, setEvaluators] = useState<LLMGetAllMetadataResponse[]>([]);
  const [evaluatorVersions, setEvaluatorVersions] = useState<Record<string, LLMVersionResponse[]>>({});
  const [loadingEvaluators, setLoadingEvaluators] = useState(false);

  const [evalVariables, setEvalVariables] = useState<Record<string, { name: string; version: number; variables: string[] }>>({});
  const [loadingEvalDetails, setLoadingEvalDetails] = useState(false);

  const [currentEvaluatorName, setCurrentEvaluatorName] = useState<string>("");
  const [currentEvaluatorVersion, setCurrentEvaluatorVersion] = useState<number | "">("");

  const [generalError, setGeneralError] = useState<string | undefined>();

  const [selectedSavedConfigId, setSelectedSavedConfigId] = useState<string>("");
  const [selectedSavedConfigVersion, setSelectedSavedConfigVersion] = useState<number | "">("");
  const [savedConfigVersions, setSavedConfigVersions] = useState<Record<string, RagSearchSettingConfigurationVersionResponse[]>>({});
  const [loadingSavedConfigVersions, setLoadingSavedConfigVersions] = useState(false);

  const { data: savedRagConfigsData, isLoading: loadingSavedRagConfigs } = useRagSearchSettings(isSavedConfigsMode ? taskId : undefined, {
    page_size: 100,
  });
  const savedRagConfigs = useMemo(
    () => savedRagConfigsData?.rag_provider_setting_configurations ?? [],
    [savedRagConfigsData?.rag_provider_setting_configurations]
  );

  const availableRagConfigs = useMemo((): RagConfigSelection[] => {
    if (isSavedConfigsMode) {
      return [];
    }
    return panels
      .filter((panel) => panel.providerId && panel.collection)
      .map((panel): RagConfigSelection => {
        if (panel.loadedConfigId && panel.loadedVersion !== null) {
          return {
            type: "saved",
            panelId: panel.id,
            displayName: panel.loadedConfigName || `Saved Config v${panel.loadedVersion}`,
            setting_configuration_id: panel.loadedConfigId,
            version: panel.loadedVersion,
          };
        } else {
          return {
            type: "unsaved",
            panelId: panel.id,
            displayName: `${panel.collection?.identifier || "Unknown"} (${panel.method})`,
            rag_provider_id: panel.providerId,
            settings: buildUnsavedSettings(panel),
          };
        }
      });
  }, [panels, isSavedConfigsMode]);

  const loadDatasets = useCallback(async () => {
    if (!api || !taskId) return;
    try {
      setLoadingDatasets(true);
      const response = await api.api.getDatasetsApiV2TasksTaskIdDatasetsSearchGet({ taskId, page_size: 100 });
      setDatasets(response.data.datasets);
    } catch {
      // Error handled silently
    } finally {
      setLoadingDatasets(false);
    }
  }, [api, taskId]);

  const loadDatasetVersions = useCallback(
    async (datasetId: string, desiredVersion?: number) => {
      if (!api) return;
      try {
        setLoadingDatasetVersions(true);
        const response = await api.api.getDatasetVersionsApiV2DatasetsDatasetIdVersionsGet({ datasetId, page_size: 100 });
        const versions = response.data.versions;
        setDatasetVersions(versions);

        if (versions.length > 0) {
          const targetVersion = desiredVersion ?? Math.max(...versions.map((v) => v.version_number));
          form.setFieldValue("datasetVersion", targetVersion);

          const versionData = versions.find((v) => v.version_number === targetVersion);
          if (versionData) {
            setDatasetColumns(versionData.column_names);
          }
        }
      } catch {
        // Error handled silently
      } finally {
        setLoadingDatasetVersions(false);
      }
    },
    [api, form]
  );

  const loadEvaluators = useCallback(async () => {
    if (!taskId || !api) return;
    try {
      setLoadingEvaluators(true);
      const response = await api.api.getAllLlmEvalsApiV1TasksTaskIdLlmEvalsGet({ taskId, page_size: 100 });
      setEvaluators(response.data.llm_metadata);
    } catch {
      // Error handled silently
    } finally {
      setLoadingEvaluators(false);
    }
  }, [taskId, api]);

  // Load datasets and evaluators when modal opens
  useEffect(() => {
    if (open && taskId && api) {
      loadDatasets();
      loadEvaluators();
    }
  }, [open, taskId, api, loadDatasets, loadEvaluators]);

  useEffect(() => {
    if (open && !isSavedConfigsMode) {
      form.setFieldValue("ragConfigs", availableRagConfigs as FormValues["ragConfigs"]);
    }
  }, [availableRagConfigs, open, form, isSavedConfigsMode]);

  const loadEvaluatorVersions = useCallback(
    async (evalName: string) => {
      if (!taskId || !api) return;
      try {
        const response = await api.api.getAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGet({
          taskId,
          evalName,
          page_size: 100,
        });
        const versions = response.data.versions.filter((v) => !v.deleted_at);
        setEvaluatorVersions((prev) => ({ ...prev, [evalName]: versions }));

        if (versions.length > 0) {
          const maxVersion = Math.max(...versions.map((v) => v.version));
          setCurrentEvaluatorVersion(maxVersion);
        }
      } catch {
        // Error handled silently
      }
    },
    [taskId, api]
  );

  const loadSavedConfigVersions = useCallback(
    async (configId: string) => {
      if (!api) return;
      try {
        setLoadingSavedConfigVersions(true);
        const response = await api.api.getRagSearchSettingConfigurationVersionsApiV1RagSearchSettingsSettingConfigurationIdVersionsGet({
          settingConfigurationId: configId,
          page_size: 100,
        });
        const versions = response.data.rag_provider_setting_configurations;
        setSavedConfigVersions((prev) => ({ ...prev, [configId]: versions }));
        if (versions.length > 0) {
          const maxVersion = Math.max(...versions.map((v) => v.version_number));
          setSelectedSavedConfigVersion(maxVersion);
        }
      } catch {
        // Error handled silently
      } finally {
        setLoadingSavedConfigVersions(false);
      }
    },
    [api]
  );

  const handleAddSavedRagConfig = useCallback(() => {
    if (!selectedSavedConfigId || !selectedSavedConfigVersion) return;
    const config = savedRagConfigs.find((c) => c.id === selectedSavedConfigId);
    if (!config) return;

    const currentConfigs = form.getFieldValue("ragConfigs");
    const alreadyAdded = currentConfigs.some(
      (c) => c.type === "saved" && c.setting_configuration_id === selectedSavedConfigId && c.version === selectedSavedConfigVersion
    );

    if (!alreadyAdded) {
      const newConfig: RagConfigSelection = {
        type: "saved",
        panelId: `saved-${selectedSavedConfigId}-${selectedSavedConfigVersion}`,
        displayName: `${config.name} v${selectedSavedConfigVersion}`,
        setting_configuration_id: selectedSavedConfigId,
        version: selectedSavedConfigVersion as number,
      };
      form.setFieldValue("ragConfigs", [...currentConfigs, newConfig] as FormValues["ragConfigs"]);
      setSelectedSavedConfigId("");
      setSelectedSavedConfigVersion("");
    }
  }, [selectedSavedConfigId, selectedSavedConfigVersion, savedRagConfigs, form]);

  const handleRemoveRagConfig = useCallback(
    (index: number) => {
      const currentConfigs = form.getFieldValue("ragConfigs");
      form.setFieldValue("ragConfigs", currentConfigs.filter((_, i) => i !== index) as FormValues["ragConfigs"]);
    },
    [form]
  );

  const initializeDefaultMappings = useCallback(
    (evalName: string, evalVersion: number, variables: string[]) => {
      if (variables.length === 0) return;

      const currentMappings = form.getFieldValue("evalVariableMappings");
      const existingIndex = currentMappings.findIndex((m) => m.evalName === evalName && m.evalVersion === evalVersion);

      if (existingIndex >= 0) return; // Already has mappings

      const defaultMappings: EvalVariableMappings = {
        evalName,
        evalVersion,
        mappings: Object.fromEntries(variables.map((varName) => [varName, { sourceType: "experiment_output" as const, jsonPath: "" }])),
      };

      form.setFieldValue("evalVariableMappings", [...currentMappings, defaultMappings]);
    },
    [form]
  );

  const loadEvalVariablesForEvaluator = useCallback(
    async (evalName: string, evalVersion: number) => {
      if (!taskId || !api) return;
      try {
        setLoadingEvalDetails(true);
        const response = await api.api.getLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGet(evalName, String(evalVersion), taskId);
        const variables = response.data.variables || [];
        if (variables.length > 0) {
          setEvalVariables((prev) => ({
            ...prev,
            [`${evalName}-${evalVersion}`]: {
              name: evalName,
              version: evalVersion,
              variables,
            },
          }));
          // Initialize default mappings
          initializeDefaultMappings(evalName, evalVersion, variables);
        }
      } catch {
        // Error handled silently
      } finally {
        setLoadingEvalDetails(false);
      }
    },
    [taskId, api, initializeDefaultMappings]
  );

  const handleAddEvaluator = useCallback(() => {
    if (!currentEvaluatorName || !currentEvaluatorVersion) return;

    const currentEvaluators = form.getFieldValue("evaluators");
    const alreadyAdded = currentEvaluators.some((e) => e.name === currentEvaluatorName && e.version === currentEvaluatorVersion);

    if (!alreadyAdded) {
      form.setFieldValue("evaluators", [...currentEvaluators, { name: currentEvaluatorName, version: currentEvaluatorVersion as number }]);
      setCurrentEvaluatorName("");
      setCurrentEvaluatorVersion("");
    }
  }, [currentEvaluatorName, currentEvaluatorVersion, form]);

  const handleRemoveEvaluator = useCallback(
    (index: number) => {
      const currentEvaluators = form.getFieldValue("evaluators");
      form.setFieldValue(
        "evaluators",
        currentEvaluators.filter((_, i) => i !== index)
      );
    },
    [form]
  );

  const handleToggleRagConfig = useCallback(
    (config: RagConfigSelection) => {
      const currentConfigs = form.getFieldValue("ragConfigs");
      const isSelected = currentConfigs.some((c) => c.panelId === config.panelId);

      if (isSelected) {
        form.setFieldValue("ragConfigs", currentConfigs.filter((c) => c.panelId !== config.panelId) as FormValues["ragConfigs"]);
      } else {
        form.setFieldValue("ragConfigs", [...currentConfigs, config] as FormValues["ragConfigs"]);
      }
    },
    [form]
  );

  const validateStep1 = useCallback((): boolean => {
    const values = form.state.values;
    const result = step1Schema.safeParse(values);

    if (!result.success) {
      result.error.issues.forEach((issue) => {
        const fieldName = issue.path[0] as keyof FormValues;
        form.setFieldMeta(fieldName, (prev) => ({
          ...prev,
          errors: [issue.message],
          errorMap: { onChange: issue.message },
        }));
      });
      return false;
    }
    return true;
  }, [form]);

  const buildApiRequest = useCallback((): CreateRagExperimentRequest => {
    const values = form.state.values;

    // Use single shared query column for all RAG configs
    const queryColumnSource: DatasetColumnVariableSource = {
      type: "dataset_column",
      dataset_column: { name: values.queryColumn || "query" },
    };

    const ragConfigs: (({ type: "saved" } & SavedRagConfigInput) | ({ type: "unsaved" } & UnsavedRagConfig))[] = values.ragConfigs.map((config) => {
      if (config.type === "saved" && config.setting_configuration_id && config.version !== undefined) {
        return {
          type: "saved" as const,
          setting_configuration_id: config.setting_configuration_id,
          version: config.version,
          query_column: queryColumnSource,
        };
      } else if (config.type === "unsaved") {
        return {
          type: "unsaved" as const,
          unsaved_id: config.panelId,
          rag_provider_id: config.rag_provider_id!,
          settings: config.settings as UnsavedRagConfig["settings"],
          query_column: queryColumnSource,
        };
      }
      throw new Error(`Invalid config type: ${config.type}`);
    });

    const evalList: EvalRefInput[] = values.evaluators.map((evaluator) => {
      const evalMappings = values.evalVariableMappings.find((m) => m.evalName === evaluator.name && m.evalVersion === evaluator.version);

      const mappings = evalMappings?.mappings || {};
      const variableMapping = Object.entries(mappings).map(([variableName, mapping]) => ({
        variable_name: variableName,
        source:
          mapping.sourceType === "dataset_column"
            ? { type: "dataset_column" as const, dataset_column: { name: mapping.datasetColumn! } }
            : { type: "experiment_output" as const, experiment_output: { json_path: mapping.jsonPath || "" } },
      }));

      return { name: evaluator.name, version: evaluator.version, variable_mapping: variableMapping };
    });

    return {
      name: values.name,
      description: values.description || undefined,
      dataset_ref: { id: values.datasetId, version: values.datasetVersion as number },
      rag_configs: ragConfigs,
      eval_list: evalList,
      dataset_row_filter:
        values.datasetRowFilter.length > 0
          ? values.datasetRowFilter.map((f) => ({ column_name: f.column_name, column_value: f.column_value }))
          : undefined,
    };
  }, [form]);

  const canProceedFromStep = useCallback(
    (step: number): boolean => {
      const values = form.state.values;

      switch (step) {
        case 0: {
          const hasExperimentName = !!values.name.trim();
          const hasRagConfigs = values.ragConfigs.length > 0;
          const hasDataset = !!values.datasetId && !!values.datasetVersion;
          const hasEvaluators = values.evaluators.length > 0;
          const hasQueryColumn = !!values.queryColumn;
          return hasExperimentName && hasRagConfigs && hasDataset && hasEvaluators && hasQueryColumn;
        }
        case 1: {
          const hasMappingsAndEvaluators = !!values.evalVariableMappings && values.evaluators.length > 0;
          if (!hasMappingsAndEvaluators) return false;
          return values.evaluators.every((evaluator) => {
            const evalMappings = values.evalVariableMappings?.find((m) => m.evalName === evaluator.name && m.evalVersion === evaluator.version);
            if (!evalMappings) return false;
            const evalKey = `${evaluator.name}-${evaluator.version}`;
            const evalVars = evalVariables[evalKey]?.variables || [];
            return evalVars.every((varName) => !!evalMappings.mappings[varName]);
          });
        }
        default:
          return false;
      }
    },
    [form, evalVariables]
  );

  const canProceedFromCurrentEval = useCallback((): boolean => {
    if (currentStep !== 1) return true;

    const values = form.state.values;
    const evaluator = values.evaluators[currentEvalIndex];
    if (!evaluator) return false;

    const evalMappings = values.evalVariableMappings?.find((m) => m.evalName === evaluator.name && m.evalVersion === evaluator.version);
    if (!evalMappings) return false;

    const evalKey = `${evaluator.name}-${evaluator.version}`;
    const evalVars = evalVariables[evalKey]?.variables || [];
    return evalVars.every((varName) => !!evalMappings.mappings[varName]);
  }, [currentStep, currentEvalIndex, form, evalVariables]);

  const values = form.state.values;
  const isLastStep = currentStep === 1 && currentEvalIndex === values.evaluators.length - 1;

  const currentEvaluator: EvaluatorSelection | undefined = values.evaluators[currentEvalIndex];
  const evalKey = currentEvaluator ? `${currentEvaluator.name}-${currentEvaluator.version}` : "";
  const currentEvalVariables = evalVariables[evalKey]?.variables || [];

  const handleNext = useCallback(async () => {
    const values = form.state.values;

    if (currentStep === 0) {
      if (!validateStep1()) return;

      // Load eval variables for first evaluator before moving to step 1
      if (values.evaluators.length > 0) {
        const firstEval = values.evaluators[0];
        await loadEvalVariablesForEvaluator(firstEval.name, firstEval.version);
        setCurrentEvalIndex(0);
      }
      setCompletedSteps((prev) => new Set(prev).add(currentStep));
      setCurrentStep((prev) => prev + 1);
    } else if (currentStep === 1) {
      // Step 1 is now eval variable mappings
      const nextEvalIndex = currentEvalIndex + 1;
      if (nextEvalIndex < values.evaluators.length) {
        const nextEval = values.evaluators[nextEvalIndex];
        await loadEvalVariablesForEvaluator(nextEval.name, nextEval.version);
        setCurrentEvalIndex(nextEvalIndex);
      } else {
        setCompletedSteps((prev) => new Set(prev).add(currentStep));
      }
    }
  }, [currentStep, currentEvalIndex, form, loadEvalVariablesForEvaluator, validateStep1]);

  const handleBack = useCallback(() => {
    if (currentStep === 1 && currentEvalIndex > 0) {
      setCurrentEvalIndex((prev) => prev - 1);
    } else {
      setCurrentStep((prev) => prev - 1);
      if (currentStep === 1) {
        setCurrentEvalIndex(0);
      }
    }
  }, [currentStep, currentEvalIndex]);

  const resetForm = useCallback(() => {
    form.reset();
    setCurrentEvaluatorName("");
    setCurrentEvaluatorVersion("");
    setEvalVariables({});
    setDatasetColumns([]);
    setCurrentStep(0);
    setCurrentEvalIndex(0);
    setCompletedSteps(new Set());
    setGeneralError(undefined);
    setSelectedSavedConfigId("");
    setSelectedSavedConfigVersion("");
  }, [form]);

  return {
    // TanStack Form instance
    form,

    // Mode
    isSavedConfigsMode,

    // Step management
    currentStep,
    completedSteps,
    currentEvalIndex,
    isLastStep,
    currentEvaluator,
    currentEvalVariables,

    // Data
    datasets,
    datasetVersions,
    datasetColumns,
    evaluators,
    evaluatorVersions,
    evalVariables,
    availableRagConfigs,

    // Saved RAG configs (for saved configs mode)
    savedRagConfigs,
    savedConfigVersions,
    loadingSavedRagConfigs,
    loadingSavedConfigVersions,
    selectedSavedConfigId,
    setSelectedSavedConfigId,
    selectedSavedConfigVersion,
    setSelectedSavedConfigVersion,

    // Loading states
    loadingDatasets,
    loadingDatasetVersions,
    loadingEvaluators,
    loadingEvalDetails,

    // Current evaluator selection
    currentEvaluatorName,
    setCurrentEvaluatorName,
    currentEvaluatorVersion,
    setCurrentEvaluatorVersion,

    // Error state
    generalError,
    setGeneralError,

    // Actions
    loadDatasetVersions,
    loadEvaluatorVersions,
    loadSavedConfigVersions,
    loadEvalVariablesForEvaluator,
    handleAddEvaluator,
    handleRemoveEvaluator,
    handleToggleRagConfig,
    handleAddSavedRagConfig,
    handleRemoveRagConfig,
    validate: validateStep1,
    buildApiRequest,
    canProceedFromStep,
    canProceedFromCurrentEval,
    handleNext,
    handleBack,
    resetForm,
  };
}
