import { Autocomplete, Button, DialogActions, DialogContent, DialogTitle, ListItem, Stack, TextField, Typography } from "@mui/material";
import { useQueryClient } from "@tanstack/react-query";
import { useSnackbar } from "notistack";
import z from "zod";

import { agentNotebookStateFormOpts } from "../../form";
import { mapTemplateToForm } from "../../utils/mapper";

import { agentExperimentQueryOptions } from "@/components/agent-experiments/hooks/useAgentExperiment";
import { useAgentExperiments } from "@/components/agent-experiments/hooks/useAgentExperiments";
import { useAppForm, withForm } from "@/components/traces/components/filtering/hooks/form";
import { useApi } from "@/hooks/useApi";
import { EVENT_NAMES, track } from "@/services/amplitude";

type Props = {
  onClose: () => void;
};

export const ExperimentConfigSelector = withForm({
  ...agentNotebookStateFormOpts,
  props: {} as Props,
  render: function Render({ form: parentForm, onClose }) {
    const api = useApi()!;
    const queryClient = useQueryClient();
    const { enqueueSnackbar } = useSnackbar();

    const form = useAppForm({
      defaultValues: {
        experimentId: "",
      },
      onSubmit: async ({ value }) => {
        try {
          const experiment = await queryClient.fetchQuery(agentExperimentQueryOptions({ api, experimentId: value.experimentId }));

          track(EVENT_NAMES.AGENT_NOTEBOOK_LOAD_EXPERIMENT_CONFIG, { experiment_id: value.experimentId });

          parentForm.reset(mapTemplateToForm(experiment.data));
          await parentForm.validateAllFields("change");

          onClose();
        } catch (error) {
          console.error(error);
          enqueueSnackbar("Failed to load experiment configuration", { variant: "error" });
        }
      },
    });

    const { data: experiments, isLoading } = useAgentExperiments({ page: 0, page_size: 25 });

    return (
      <>
        <DialogTitle>Load Experiment Config</DialogTitle>
        <form
          className="contents"
          onSubmit={(e) => {
            e.preventDefault();
            e.stopPropagation();
            form.handleSubmit();
          }}
        >
          <DialogContent dividers>
            <Stack gap={2}>
              <Typography variant="body2" color="text.secondary">
                Select an experiment to load the configuration from. Loading the configuration will overwrite the current notebook configuration.
              </Typography>
              <form.Field name="experimentId" validators={{ onChange: z.string().min(1, "Experiment is required") }}>
                {(field) => {
                  const selected = experiments?.data?.find((e) => e.id === field.state.value) ?? null;

                  return (
                    <Autocomplete
                      loading={isLoading}
                      options={experiments?.data ?? []}
                      value={selected}
                      onChange={(_, value) => {
                        field.handleChange(value?.id ?? "");
                      }}
                      getOptionLabel={(option) => option.name}
                      getOptionKey={(option) => option.id}
                      renderOption={(props, option) => {
                        const { key, ...optionProps } = props;
                        return (
                          <ListItem key={key} {...optionProps}>
                            <Stack>
                              <Typography variant="body1">{option.name}</Typography>
                              <Typography variant="body2" color="text.secondary">
                                {option.http_template.endpoint_url}
                              </Typography>
                            </Stack>
                          </ListItem>
                        );
                      }}
                      renderInput={(params) => <TextField {...params} label="Experiment" />}
                    />
                  );
                }}
              </form.Field>
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                form.reset();
                onClose();
              }}
            >
              Cancel
            </Button>
            <form.Subscribe selector={(state) => [state.canSubmit, state.isSubmitting]}>
              {([canSubmit, isSubmitting]) => (
                <Button type="submit" variant="contained" color="primary" disabled={!canSubmit} loading={isSubmitting}>
                  Load Configuration
                </Button>
              )}
            </form.Subscribe>
          </DialogActions>
        </form>
      </>
    );
  },
});
