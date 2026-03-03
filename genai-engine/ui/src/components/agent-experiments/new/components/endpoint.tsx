import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import { Box, Button, Divider, IconButton, Paper, Stack, TextField, Typography } from "@mui/material";
import { z } from "zod";

import { NewAgentExperimentFormData } from "../form";

import { MustacheHighlightedTextField } from "@arthur/shared-components";
import { withFieldGroup } from "@arthur/shared-components";

export const EndpointSetup = withFieldGroup({
  defaultValues: {} as Pick<NewAgentExperimentFormData, "endpoint">,
  render: function Render({ group }) {
    return (
      <Stack gap={2}>
        <Stack gap={2}>
          <group.AppField
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
          </group.AppField>
          <group.AppField
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
          </group.AppField>
        </Stack>
        <group.AppField name="endpoint.headers" mode="array">
          {(field) => (
            <Stack component={Paper} variant="outlined" p={2}>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Stack>
                  <Typography variant="body2" fontWeight="bold">
                    Headers
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Add custom HTTP headers. Use{" "}
                    <Box component="code" sx={{ color: "primary.main", bgcolor: "action.hover", px: 0.5, borderRadius: 0.5 }}>{`{{ variable }}`}</Box>{" "}
                    for dynamic values.
                  </Typography>
                </Stack>
                <Button
                  size="small"
                  variant="outlined"
                  disableElevation
                  startIcon={<AddIcon />}
                  onClick={() => field.pushValue({ name: "", value: "" })}
                >
                  Add Header
                </Button>
              </Stack>
              <Divider sx={{ my: 2 }} />
              <Stack gap={1}>
                {field.state.value.length > 0 ? (
                  field.state.value.map((header, index) => (
                    <Stack key={index} direction="row" gap={1} alignItems="center">
                      <group.AppField
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
                      </group.AppField>
                      <Typography variant="body2" color="text.secondary" mb={3}>
                        :
                      </Typography>
                      <group.AppField
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
                      </group.AppField>
                      <IconButton color="error" onClick={() => field.removeValue(index)} sx={{ mb: 3 }}>
                        <DeleteIcon />
                      </IconButton>
                    </Stack>
                  ))
                ) : (
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      py: 4,
                      border: "1px dashed",
                      borderColor: "divider",
                      borderRadius: 1,
                    }}
                  >
                    <Typography variant="body2" color="text.secondary">
                      No headers added yet
                    </Typography>
                  </Box>
                )}
              </Stack>
            </Stack>
          )}
        </group.AppField>
        <group.AppField
          name="endpoint.body"
          validators={{
            onChange: z.string().min(1, "Request body is required"),
          }}
        >
          {(field) => {
            const hasErrors = field.state.meta.errors.length > 0;
            const error = field.state.meta.errors[0]?.message;

            return (
              <Stack component={Paper} variant="outlined" p={2} sx={{ borderColor: hasErrors ? "error.main" : "divider" }}>
                <Stack>
                  <Typography variant="body2" fontWeight="bold">
                    Request Body
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Define the request body as a string. Use{" "}
                    <Box component="code" sx={{ color: "primary.main", bgcolor: "action.hover", px: 0.5, borderRadius: 0.5 }}>{`{{ variable }}`}</Box>{" "}
                    placeholders for dataset values. The body will be sent as-is after variable substitution.
                  </Typography>
                </Stack>
                <Divider sx={{ my: 2 }} />
                <MustacheHighlightedTextField
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  placeholder="Enter request body..."
                  size="small"
                  hideTokens={hasErrors}
                />
                {hasErrors && (
                  <Typography variant="caption" color="error" mt={1}>
                    {error}
                  </Typography>
                )}
              </Stack>
            );
          }}
        </group.AppField>
      </Stack>
    );
  },
});
