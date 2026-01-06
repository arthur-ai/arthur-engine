import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import { Button, DialogActions, DialogContent, DialogTitle, IconButton, Stack, TextField, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import z from "zod";

import MustacheHighlightedTextField from "@/components/evaluators/MustacheHighlightedTextField";
import { useAppForm } from "@/components/traces/components/filtering/hooks/form";

const FormSchema = z.object({
  name: z.string().min(1, "Name is required"),
  url: z.url("Invalid URL").min(1, "URL is required"),
  headers: z.array(z.object({ name: z.string().min(1, "Header name is required"), value: z.string().min(1, "Header value is required") })),
  body: z.string(),
});

export const NewEndpointDialogContent = () => {
  // TODO: Change to a global, not scoped form instance
  const form = useAppForm({
    defaultValues: {
      name: "",
      url: "",
      headers: [{ name: "", value: "" }],
      body: "{}",
    },
    validators: {
      onChange: FormSchema,
    },
    onSubmit: async ({ value }) => {
      console.log(value);
    },
  });

  const errors = useStore(form.store, (state) => state.errors);

  console.log(errors);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        form.handleSubmit();
      }}
    >
      <DialogTitle>New Endpoint</DialogTitle>
      <DialogContent dividers>
        <Stack gap={2}>
          <form.AppField name="name">
            {(field) => (
              <TextField
                size="small"
                error={field.state.meta.errors.length > 0}
                label="Endpoint Name"
                required
                onChange={(e) => field.handleChange(e.target.value)}
                value={field.state.value}
                helperText={field.state.meta.errors[0]?.message}
              />
            )}
          </form.AppField>
          <form.Field name="url">
            {(field) => (
              <TextField
                size="small"
                label="Endpoint URL"
                required
                onChange={(e) => field.handleChange(e.target.value)}
                value={field.state.value}
                error={field.state.meta.errors.length > 0}
                helperText={field.state.meta.errors[0]?.message}
              />
            )}
          </form.Field>
          <Stack gap={1}>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Typography variant="body2" fontWeight="bold">
                Headers
              </Typography>
              <form.Field name="headers" mode="array">
                {(field) => (
                  <Button size="small" startIcon={<AddIcon />} onClick={() => field.pushValue({ name: "", value: "" })}>
                    Add Header
                  </Button>
                )}
              </form.Field>
            </Stack>
            <Typography variant="body2" color="text.secondary">
              Use <code>{"{{variable}}"}</code> placeholders in header names or values for dynamic dataset values.
            </Typography>
            <form.Field name="headers" mode="array">
              {(field) => (
                <Stack gap={1}>
                  {field.state.value.map((header, index) => (
                    <Stack direction="row" gap={1} alignItems="center">
                      <form.Field name={`headers[${index}].name`}>
                        {(field) => (
                          <TextField
                            error={field.state.meta.errors.length > 0}
                            size="small"
                            label="Header Name"
                            required
                            onChange={(e) => field.handleChange(e.target.value)}
                            value={field.state.value}
                            fullWidth
                          />
                        )}
                      </form.Field>
                      <Typography variant="body2" color="text.secondary">
                        :
                      </Typography>
                      <form.Field name={`headers[${index}].value`}>
                        {(field) => (
                          <TextField
                            error={field.state.meta.errors.length > 0}
                            size="small"
                            label="Header Value"
                            required
                            onChange={(e) => field.handleChange(e.target.value)}
                            value={field.state.value}
                            fullWidth
                          />
                        )}
                      </form.Field>
                      <IconButton color="error" onClick={() => field.removeValue(index)}>
                        <DeleteIcon />
                      </IconButton>
                    </Stack>
                  ))}
                </Stack>
              )}
            </form.Field>
          </Stack>
          <Stack gap={1}>
            <Typography variant="body2" fontWeight="bold">
              Request Body (JSON)
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Use <code>{"{{variable}}"}</code> placeholders in request body for dynamic dataset values.
            </Typography>
            <form.Field name="body">
              {(field) => (
                <MustacheHighlightedTextField
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  placeholder="Enter request body..."
                  size="small"
                />
              )}
            </form.Field>
          </Stack>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => form.reset()}>Cancel</Button>
        <Button type="submit" variant="contained" disableElevation>
          Create
        </Button>
      </DialogActions>
    </form>
  );
};
