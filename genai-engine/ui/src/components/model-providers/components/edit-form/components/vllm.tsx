import { TextField } from "@mui/material";
import z from "zod";

import { withFieldGroup } from "@arthur/shared-components";

export const VllmFields = withFieldGroup({
  defaultValues: {
    api_base: "",
    api_key: "",
  },
  render: function Render({ group }) {
    return (
      <>
        <group.AppField
          name="api_base"
          validators={{
            onChange: z.string().min(1, "API Base URL is required"),
          }}
        >
          {(field) => (
            <TextField
              label="API Base URL*"
              type="text"
              fullWidth
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              error={field.state.meta.errors.length > 0}
              helperText={field.state.meta.errors[0]?.message || "The base URL for your vLLM endpoint"}
            />
          )}
        </group.AppField>
        <group.AppField name="api_key">
          {(field) => (
            <TextField
              label="API Key (Optional)"
              type="password"
              fullWidth
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              error={field.state.meta.errors.length > 0}
              helperText={field.state.meta.errors.length > 0 ? field.state.meta.errors[0] : "Optional API key for authentication"}
            />
          )}
        </group.AppField>
      </>
    );
  },
});
