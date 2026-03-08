import { MustacheHighlightedTextField, useAppForm, withFieldGroup } from "@arthur/shared-components";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import GpsFixedIcon from "@mui/icons-material/GpsFixed";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Divider,
  FormControlLabel,
  IconButton,
  Paper,
  Stack,
  Step,
  StepContent,
  StepLabel,
  Stepper,
  Switch,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import z from "zod";

import { VariableMappingSection } from "../components/variable-mapping";
import { useContinuousEvalVariableMapping } from "../hooks/useContinuousEvalVariableMapping";
import { useCreateContinuousEval } from "../hooks/useCreateContinuousEval";

import { EvaluatorSelector } from "./components/EvaluatorSelector";

import { useEval } from "@/components/evaluators/hooks/useEval";
import { validateTransform } from "@/components/traces/components/add-to-dataset/utils/transformBuilder";
import { useCreateTransformMutation } from "@/components/transforms/hooks/useCreateTransformMutation";
import { useTransforms } from "@/components/transforms/hooks/useTransforms";
import TransformFormModal from "@/components/transforms/TransformFormModal";
import { useTask } from "@/hooks/useTask";
import type { ContinuousEvalTransformVariableMappingRequest, NestedSpanWithMetricsResponse } from "@/lib/api-client/api-client";

type EvaluatorFormState = {
  name: string | null;
  version: string | null;
};

type TransformFormState = {
  transformId: string | null;
};

export type PickerState = {
  variableIndex: number;
  variableName: string;
} | null;

type VariableRow = {
  variable_name: string;
  span_name: string;
  attribute_path: string;
  fallback: string;
  previewValue?: string;
};

type ContinuousEvalStepperProps = {
  selectedSpan: NestedSpanWithMetricsResponse | null;
  pickerState: PickerState;
  onStartPicking: (variableIndex: number, variableName: string) => void;
  onCancelPicking: () => void;
  inlineVariables: VariableRow[];
  onSetInlineVariables: (variables: VariableRow[]) => void;
};

