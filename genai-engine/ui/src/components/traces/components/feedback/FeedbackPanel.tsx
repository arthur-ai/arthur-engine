import { Popover } from "@base-ui-components/react/popover";
import ThumbDownIcon from "@mui/icons-material/ThumbDown";
import ThumbUpIcon from "@mui/icons-material/ThumbUp";
import { Button, IconButton, Paper, Stack, TextField, Tooltip, Typography } from "@mui/material";
import { useForm } from "@tanstack/react-form";
import { useSnackbar } from "notistack";

import { wait } from "@/utils";

type Props = {
  containerRef: React.RefObject<HTMLDivElement | null>;
};

const handle = Popover.createHandle<{ feedback: "positive" | "negative" }>();

export const FeedbackPanel = ({ containerRef }: Props) => {
  const { enqueueSnackbar } = useSnackbar();

  const form = useForm({
    defaultValues: {
      feedback: "",
      details: "",
    },
    onSubmit: async () => {
      await wait(1000);
      enqueueSnackbar("Feedback submitted", { variant: "success" });
      form.reset();
      handle.close();
    },
  });

  return (
    <Stack direction="row" alignItems="center" gap={2}>
      <Tooltip title="Looks good">
        <span>
          <Popover.Trigger handle={handle} render={<IconButton size="small" />} payload={{ feedback: "positive" }}>
            <ThumbUpIcon fontSize="small" />
          </Popover.Trigger>
        </span>
      </Tooltip>
      <Tooltip title="Needs improvement">
        <span>
          <Popover.Trigger handle={handle} render={<IconButton size="small" />} payload={{ feedback: "negative" }}>
            <ThumbDownIcon fontSize="small" />
          </Popover.Trigger>
        </span>
      </Tooltip>
      <Popover.Root handle={handle}>
        {({ payload }) => (
          <Popover.Portal container={containerRef.current}>
            <Popover.Positioner sideOffset={8}>
              <Popover.Popup render={<Paper variant="outlined" />} className="origin-(--transform-origin) p-4">
                <Popover.Title render={<Typography variant="body1" fontWeight="bold" />}>
                  {payload?.feedback === "positive" ? "Looks good" : "Needs improvement"}
                </Popover.Title>
                <Popover.Description render={<Typography variant="body2" />}>
                  Thank you for sharing your feedback. Optionally, you can add more details below.
                </Popover.Description>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    form.handleSubmit();
                  }}
                  className="mt-2 flex flex-col gap-2"
                >
                  <form.Field
                    name="details"
                    children={(field) => (
                      <TextField
                        multiline
                        rows={4}
                        fullWidth
                        label="Additional details (optional)"
                        placeholder="The trace shows..."
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(e) => field.handleChange(e.target.value)}
                        error={field.state.meta.errors.length > 0}
                        helperText={field.state.meta.errors[0]}
                      />
                    )}
                  />
                  <form.Field
                    name="feedback"
                    key={payload?.feedback}
                    defaultValue={payload?.feedback}
                    children={(field) => <TextField hidden type="hidden" value={field.state.value} />}
                  />
                  <form.Subscribe selector={(state) => [state.isSubmitting, state.canSubmit]}>
                    {([isSubmitting, canSubmit]) => (
                      <Button type="submit" variant="contained" color="primary" disabled={!canSubmit} loading={isSubmitting}>
                        Submit
                      </Button>
                    )}
                  </form.Subscribe>
                </form>
              </Popover.Popup>
            </Popover.Positioner>
          </Popover.Portal>
        )}
      </Popover.Root>
    </Stack>
  );
};
