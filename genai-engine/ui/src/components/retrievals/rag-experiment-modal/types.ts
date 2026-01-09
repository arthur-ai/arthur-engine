import type { RagPanel } from "../ragPanelsReducer";

import type {
  CreateRagExperimentRequest,
  NewDatasetVersionRowColumnItemRequest,
  UnsavedRagConfig,
  SavedRagConfigInput,
} from "@/lib/api-client/api-client";

interface RagConfigUIFields {
  panelId: string;
  displayName: string;
}
export type SavedRagConfigSelection = {
  type: "saved";
} & RagConfigUIFields &
  Pick<SavedRagConfigInput, "setting_configuration_id" | "version">;

export type UnsavedRagConfigSelection = {
  type: "unsaved";
} & RagConfigUIFields &
  Pick<UnsavedRagConfig, "rag_provider_id" | "settings">;

export type RagConfigSelection = SavedRagConfigSelection | UnsavedRagConfigSelection;

export interface EvaluatorSelection {
  name: string;
  version: number;
}

export type VariableSourceType = "dataset_column" | "experiment_output";

export interface EvalVariableMappings {
  evalName: string;
  evalVersion: number;
  mappings: {
    [variableName: string]: {
      sourceType: VariableSourceType;
      datasetColumn?: string;
      jsonPath?: string;
    };
  };
}

export type DatasetRowFilter = NewDatasetVersionRowColumnItemRequest;

export interface RagExperimentFormData {
  name: string;
  description: string;
  ragConfigs: RagConfigSelection[];
  datasetId: string;
  datasetName: string;
  datasetVersion: number | "";
  evaluators: EvaluatorSelection[];
  queryColumn: string;
  evalVariableMappings: EvalVariableMappings[];
  datasetRowFilter: DatasetRowFilter[];
}

// Form values type matches RagExperimentFormData
export type FormValues = RagExperimentFormData;

export interface CreateRagExperimentModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (request: CreateRagExperimentRequest) => Promise<{ id: string }>;
  /** RAG panels from the experiment page UI. If empty/undefined, saved RAG configs will be loaded from the API */
  panels?: RagPanel[];
  disableNavigation?: boolean;
}

export type FormErrors = Partial<Record<keyof RagExperimentFormData | "general", string>>;
