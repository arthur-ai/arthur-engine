import { withFieldGroup } from "@arthur/shared-components";
import { TextField } from "@mui/material";
import z from "zod";

export const APIKeyFields = withFieldGroup({
  defaultValues: {
    api_key: "",
  },
  render: function Render({ group }) {
    return (
      <group.AppField
        name="api_key"
        validators={{
          onChange: z.string().min(1, "API Key is required"),
        }}
      >
        {(field) => (
          <TextField
            label="API Key"
            type="password"
            fullWidth
            value={field.state.value}
            onChange={(e) => field.handleChange(e.target.value)}
            onBlur={field.handleBlur}
            error={field.state.meta.errors.length > 0}
            helperText={field.state.meta.errors[0]?.message}
          />
        )}
      </group.AppField>
    );
  },
});
