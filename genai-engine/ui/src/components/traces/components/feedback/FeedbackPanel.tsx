import { Popover } from "@base-ui-components/react/popover";
import ClearIcon from "@mui/icons-material/Clear";
import SendIcon from "@mui/icons-material/Send";
import ThumbDownOutlinedIcon from "@mui/icons-material/ThumbDownOutlined";
import ThumbUpOutlinedIcon from "@mui/icons-material/ThumbUpOutlined";
import { Button, ButtonGroup, Paper, Stack, TextField, Tooltip, Typography } from "@mui/material";
import { useForm } from "@tanstack/react-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useSnackbar } from "notistack";
import z from "zod";

import { useApi } from "@/hooks/useApi";
import { AgenticAnnotationResponse, TraceResponse } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

type Props = {
  containerRef: React.RefObject<HTMLDivElement | null>;
  annotation?: AgenticAnnotationResponse | null;
  traceId: string;
};

type Feedback = "positive" | "negative" | null;

const handle = Popover.createHandle<{ feedback: Feedback }>();

export const FeedbackPanel = ({ containerRef, annotation, traceId }: Props) => {
  const api = useApi()!;
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();

  const sendFeedbackMutation = useMutation({
    mutationFn: async (data: { feedback: Feedback; details: string }) => {
      await api.api.annotateTraceApiV1TracesTraceIdAnnotationsPost(traceId, {
        annotation_score: data.feedback === "positive" ? 1 : 0,
        annotation_description: data.details,
      });
    },
    onMutate: async (data) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.traces.byId(traceId) });

      const previousData = queryClient.getQueryData<TraceResponse>(queryKeys.traces.byId(traceId));

      if (previousData) {
        queryClient.setQueryData(queryKeys.traces.byId(traceId), (old: TraceResponse) => ({
          ...old,
          annotation: {
            ...old.annotation,
            annotation_score: data.feedback === "positive" ? 1 : 0,
            annotation_description: data.details,
          },
        }));
      }

      return { previousData };
    },
    onSuccess: () => {
      enqueueSnackbar("Feedback submitted", { variant: "success" });
    },
    onError: (error, data, context) => {
      queryClient.setQueryData(queryKeys.traces.byId(traceId), context?.previousData);
      enqueueSnackbar("Failed to submit feedback", { variant: "error" });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.traces.byId(traceId) });
    },
  });

  const clearFeedbackMutation = useMutation({
    mutationFn: () => api.api.deleteAnnotationFromTraceApiV1TracesTraceIdAnnotationsDelete(traceId),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: queryKeys.traces.byId(traceId) });

      const previousData = queryClient.getQueryData<TraceResponse>(queryKeys.traces.byId(traceId));

      if (previousData) {
        queryClient.setQueryData(queryKeys.traces.byId(traceId), (old: TraceResponse) => ({
          ...old,
          annotation: null,
        }));
      }

      return { previousData };
    },
    onSuccess: () => {
      enqueueSnackbar("Feedback cleared", { variant: "success" });
    },
    onError: (error, data, context) => {
      queryClient.setQueryData(queryKeys.traces.byId(traceId), context?.previousData);
      enqueueSnackbar("Failed to clear feedback", { variant: "error" });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.traces.byId(traceId) });

      handle.close();
      form.reset();
    },
  });

  const form = useForm({
    defaultValues: annotation
      ? {
          feedback: annotation.annotation_score === 1 ? ("positive" as const) : ("negative" as const),
          details: annotation.annotation_description,
        }
      : {
          feedback: null,
          details: "",
        },
    validators: {
      onSubmit: z.object({
        feedback: z.enum(["positive", "negative"]),
        details: z.string().min(0),
      }),
    },
    onSubmit: ({ value }) => sendFeedbackMutation.mutateAsync({ feedback: value.feedback, details: value.details! }),
  });

  const feedback = annotation ? (annotation.annotation_score === 1 ? "positive" : "negative") : null;
  const isMutating = sendFeedbackMutation.isPending || clearFeedbackMutation.isPending;

  return (
    <>
      <ButtonGroup size="small" disableElevation disabled={isMutating}>
        <Tooltip title="Helpful">
          <Popover.Trigger
            handle={handle}
            render={
              <Button
                color={feedback === "positive" ? "success" : undefined}
                variant={feedback === "positive" ? "contained" : "outlined"}
                startIcon={<ThumbUpOutlinedIcon sx={{ fontSize: 16 }} />}
              />
            }
            payload={{ feedback: "positive" }}
            disabled={feedback === "negative"}
          >
            Helpful
          </Popover.Trigger>
        </Tooltip>
        <Tooltip title="Needs improvement">
          <Popover.Trigger
            handle={handle}
            render={
              <Button
                variant={feedback === "negative" ? "contained" : "outlined"}
                color={feedback === "negative" ? "error" : undefined}
                startIcon={<ThumbDownOutlinedIcon sx={{ fontSize: 16 }} />}
              />
            }
            payload={{ feedback: "negative" }}
            disabled={feedback === "positive"}
          >
            Unhelpful
          </Popover.Trigger>
        </Tooltip>
      </ButtonGroup>

      <Popover.Root handle={handle}>
        {({ payload }) => {
          if (!payload) return null;

          const config = FEEDBACK_CONFIG[payload.feedback!];

          return (
            <Popover.Portal container={containerRef.current}>
              <Popover.Positioner sideOffset={8} side="bottom" align="end">
                <Popover.Popup render={<Paper />} className="origin-(--transform-origin) p-4 w-80 outline-none">
                  <Stack direction="column" gap={1}>
                    <Stack direction="column" gap={0}>
                      <Popover.Title render={<Typography variant="body2" fontWeight="bold" color="text.primary" />}>
                        Provide additional details
                      </Popover.Title>
                      <Popover.Description render={<Typography variant="body2" color="text.secondary" />}>{config.description}</Popover.Description>
                    </Stack>
                    <Stack
                      component="form"
                      direction="column"
                      gap={1}
                      onSubmit={(e) => {
                        e.preventDefault();
                        form.handleSubmit();
                      }}
                    >
                      <form.Field
                        name="details"
                        children={(field) => (
                          <TextField
                            multiline
                            rows={3}
                            fullWidth
                            size="small"
                            label="Additional details"
                            placeholder="The trace shows..."
                            value={field.state.value}
                            onBlur={field.handleBlur}
                            onChange={(e) => field.handleChange(e.target.value)}
                            error={field.state.meta.errors.length > 0}
                          />
                        )}
                      />
                      <form.Field
                        name="feedback"
                        key={`feedback-${payload.feedback}`}
                        defaultValue={payload.feedback!}
                        children={(field) => <TextField hidden type="hidden" value={field.state.value} sx={{ display: "none" }} />}
                      />
                      <Stack direction="row" gap={1}>
                        {annotation && (
                          <Button
                            variant="outlined"
                            color="error"
                            size="small"
                            onClick={() => clearFeedbackMutation.mutate()}
                            startIcon={<ClearIcon />}
                            loading={clearFeedbackMutation.isPending}
                          >
                            Clear
                          </Button>
                        )}
                        <form.Subscribe selector={(state) => [state.isSubmitting, state.canSubmit]}>
                          {([isSubmitting, canSubmit]) => (
                            <Button
                              type="submit"
                              variant="contained"
                              color="primary"
                              disabled={!canSubmit}
                              loading={isSubmitting}
                              size="small"
                              sx={{ flex: 1 }}
                              startIcon={<SendIcon />}
                            >
                              Submit
                            </Button>
                          )}
                        </form.Subscribe>
                      </Stack>
                    </Stack>
                  </Stack>
                </Popover.Popup>
              </Popover.Positioner>
            </Popover.Portal>
          );
        }}
      </Popover.Root>
    </>
  );
};

const FEEDBACK_CONFIG = {
  positive: {
    icon: <ThumbUpOutlinedIcon fontSize="small" />,
    label: "Looks good",
    description: "What did you find helpful about this trace?",
    color: "success" as const,
  },
  negative: {
    icon: <ThumbDownOutlinedIcon fontSize="small" />,
    label: "Needs improvement",
    description: "What went wrong or could be improved?",
    color: "error" as const,
  },
};
