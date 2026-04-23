import { withFieldGroup } from "@arthur/shared-components";
import AddIcon from "@mui/icons-material/Add";
import { Autocomplete, Box, Button, Chip, CircularProgress, Stack, TextField, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useEffect, useState } from "react";

import CreateEvalTypeModal from "@/components/evaluators/CreateEvalTypeModal";
import EvalFormModal from "@/components/evaluators/EvalFormModal";
import { useCreateEvalMutation } from "@/components/evaluators/hooks/useCreateEvalMutation";
import { useEvals } from "@/components/evaluators/hooks/useEvals";
import { useEvalVersions } from "@/components/evaluators/hooks/useEvalVersions";
import { useCreateMlEvalMutation } from "@/components/ml-evaluators/hooks/useCreateMlEvalMutation";
import MLEvalFormModal from "@/components/ml-evaluators/MLEvalFormModal";
import { useApiQuery } from "@/hooks/useApiQuery";
import type { LLMEvalsVersionListResponse, LLMGetAllMetadataResponse } from "@/lib/api-client/api-client";
import { encodePathParam } from "@/utils/url";

type EvaluatorFormState = {
  name: string | null;
  version: string | null;
  eval_type: string | null;
};

type EvaluatorSelectorProps = {
  taskId: string;
  onSelectionChange?: () => void;
};

function useDebouncedValue(value: string, delayMs: number) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

function useMLEvalVersions(taskId: string | undefined, evalName: string | undefined) {
  const { data, isLoading } = useApiQuery<"getAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGet">({
    method: "getAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGet",
    args: [
      {
        taskId: taskId!,
        evalName: encodePathParam(evalName!),
        page: 0,
        page_size: 100,
        sort: "desc",
        created_after: null,
        created_before: null,
        model_provider: null,
        model_name: null,
        exclude_deleted: false,
        min_version: null,
        max_version: null,
      },
    ],
    enabled: !!taskId && !!evalName,
    queryOptions: { staleTime: 2000 },
  });
  return {
    versions: (data as LLMEvalsVersionListResponse | undefined)?.versions ?? [],
    isLoading,
  };
}

