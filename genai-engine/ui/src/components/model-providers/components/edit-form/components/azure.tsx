import { withFieldGroup } from "@arthur/shared-components";
import { TextField } from "@mui/material";
import z from "zod";

export const AzureFields = withFieldGroup({
  defaultValues: {
    api_key: "",
    api_base: "",
    api_version: "",
  },
  render: function Render({ group }) {
    return (
      <>
        <group.AppField
          name="api_key"
          validators={{
            onChange: z.string().min(1, "API Key is required"),
          }}
        >
          {(field) => (
            <TextField
              label="API Key*"
              type="password"
              fullWidth
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              error={field.state.meta.errors.length > 0}
              helperText={field.state.meta.errors[0]?.message || "Your Azure OpenAI API key"}
            />
          )}
        </group.AppField>
        <group.AppField
          name="api_base"
          validators={{
            onChange: z.string().min(1, "Endpoint URL is required"),
          }}
        >
          {(field) => (
            <TextField
              label="Endpoint URL*"
              type="text"
              fullWidth
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              error={field.state.meta.errors.length > 0}
              helperText={field.state.meta.errors[0]?.message || "Your Azure OpenAI endpoint (e.g. https://my-deployment.openai.azure.com/)"}
            />
          )}
        </group.AppField>
        <group.AppField
          name="api_version"
          validators={{
            onChange: z.string().min(1, "API Version is required"),
          }}
        >
          {(field) => (
            <TextField
              label="API Version*"
              type="text"
              fullWidth
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              error={field.state.meta.errors.length > 0}
              helperText={field.state.meta.errors[0]?.message || "Azure API version (e.g. 2024-02-01)"}
            />
          )}
        </group.AppField>
      </>
    );
  },
});