export const ContinuousEvalStepper = ({
  selectedSpan,
  pickerState,
  onStartPicking,
  onCancelPicking,
  inlineVariables,
  onSetInlineVariables,
}: ContinuousEvalStepperProps) => {
  const { task } = useTask();
  const navigate = useNavigate();

  const [activeStep, setActiveStep] = useState(0);
  const [transformMode, setTransformMode] = useState<"select" | "create">("create");

  const createContinuousEval = useCreateContinuousEval();

  const form = useAppForm({
    defaultValues: {
      name: "",
      description: "",
      enabled: true,
      evaluator: {
        name: null,
        version: null,
      } as EvaluatorFormState,
      transform: {
        transformId: null,
      } as TransformFormState,
      variableMappings: [] as ContinuousEvalTransformVariableMappingRequest[],
    },
    validators: {
      onMount: z.object({
        name: z.string().min(1, "Name is required"),
        description: z.string(),
        enabled: z.boolean(),
        evaluator: z.object({
          name: z.string().min(1),
          version: z.string().min(1),
        }),
        transform: z.object({
          transformId: z.string().nullable(),
        }),
        variableMappings: z.array(
          z.object({
            eval_variable: z.string(),
            transform_variable: z.string(),
          })
        ),
      }),
      onChange: z.object({
        name: z.string().min(1, "Name is required"),
        description: z.string(),
        enabled: z.boolean(),
        evaluator: z.object({
          name: z.string().min(1),
          version: z.string().min(1),
        }),
        transform: z.object({
          transformId: z.string().nullable(),
        }),
        variableMappings: z.array(
          z.object({
            eval_variable: z.string(),
            transform_variable: z.string(),
          })
        ),
      }),
    },
    onSubmit: async ({ value }) => {
      if (transformMode === "create") {
        // First create the transform, then create the continuous eval
        const validationErrors = validateInlineTransform();
        if (validationErrors.length > 0) {
          setInlineErrors(validationErrors);
          return;
        }

        const definition = {
          variables: inlineVariables.map((v) => {
            let fallbackValue = undefined;
            if (v.fallback && v.fallback.trim()) {
              const parsed = JSON.parse(v.fallback);
              fallbackValue = parsed !== null ? parsed : undefined;
            }
            return {
              variable_name: v.variable_name,
              span_name: v.span_name,
              attribute_path: v.attribute_path,
              fallback: fallbackValue,
            };
          }),
        };

        const transformData = await createTransform.mutateAsync({
          name: `${value.name}_transform`,
          description: `Auto-created transform for continuous eval "${value.name}"`,
          definition,
        });

        const { id } = await createContinuousEval.mutateAsync({
          name: value.name,
          description: value.description?.trim() || undefined,
          enabled: value.enabled,
          llm_eval_name: value.evaluator.name!,
          llm_eval_version: value.evaluator.version!,
          transform_id: transformData.id,
          transform_variable_mapping: inlineVariables.map((v) => ({
            eval_variable: v.variable_name,
            transform_variable: v.variable_name,
          })),
        });

        navigate(`/tasks/${task?.id}/continuous-evals/${id}`);
      } else {
        // Select existing transform
        const { id } = await createContinuousEval.mutateAsync({
          name: value.name,
          description: value.description?.trim() || undefined,
          enabled: value.enabled,
          llm_eval_name: value.evaluator.name!,
          llm_eval_version: value.evaluator.version!,
          transform_id: value.transform.transformId!,
          transform_variable_mapping: value.variableMappings,
        });

        navigate(`/tasks/${task?.id}/continuous-evals/${id}`);
      }
    },
  });

  const evaluator = useStore(form.store, (state) => state.values.evaluator);
  const transform = useStore(form.store, (state) => state.values.transform);

  const { eval: evaluatorData } = useEval(task?.id, evaluator.name ?? undefined, evaluator.version ?? undefined);

  const evalVariables = useMemo(() => evaluatorData?.variables ?? [], [evaluatorData]);

  // Sync inline variables with eval variables when eval changes
  useEffect(() => {
    if (transformMode === "create" && evalVariables.length > 0) {
      // Preserve existing mappings where variable name matches
      const newVariables = evalVariables.map((varName) => {
        const existing = inlineVariables.find((v) => v.variable_name === varName);
        return existing ?? { variable_name: varName, span_name: "", attribute_path: "", fallback: "", previewValue: undefined };
      });
      onSetInlineVariables(newVariables);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [evalVariables, transformMode]);

  const { data: variableMappingData, isLoading: isLoadingVariableMapping } = useContinuousEvalVariableMapping(
    task?.id,
    transform.transformId ?? undefined,
    evaluator.name ?? undefined,
    evaluator.version ?? undefined
  );

  const variableMappings = useStore(form.store, (state) => state.values.variableMappings);

  const createTransform = useCreateTransformMutation(task?.id);

  const [inlineErrors, setInlineErrors] = useState<string[]>([]);

  const handleSelectionChange = () => {
    form.setFieldValue("variableMappings", []);
  };

  const isEvaluatorSelected = !!(evaluator.name && evaluator.version);

  const validateInlineTransform = (): string[] => {
    const errors: string[] = [];
    if (inlineVariables.length === 0) {
      errors.push("At least one variable mapping is required");
      return errors;
    }
    inlineVariables.forEach((v, idx) => {
      if (!v.variable_name.trim()) errors.push(`Variable ${idx + 1}: Variable name is required`);
      if (!v.span_name.trim()) errors.push(`Variable ${idx + 1}: Span name is required`);
      if (!v.attribute_path.trim()) errors.push(`Variable ${idx + 1}: Attribute path is required`);
      if (v.fallback) {
        try {
          JSON.parse(v.fallback);
        } catch {
          errors.push(`Variable ${idx + 1}: Fallback must be valid JSON`);
        }
      }
    });
    try {
      const def = {
        variables: inlineVariables.map((v) => ({
          variable_name: v.variable_name,
          span_name: v.span_name,
          attribute_path: v.attribute_path,
          fallback: v.fallback ? JSON.parse(v.fallback) : undefined,
        })),
      };
      errors.push(...validateTransform(def));
    } catch {
      errors.push("Invalid transform definition");
    }
    return errors;
  };

  const canSubmitCreate = inlineVariables.length > 0 && inlineVariables.every((v) => v.variable_name && v.span_name && v.attribute_path);

  const allVariablesMapped =
    !variableMappingData ||
    variableMappingData.eval_variables.length === 0 ||
    variableMappingData.eval_variables.every((evalVar) => variableMappings.some((m) => m.eval_variable === evalVar && m.transform_variable));

  const canSubmitSelect = transform.transformId && allVariablesMapped;

  const handleInlineVariableChange = (index: number, field: keyof VariableRow, value: string) => {
    const newVariables = [...inlineVariables];
    newVariables[index] = { ...newVariables[index], [field]: value };
    onSetInlineVariables(newVariables);
  };

  const handleAddInlineVariable = () => {
    onSetInlineVariables([...inlineVariables, { variable_name: "", span_name: "", attribute_path: "", fallback: "" }]);
  };

  const handleRemoveInlineVariable = (index: number) => {
    onSetInlineVariables(inlineVariables.filter((_, i) => i !== index));
    if (pickerState && pickerState.variableIndex === index) {
      onCancelPicking();
    }
  };

  // For "select existing" mode - TransformFormModal
  const [openCreateTransformModal, setOpenCreateTransformModal] = useState(false);
  const transforms = useTransforms(task?.id ?? undefined);

  const createTransformFromModal = useCreateTransformMutation(task?.id, async (data) => {
    await transforms.refetch();
    setOpenCreateTransformModal(false);
    form.setFieldValue("transform.transformId", data.id);
    handleSelectionChange();
  });

  return (
    <Stack
      component="form"
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        form.handleSubmit();
      }}
      sx={{ height: "100%", overflow: "auto" }}
    >
      <Stack sx={{ p: 2 }} gap={2}>
        <Typography variant="h6" fontWeight="bold" color="text.primary">
          New Continuous Eval
        </Typography>

        <DetailsFieldGroup
          form={form}
          fields={{
            name: "name",
            description: "description",
          }}
        />

        <form.Field name="enabled">
          {(field) => (
            <FormControlLabel
              control={<Switch checked={field.state.value} onChange={(e) => field.handleChange(e.target.checked)} />}
              label="Enable continuous eval"
              slotProps={{ typography: { color: "text.primary", variant: "body2" } }}
            />
          )}
        </form.Field>

        <Divider />

        <Stepper activeStep={activeStep} orientation="vertical">
          <Step>
            <StepLabel>
              <Typography variant="subtitle1" fontWeight={600}>
                Select Evaluator
              </Typography>
            </StepLabel>
            <StepContent>
              <Stack gap={2}>
                <EvaluatorSelector taskId={task?.id ?? ""} form={form} fields="evaluator" onSelectionChange={handleSelectionChange} />

                {evaluatorData && (
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="body2" fontWeight="bold" mb={1}>
                      Instructions Preview
                    </Typography>
                    <MustacheHighlightedTextField value={evaluatorData?.instructions ?? ""} onChange={() => {}} readOnly size="small" />
                  </Paper>
                )}

                <Box>
                  <Button variant="contained" disabled={!isEvaluatorSelected} onClick={() => setActiveStep(1)}>
                    Next
                  </Button>
                </Box>
              </Stack>
            </StepContent>
          </Step>

          <Step>
            <StepLabel>
              <Typography variant="subtitle1" fontWeight={600}>
                Configure Transform
              </Typography>
            </StepLabel>
            <StepContent>
              <Stack gap={2}>
                <Tabs value={transformMode} onChange={(_, v) => setTransformMode(v as "select" | "create")} sx={{ mb: 1 }}>
                  <Tab label="Create New" value="create" />
                  <Tab label="Select Existing" value="select" />
                </Tabs>

                {transformMode === "create" ? (
                  <InlineTransformCreator
                    variables={inlineVariables}
                    onVariableChange={handleInlineVariableChange}
                    onAddVariable={handleAddInlineVariable}
                    onRemoveVariable={handleRemoveInlineVariable}
                    onStartPicking={onStartPicking}
                    onCancelPicking={onCancelPicking}
                    pickerState={pickerState}
                    errors={inlineErrors}
                    selectedSpan={selectedSpan}
                  />
                ) : (
                  <SelectExistingTransform
                    form={form}
                    transforms={transforms}
                    onSelectionChange={handleSelectionChange}
                    variableMappingData={variableMappingData}
                    isLoadingVariableMapping={isLoadingVariableMapping}
                    evaluator={evaluator}
                    onOpenCreateModal={() => setOpenCreateTransformModal(true)}
                    createTransformLoading={createTransformFromModal.isPending}
                    evalVariables={evalVariables}
                  />
                )}

                <Stack direction="row" gap={1}>
                  <Button onClick={() => setActiveStep(0)}>Back</Button>
                </Stack>
              </Stack>
            </StepContent>
          </Step>
        </Stepper>
      </Stack>

      <Box sx={{ p: 2, borderTop: 1, borderColor: "divider", mt: "auto" }}>
        <form.Subscribe selector={(state) => [state.canSubmit, state.isSubmitting]}>
          {([, isSubmitting]) => {
            const formName = form.getFieldValue("name");
            const canSubmitForm = formName && isEvaluatorSelected && activeStep === 1 && (transformMode === "create" ? canSubmitCreate : canSubmitSelect);

            return (
              <Button
                variant="contained"
                size="large"
                color="primary"
                disabled={!canSubmitForm}
                loading={isSubmitting || createTransform.isPending || createContinuousEval.isPending}
                fullWidth
                type="submit"
              >
                Create Continuous Eval
              </Button>
            );
          }}
        </form.Subscribe>
      </Box>

      <TransformFormModal
        open={openCreateTransformModal}
        onClose={() => setOpenCreateTransformModal(false)}
        onSubmit={async (name, description, definition) =>
          void createTransformFromModal.mutateAsync({ name, description, definition })
        }
        isLoading={createTransformFromModal.isPending}
        taskId={task?.id}
        initialTransform={undefined}
        initialVariableNames={evalVariables}
      />
    </Stack>
  );
};