export const EvaluatorSelector = withFieldGroup({
  defaultValues: {
    name: null,
    version: null,
    eval_type: null,
  } as EvaluatorFormState,
  props: {} as EvaluatorSelectorProps,
  render: function Render({ group, taskId, onSelectionChange }) {
    const [openTypePicker, setOpenTypePicker] = useState(false);
    const [openCreateLLMModal, setOpenCreateLLMModal] = useState(false);
    const [openCreateMLModal, setOpenCreateMLModal] = useState(false);
    const [inputValue, setInputValue] = useState("");
    const debouncedSearch = useDebouncedValue(inputValue, 300);

    const {
      evals,
      isLoading: isEvaluatorsLoading,
      refetch,
    } = useEvals(taskId, {
      page: 0,
      pageSize: 30,
      sort: "desc",
      llm_asset_names: debouncedSearch ? [debouncedSearch] : null,
    });

    const createEval = useCreateEvalMutation(taskId, async (evalData) => {
      await refetch();
      setOpenCreateLLMModal(false);
      group.setFieldValue("name", evalData.name);
      group.setFieldValue("version", evalData.version?.toString() ?? null);
      group.setFieldValue("eval_type", "llm");
      onSelectionChange?.();
    });

    const createMLEval = useCreateMlEvalMutation(taskId, async (evalData) => {
      await refetch();
      setOpenCreateMLModal(false);
      group.setFieldValue("name", evalData.name);
      group.setFieldValue("version", "latest");
      group.setFieldValue("eval_type", evalData.eval_type);
      onSelectionChange?.();
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const name = useStore(group.store, (state: any) => state.values.name as string | null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const evalType = useStore(group.store, (state: any) => state.values.eval_type as string | null);

    const isML = evalType !== null && evalType !== "llm_as_a_judge";

    const llmVersions = useEvalVersions(taskId, isML ? undefined : (name ?? undefined), {
      page: 0,
      pageSize: 100,
      sort: "desc",
    });

    const mlVersions = useMLEvalVersions(isML ? taskId : undefined, isML ? (name ?? undefined) : undefined);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const version = useStore(group.store, (state: any) => state.values.version as string | null);

    const selectedEval = evals.find((e) => e.name === name) ?? null;

    const handleEvalChange = (newEval: LLMGetAllMetadataResponse | null) => {
      group.setFieldValue("name", newEval?.name ?? null);
      group.setFieldValue("eval_type", newEval?.eval_type ?? null);
      // Default to "latest" for ML evals; clear for LLM evals (user must pick)
      group.setFieldValue("version", newEval?.eval_type !== "llm_as_a_judge" ? "latest" : null);
      onSelectionChange?.();
    };

    const handleVersionChange = (newVersion: string | null) => {
      group.setFieldValue("version", newVersion);
      onSelectionChange?.();
    };

    const mlVersionOptions = ["latest", ...mlVersions.versions.map((v) => v.version.toString())];
    const llmVersionOptions = llmVersions.versions?.map((v) => v.version.toString()) ?? [];

    return (
      <>
        <Stack gap={2}>
          <Stack direction="row" gap={2} width="100%" alignItems="center">
            <Typography variant="h6" color="text.primary" fontWeight="bold">
              Evaluator
            </Typography>
            <Button
              loading={createEval.isPending || createMLEval.isPending}
              variant="contained"
              disableElevation
              size="small"
              color="primary"
              startIcon={<AddIcon />}
              type="button"
              onClick={() => setOpenTypePicker(true)}
              sx={{ ml: "auto" }}
            >
              Create New Evaluator
            </Button>
          </Stack>

          <Stack direction="row" gap={2} width="100%">
            {/* Eval name selector */}
            <Autocomplete
              sx={{ flex: 1 }}
              loading={isEvaluatorsLoading}
              options={evals}
              value={selectedEval}
              onChange={(_, value) => handleEvalChange(value)}
              inputValue={inputValue}
              onInputChange={(_, value) => setInputValue(value)}
              getOptionLabel={(option) => option.name}
              isOptionEqualToValue={(option, value) => option.name === value.name}
              getOptionKey={(option) => `${option.eval_type}:${option.name}`}
              renderOption={(props, option) => (
                <Box component="li" {...props}>
                  <Stack direction="row" alignItems="center" gap={1} width="100%">
                    <Typography variant="body2" sx={{ flex: 1 }}>
                      {option.name}
                    </Typography>
                    {option.eval_type !== "llm_as_a_judge" ? (
                      <Chip label="ML" size="small" color="secondary" variant="outlined" sx={{ height: 18, fontSize: "0.65rem" }} />
                    ) : (
                      <Chip label="LLM" size="small" color="primary" variant="outlined" sx={{ height: 18, fontSize: "0.65rem" }} />
                    )}
                    {option.eval_type !== "llm_as_a_judge" && (
                      <Chip label={option.eval_type} size="small" variant="outlined" sx={{ height: 18, fontSize: "0.65rem" }} />
                    )}
                  </Stack>
                </Box>
              )}
              renderInput={(params) => (
                <TextField
                  {...params}
                  variant="filled"
                  label="Evaluator"
                  slotProps={{
                    input: {
                      ...params.InputProps,
                      endAdornment: (
                        <>
                          {isEvaluatorsLoading ? <CircularProgress color="inherit" size={16} /> : null}
                          {params.InputProps.endAdornment}
                        </>
                      ),
                    },
                  }}
                />
              )}
            />

            {/* Version selector — LLM evals */}
            {!isML && (
              <Autocomplete
                sx={{ width: 160 }}
                loading={llmVersions.isLoading}
                options={llmVersionOptions}
                value={version}
                onChange={(_, value) => handleVersionChange(value)}
                disabled={!name}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    variant="filled"
                    label="Version"
                    slotProps={{
                      input: {
                        ...params.InputProps,
                        endAdornment: (
                          <>
                            {llmVersions.isLoading ? <CircularProgress color="inherit" size={16} /> : null}
                            {params.InputProps.endAdornment}
                          </>
                        ),
                      },
                    }}
                  />
                )}
              />
            )}

            {/* Version selector — ML evals */}
            {isML && (
              <Autocomplete
                sx={{ width: 160 }}
                loading={mlVersions.isLoading}
                options={mlVersionOptions}
                value={version}
                onChange={(_, value) => handleVersionChange(value)}
                disabled={!name}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    variant="filled"
                    label="Version"
                    slotProps={{
                      input: {
                        ...params.InputProps,
                        endAdornment: (
                          <>
                            {mlVersions.isLoading ? <CircularProgress color="inherit" size={16} /> : null}
                            {params.InputProps.endAdornment}
                          </>
                        ),
                      },
                    }}
                  />
                )}
              />
            )}
          </Stack>
        </Stack>

        <CreateEvalTypeModal
          open={openTypePicker}
          onClose={() => setOpenTypePicker(false)}
          onSelectType={(type) => {
            setOpenTypePicker(false);
            if (type === "llm") setOpenCreateLLMModal(true);
            else setOpenCreateMLModal(true);
          }}
        />

        <EvalFormModal
          open={openCreateLLMModal}
          onClose={() => setOpenCreateLLMModal(false)}
          onSubmit={async (evalName, data) => {
            await createEval.mutateAsync({ evalName, data });
          }}
          isLoading={createEval.isPending}
        />

        <MLEvalFormModal
          open={openCreateMLModal}
          onClose={() => setOpenCreateMLModal(false)}
          onSubmit={async (evalName, data) => {
            await createMLEval.mutateAsync({ evalName, data });
          }}
          isLoading={createMLEval.isPending}
        />
      </>
    );
  },
});
