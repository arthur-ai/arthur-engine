import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  CircularProgress,
  Typography,
  Stepper,
  Step,
  StepLabel,
  Snackbar,
  Alert,
} from "@mui/material";
import React, { useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";

import { EvalVariableMappingStep } from "./EvalVariableMappingStep";
import { ExperimentInfoStep } from "./ExperimentInfoStep";
import type { CreateRagExperimentModalProps } from "./types";
import { useRagExperimentForm } from "./useRagExperimentForm";

import { useApi } from "@/hooks/useApi";
import useSnackbar from "@/hooks/useSnackbar";
import { getApiErrorMessage } from "@/utils/errorUtils";

const STEP_LABELS = ["Experiment Info", "Configure Evals"];

export const CreateRagExperimentModal: React.FC<CreateRagExperimentModalProps> = ({
  open,
  onClose,
  onSubmit,
  panels = [],
  disableNavigation = false,
}) => {
  const { id: taskId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const api = useApi();
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();

  const [isSubmitting, setIsSubmitting] = useState(false);

  // Evaluator instructions modal state
  const [instructionsModalOpen, setInstructionsModalOpen] = useState(false);
  const [selectedEvalInstructions, setSelectedEvalInstructions] = useState<{
    name: string;
    version: number;
    instructions: string;
  } | null>(null);
  const [loadingInstructions, setLoadingInstructions] = useState(false);

  const formHook = useRagExperimentForm(taskId, panels, open);

  const loadEvaluatorInstructions = useCallback(
    async (evalName: string, evalVersion: number) => {
      if (!taskId || !api) return;
      try {
        setLoadingInstructions(true);
        const response = await api.api.getLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGet(evalName, String(evalVersion), taskId);
        setSelectedEvalInstructions({
          name: evalName,
          version: evalVersion,
          instructions: response.data.instructions || "",
        });
        setInstructionsModalOpen(true);
      } catch {
        // Error handled silently
      } finally {
        setLoadingInstructions(false);
      }
    },
    [taskId, api]
  );

  const handleSubmit = async () => {
    if (!formHook.validate()) return;

    try {
      setIsSubmitting(true);
      const request = formHook.buildApiRequest();
      const result = await onSubmit(request);

      const experimentName = formHook.form.getFieldValue("name");
      showSnackbar(`Experiment "${experimentName}" created successfully!`, "success");

      formHook.resetForm();
      onClose();

      if (!disableNavigation && taskId) {
        navigate(`/tasks/${taskId}/rag-experiments/${result.id}`);
      }
    } catch (error) {
      const errorMessage = getApiErrorMessage(error, "Failed to create experiment. Please try again.");
      formHook.setGeneralError(errorMessage);
      showSnackbar(errorMessage, "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    formHook.resetForm();
    onClose();
  };

  const renderStepContent = () => {
    if (formHook.currentStep === 0) {
      return (
        <ExperimentInfoStep
          form={formHook.form}
          isSavedConfigsMode={formHook.isSavedConfigsMode}
          availableRagConfigs={formHook.availableRagConfigs}
          // Saved configs mode props
          savedRagConfigs={formHook.savedRagConfigs}
          savedConfigVersions={formHook.savedConfigVersions}
          loadingSavedRagConfigs={formHook.loadingSavedRagConfigs}
          loadingSavedConfigVersions={formHook.loadingSavedConfigVersions}
          selectedSavedConfigId={formHook.selectedSavedConfigId}
          setSelectedSavedConfigId={formHook.setSelectedSavedConfigId}
          selectedSavedConfigVersion={formHook.selectedSavedConfigVersion}
          setSelectedSavedConfigVersion={formHook.setSelectedSavedConfigVersion}
          onLoadSavedConfigVersions={formHook.loadSavedConfigVersions}
          onAddSavedRagConfig={formHook.handleAddSavedRagConfig}
          onRemoveRagConfig={formHook.handleRemoveRagConfig}
          // Common props
          datasets={formHook.datasets}
          datasetVersions={formHook.datasetVersions}
          datasetColumns={formHook.datasetColumns}
          evaluators={formHook.evaluators}
          evaluatorVersions={formHook.evaluatorVersions}
          loadingDatasets={formHook.loadingDatasets}
          loadingDatasetVersions={formHook.loadingDatasetVersions}
          loadingEvaluators={formHook.loadingEvaluators}
          currentEvaluatorName={formHook.currentEvaluatorName}
          setCurrentEvaluatorName={formHook.setCurrentEvaluatorName}
          currentEvaluatorVersion={formHook.currentEvaluatorVersion}
          setCurrentEvaluatorVersion={formHook.setCurrentEvaluatorVersion}
          onDatasetSelect={formHook.loadDatasetVersions}
          onEvaluatorNameSelect={formHook.loadEvaluatorVersions}
          onAddEvaluator={formHook.handleAddEvaluator}
          onRemoveEvaluator={formHook.handleRemoveEvaluator}
          onToggleRagConfig={formHook.handleToggleRagConfig}
        />
      );
    } else if (formHook.currentStep === 1 && formHook.currentEvaluator) {
      return (
        <EvalVariableMappingStep
          form={formHook.form}
          evaluator={formHook.currentEvaluator}
          evalIndex={formHook.currentEvalIndex}
          totalEvaluators={formHook.form.getFieldValue("evaluators").length}
          variables={formHook.currentEvalVariables}
          datasetColumns={formHook.datasetColumns}
          loadingEvalDetails={formHook.loadingEvalDetails}
          loadingInstructions={loadingInstructions}
          onViewInstructions={() => loadEvaluatorInstructions(formHook.currentEvaluator!.name, formHook.currentEvaluator!.version)}
        />
      );
    }
    return null;
  };

  return (
    <>
      <Dialog open={open} onClose={handleCancel} maxWidth="md" fullWidth aria-labelledby="create-rag-experiment-dialog-title">
        <DialogTitle id="create-rag-experiment-dialog-title">Create RAG Experiment</DialogTitle>
        <DialogContent>
          {formHook.generalError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => formHook.setGeneralError(undefined)}>
              {formHook.generalError}
            </Alert>
          )}
          <Box className="mb-4">
            <Stepper activeStep={formHook.currentStep} alternativeLabel>
              {STEP_LABELS.map((label, index) => (
                <Step key={label} completed={formHook.completedSteps.has(index)}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>
          </Box>
          {renderStepContent()}
        </DialogContent>
        <DialogActions className="px-6 pb-4">
          <Button onClick={handleCancel} disabled={isSubmitting}>
            Cancel
          </Button>

          {formHook.currentStep > 0 && (
            <Button onClick={formHook.handleBack} disabled={isSubmitting}>
              Back
            </Button>
          )}

          <formHook.form.Subscribe selector={(state) => state.values}>
            {() =>
              formHook.isLastStep ? (
                <Button variant="contained" onClick={handleSubmit} disabled={isSubmitting || !formHook.canProceedFromCurrentEval()}>
                  {isSubmitting ? <CircularProgress size={20} /> : "Create Experiment"}
                </Button>
              ) : (
                <Button
                  variant="contained"
                  onClick={formHook.handleNext}
                  disabled={
                    (formHook.currentStep === 0 && !formHook.canProceedFromStep(0)) ||
                    (formHook.currentStep === 1 && !formHook.canProceedFromCurrentEval())
                  }
                >
                  Next
                </Button>
              )
            }
          </formHook.form.Subscribe>
        </DialogActions>
      </Dialog>

      <Dialog open={instructionsModalOpen} onClose={() => setInstructionsModalOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {selectedEvalInstructions?.name} v{selectedEvalInstructions?.version} - Instructions
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" sx={{ whiteSpace: "pre-wrap" }}>
            {selectedEvalInstructions?.instructions || "No instructions available."}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInstructionsModalOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>
    </>
  );
};
