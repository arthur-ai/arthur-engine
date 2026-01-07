import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import { Button, Divider, IconButton, Paper, Stack, TextField, Typography } from "@mui/material";
import { z } from "zod";

import { newAgentExperimentFormOpts } from "../form";

import NunjucksHighlightedTextField from "@/components/evaluators/MustacheHighlightedTextField";
import { withForm } from "@/components/traces/components/filtering/hooks/form";

export const EndpointSetup = withForm({
  ...newAgentExperimentFormOpts,
  render: function Render({ form }) {
    return (
      <Stack component={Paper} variant="outlined" p={2} gap={2} divider={<Divider />}>
        <Stack gap={2}>
          <form.AppField
            name="endpoint.name"
            validators={{
              onChange: z.string().min(1, "Name is required"),
            }}
          >
            {(field) => (
              <TextField
                size="small"
                label="Endpoint Name"
                required
                onChange={(e) => field.handleChange(e.target.value)}
                value={field.state.value}
                error={field.state.meta.errors.length > 0}
                helperText={field.state.meta.errors[0]?.message}
              />
            )}
          </form.AppField>
          <form.AppField
            name="endpoint.url"
            validators={{
              onChange: z.url("Invalid URL").min(1, "URL is required"),
            }}
          >
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
          </form.AppField>
        </Stack>
        <form.AppField
          name="endpoint.headers"
          validators={{
            onChange: z.array(
              z.object({
                name: z.string().min(1, "Header name is required"),
                value: z.string().min(1, "Header value is required"),
              })
            ),
          }}
          mode="array"
        >
          {(field) => (
            <Stack component={Paper} variant="outlined" p={2} gap={1}>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Stack>
                  <Typography variant="body2" fontWeight="bold">
                    Headers
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Use <code>{"{{variable}}"}</code> placeholders in header names or values for dynamic dataset values.
                  </Typography>
                </Stack>
                <Button size="small" startIcon={<AddIcon />} onClick={() => field.pushValue({ name: "", value: "" })}>
                  Add Header
                </Button>
              </Stack>
              <Stack gap={1}>
                {field.state.value.length > 0 ? (
                  field.state.value.map((header, index) => (
                    <Stack direction="row" gap={1} alignItems="center">
                      <form.AppField
                        name={`endpoint.headers[${index}].name`}
                        validators={{
                          onChange: z.string().min(1, "Header name is required"),
                        }}
                      >
                        {(field) => (
                          <TextField
                            size="small"
                            label="Header Name"
                            required
                            onChange={(e) => field.handleChange(e.target.value)}
                            value={field.state.value}
                            error={field.state.meta.errors.length > 0}
                            helperText={field.state.meta.errors[0]?.message ?? "Name of the header"}
                            fullWidth
                          />
                        )}
                      </form.AppField>
                      <Typography variant="body2" color="text.secondary" mb={3}>
                        :
                      </Typography>
                      <form.AppField
                        name={`endpoint.headers[${index}].value`}
                        validators={{
                          onChange: z.string().min(1, "Header value is required"),
                        }}
                      >
                        {(field) => (
                          <TextField
                            size="small"
                            label="Header Value"
                            required
                            onChange={(e) => field.handleChange(e.target.value)}
                            value={field.state.value}
                            error={field.state.meta.errors.length > 0}
                            helperText={field.state.meta.errors[0]?.message ?? "Value of the header"}
                            fullWidth
                          />
                        )}
                      </form.AppField>
                      <IconButton color="error" onClick={() => field.removeValue(index)} sx={{ mb: 3 }}>
                        <DeleteIcon />
                      </IconButton>
                    </Stack>
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No headers added yet
                  </Typography>
                )}
              </Stack>
            </Stack>
          )}
        </form.AppField>
        <form.AppField
          name="endpoint.body"
          validators={{
            onChange: z.string().min(1, "Body is required"),
          }}
        >
          {(field) => (
            <Stack component={Paper} variant="outlined" p={2} gap={1}>
              <Stack>
                <Typography variant="body2" fontWeight="bold">
                  Request Body (JSON)
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Use <code>{"{{variable}}"}</code> placeholders in request body for dynamic dataset values.
                </Typography>
              </Stack>
              <NunjucksHighlightedTextField
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                placeholder="Enter request body..."
                size="small"
              />
            </Stack>
          )}
        </form.AppField>
      </Stack>
    );
  },
});