const DetailsFieldGroup = withFieldGroup({
  defaultValues: {
    name: "",
    description: "",
  },
  render: function Render({ group }) {
    return (
      <Stack gap={2}>
        <group.AppField
          name="name"
          children={(field) => (
            <TextField
              autoFocus
              label="Eval Name"
              type="text"
              fullWidth
              variant="outlined"
              size="small"
              required
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              error={field.state.meta.errors.length > 0}
            />
          )}
        />
        <group.AppField
          name="description"
          children={(field) => (
            <TextField
              multiline
              rows={2}
              label="Description"
              type="text"
              fullWidth
              variant="outlined"
              size="small"
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              error={field.state.meta.errors.length > 0}
            />
          )}
        />
      </Stack>
    );
  },
});

type InlineTransformCreatorProps = {
  variables: VariableRow[];
  onVariableChange: (index: number, field: keyof VariableRow, value: string) => void;
  onAddVariable: () => void;
  onRemoveVariable: (index: number) => void;
  onStartPicking: (index: number, variableName: string) => void;
  onCancelPicking: () => void;
  pickerState: PickerState;
  errors: string[];
  selectedSpan: NestedSpanWithMetricsResponse | null;
};

const InlineTransformCreator = ({
  variables,
  onVariableChange,
  onAddVariable,
  onRemoveVariable,
  onStartPicking,
  onCancelPicking,
  pickerState,
  errors,
}: InlineTransformCreatorProps) => {
  return (
    <Stack gap={2}>
      {errors.length > 0 && (
        <Alert severity="error">
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {errors.map((error, idx) => (
              <li key={idx}>{error}</li>
            ))}
          </ul>
        </Alert>
      )}

      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Typography variant="subtitle2" fontWeight={600}>
          Variable Mappings
        </Typography>
        <Button startIcon={<AddIcon />} onClick={onAddVariable} size="small">
          Add Variable
        </Button>
      </Stack>

      {variables.length === 0 && (
        <Alert severity="info">Select an evaluator with variables to auto-populate variable mappings.</Alert>
      )}

      <Stack spacing={2}>
        {variables.map((variable, idx) => {
          const isPicking = pickerState?.variableIndex === idx;

          return (
            <Box
              key={idx}
              sx={{
                p: 2,
                border: "1px solid",
                borderColor: isPicking ? "primary.main" : "divider",
                borderRadius: 1,
                backgroundColor: isPicking ? "primary.50" : "action.hover",
              }}
            >
              <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1.5}>
                <Typography variant="body2" fontWeight={600}>
                  {variable.variable_name || `Variable ${idx + 1}`}
                </Typography>
                <Stack direction="row" gap={0.5}>
                  {isPicking ? (
                    <Button size="small" variant="outlined" color="primary" onClick={onCancelPicking}>
                      Cancel Selection
                    </Button>
                  ) : (
                    <Tooltip title="Click to select span and attribute from the trace">
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<GpsFixedIcon />}
                        onClick={() => onStartPicking(idx, variable.variable_name)}
                      >
                        Select in trace
                      </Button>
                    </Tooltip>
                  )}
                  <IconButton size="small" onClick={() => onRemoveVariable(idx)} disabled={variables.length === 1}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Stack>
              </Stack>

              <Stack spacing={1.5}>
                <TextField
                  label="Variable Name"
                  value={variable.variable_name}
                  onChange={(e) => onVariableChange(idx, "variable_name", e.target.value)}
                  size="small"
                  required
                  fullWidth
                />
                <TextField
                  label="Span Name"
                  value={variable.span_name}
                  onChange={(e) => onVariableChange(idx, "span_name", e.target.value)}
                  placeholder="e.g., LLMCall"
                  size="small"
                  required
                  fullWidth
                />
                <TextField
                  label="Attribute Path"
                  value={variable.attribute_path}
                  onChange={(e) => onVariableChange(idx, "attribute_path", e.target.value)}
                  placeholder="e.g., attributes.input.value"
                  size="small"
                  required
                  fullWidth
                />
                <TextField
                  label="Fallback Value (JSON, Optional)"
                  value={variable.fallback}
                  onChange={(e) => onVariableChange(idx, "fallback", e.target.value)}
                  placeholder='e.g., null or "default"'
                  size="small"
                  fullWidth
                />
                {variable.previewValue && (
                  <Paper variant="outlined" sx={{ p: 1, backgroundColor: "action.hover" }}>
                    <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
                      Preview
                    </Typography>
                    <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: "0.75rem", wordBreak: "break-all" }}>
                      {variable.previewValue.length > 200 ? variable.previewValue.slice(0, 200) + "..." : variable.previewValue}
                    </Typography>
                  </Paper>
                )}
              </Stack>
            </Box>
          );
        })}
      </Stack>
    </Stack>
  );
};

