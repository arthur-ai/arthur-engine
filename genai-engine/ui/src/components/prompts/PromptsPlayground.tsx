import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import Divider from "@mui/material/Divider";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import React, { useCallback, useReducer, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";

import PromptComponent from "./PromptComponent";
import { PromptProvider } from "./PromptContext";
import { promptsReducer, initialState } from "./reducer";
import { toFrontendPrompt, spanToPrompt } from "./utils";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import {
  ModelProvider,
  ModelProviderResponse,
} from "@/lib/api-client/api-client";
import { sampleSpans } from "./sampleSpans";

const PromptsPlayground = () => {
  const [state, dispatch] = useReducer(promptsReducer, initialState);
  const [searchParams] = useSearchParams();
  const hasFetchedPrompts = useRef(false);
  const hasFetchedProviders = useRef(false);
  const hasFetchedAvailableModels = useRef(false);
  const hasFetchedSpan = useRef(false);

  const apiClient = useApi();
  const { task } = useTask();
  const taskId = task?.id;
  const spanId = searchParams.get("spanId");

  const fetchPrompts = useCallback(async () => {
    if (hasFetchedPrompts.current) {
      return;
    }

    if (!apiClient || !taskId) {
      console.error("No api client or task id");
      return;
    }

    hasFetchedPrompts.current = true;
    try {
      const response =
        await apiClient.api.getAllAgenticPromptsApiV1TasksTaskIdPromptsGet({
          taskId,
        });

      const { data } = response;
      const convertedPrompts = data.prompts.map(toFrontendPrompt);

      dispatch({
        type: "updateBackendPrompts",
        payload: { prompts: convertedPrompts },
      });
    } catch (error) {
      console.error("Failed to fetch prompts:", error);
    }
  }, [apiClient, taskId]);

  const fetchProviders = useCallback(async () => {
    if (hasFetchedProviders.current) {
      return;
    }

    if (!apiClient) {
      console.error("No api client");
      return;
    }

    hasFetchedProviders.current = true;
    const response =
      await apiClient.api.getModelProvidersApiV1ModelProvidersGet();

    const { data } = response;
    const providers = data.providers
      .filter((provider: ModelProviderResponse) => provider.enabled)
      .map((provider: ModelProviderResponse) => provider.provider);

    dispatch({
      type: "updateProviders",
      payload: { providers },
    });
  }, [apiClient]);

  const fetchAvailableModels = useCallback(async () => {
    if (
      hasFetchedAvailableModels.current ||
      !apiClient ||
      state.enabledProviders.length === 0
    ) {
      return;
    }

    hasFetchedAvailableModels.current = true;

    // Fetch models for all enabled providers in parallel
    const modelPromises = state.enabledProviders.map(async (provider) => {
      try {
        const response =
          await apiClient.api.getModelProvidersApiV1ModelProvidersProviderAvailableModelsGet(
            provider as ModelProvider
          );
        return { provider, models: response.data.available_models };
      } catch (error) {
        console.error(
          `Failed to fetch models for provider ${provider}:`,
          error
        );
        return { provider, models: [] };
      }
    });

    const results = await Promise.all(modelPromises);

    const newAvailableModels = new Map<ModelProvider, string[]>();
    results.forEach(({ provider, models }) => {
      newAvailableModels.set(provider, models);
    });

    // Single dispatch with the complete Map
    dispatch({
      type: "updateAvailableModels",
      payload: { availableModels: newAvailableModels },
    });
  }, [apiClient, state.enabledProviders]);

  const fetchSpanData = useCallback(async () => {
    if (hasFetchedSpan.current || !spanId || !apiClient) {
      return;
    }

    hasFetchedSpan.current = true;

    try {
      // const response = await apiClient.api.getSpanByIdApiV1TracesSpansSpanIdGet(
      //   spanId
      // );
      // const spanData = response.data;
      const spanPrompt = spanToPrompt(sampleSpans[1]); //spanToPrompt(spanData);

      // Update the first empty prompt instead of adding a new one
      if (state.prompts.length > 0) {
        dispatch({
          type: "updatePrompt",
          payload: { promptId: state.prompts[0].id, prompt: spanPrompt },
        });
      } else {
        dispatch({
          type: "hydratePrompt",
          payload: { promptData: spanPrompt },
        });
      }
    } catch (error) {
      console.error("Failed to fetch span data:", error);
    }
  }, [spanId, apiClient, state.prompts]);

  useEffect(() => {
    fetchPrompts();
    fetchProviders();
    if (spanId) {
      fetchSpanData();
    }
  }, [fetchPrompts, fetchProviders, fetchSpanData, spanId]);

  useEffect(() => {
    if (state.enabledProviders.length > 0) {
      fetchAvailableModels();
    }
  }, [state.enabledProviders, fetchAvailableModels]);

  const handleAddPrompt = useCallback(() => {
    dispatch({ type: "addPrompt" });
  }, [dispatch]);

  const handleKeywordValueChange = useCallback(
    (keyword: string, value: string) => {
      dispatch({ type: "updateKeywordValue", payload: { keyword, value } });
    },
    [dispatch]
  );

  const keywords = Array.from(state.keywords.keys());

  return (
    <PromptProvider state={state} dispatch={dispatch}>
      <div className="h-dvh bg-gray-200 overflow-y-auto">
        <div className={`h-full w-full p-1 flex flex-col gap-1`}>
          <div className={`bg-gray-300 flex-shrink-0 p-1`}>
            <Container
              component="div"
              className="flex justify-between items-center mb-1"
              maxWidth="xl"
              disableGutters
            >
              <div>Prompts Playground</div>
              <Button
                variant="contained"
                size="small"
                onClick={handleAddPrompt}
              >
                Add Prompt
              </Button>
              <Button variant="contained" size="small" onClick={() => {}}>
                Run Prompts
              </Button>
            </Container>
            <Container component="div" maxWidth="xl" disableGutters>
              <Paper elevation={3} className="p-1">
                <div className="grid grid-template-rows-2">
                  <div className="flex justify-center items-center">
                    <Typography variant="h5">Keyword Templates</Typography>
                  </div>
                  <div className="flex justify-center items-center">
                    <Typography variant="body2">
                      Keywords are identified by mustache braces
                      &#123;&#123;keyword&#125;&#125; and are used to replace
                      values in the messages. You can use the same keyword in
                      multiple prompts/messages.
                    </Typography>
                  </div>
                </div>
                <Divider />
                <div className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-1">
                  {keywords.map((keyword) => (
                    <div key={keyword} className="w-full">
                      <TextField
                        id={`keyword-${keyword}`}
                        label={keyword}
                        value={state.keywords.get(keyword)}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                          handleKeywordValueChange(keyword, e.target.value);
                        }}
                        variant="standard"
                        fullWidth
                      />
                    </div>
                  ))}
                </div>
              </Paper>
            </Container>
          </div>
          <div className="flex-1 overflow-y-auto min-h-0">
            <div className="grid grid-cols-[repeat(auto-fit,minmax(500px,1fr))] gap-1 min-h-full">
              {state.prompts.map((prompt) => (
                <PromptComponent key={prompt.id} prompt={prompt} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </PromptProvider>
  );
};

export default PromptsPlayground;