type SelectExistingTransformProps = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  form: any;
  transforms: ReturnType<typeof useTransforms>;
  onSelectionChange: () => void;
  variableMappingData: { eval_variables: string[]; transform_variables: string[]; matching_variables: string[] } | undefined;
  isLoadingVariableMapping: boolean;
  evaluator: EvaluatorFormState;
  onOpenCreateModal: () => void;
  createTransformLoading: boolean;
  evalVariables: string[];
};

const SelectExistingTransform = ({
  form,
  transforms,
  onSelectionChange,
  variableMappingData,
  isLoadingVariableMapping,
  evaluator,
  onOpenCreateModal,
  createTransformLoading,
}: SelectExistingTransformProps) => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const transform = useStore(form.store, (state: any) => state.values.transform) as TransformFormState;
  const canShowVariableMapping = evaluator.name && evaluator.version && transform.transformId;

  return (
    <Stack gap={2}>
      <Stack direction="row" gap={2} alignItems="center">
        <Typography variant="subtitle2" fontWeight={600}>
          Transform
        </Typography>
        <Button
          loading={createTransformLoading}
          variant="contained"
          disableElevation
          size="small"
          startIcon={<AddIcon />}
          type="button"
          onClick={onOpenCreateModal}
          sx={{ ml: "auto" }}
        >
          Create New
        </Button>
      </Stack>

      <form.Field
        name="transform.transformId"
        listeners={{ onChange: () => onSelectionChange() }}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        children={(field: any) => {
          const selected = transforms.data?.find((t) => t.id === field.state.value);
          return (
            <Autocomplete
              loading={transforms.isLoading}
              options={transforms.data ?? []}
              value={selected ?? null}
              onChange={(_: unknown, value: { id: string; name: string } | null) => field.handleChange(value?.id ?? "")}
              getOptionLabel={(option) => option.name}
              isOptionEqualToValue={(option, value) => option.id === value.id}
              getOptionKey={(option) => option.id}
              renderInput={(params) => <TextField {...params} label="Transform" size="small" />}
            />
          );
        }}
      />

      {canShowVariableMapping && (
        <>
          <Divider />
          <VariableMappingSection
            form={form}
            fields={{ variableMappings: "variableMappings" as never }}
            eval_variables={variableMappingData?.eval_variables ?? []}
            transform_variables={variableMappingData?.transform_variables ?? []}
            matching_variables={variableMappingData?.matching_variables ?? []}
            isLoading={isLoadingVariableMapping}
          />
        </>
      )}
    </Stack>
  );
};
