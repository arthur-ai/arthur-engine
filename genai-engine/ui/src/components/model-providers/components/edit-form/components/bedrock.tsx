import { Stack, TextField, ToggleButton, ToggleButtonGroup } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import z from "zod";

import { BedrockFormValues } from "../form";

import { withFieldGroup } from "@/components/traces/components/filtering/hooks/form";

export const BedrockFields = withFieldGroup({
  defaultValues: {
    type: "api_key",
    api_key: "",
    aws_bedrock_runtime_endpoint: "",
    aws_role_name: "",
    aws_session_name: "",
  } as BedrockFormValues,
  render: function Render({ group }) {
    const type = useStore(group.store, (state) => state.values.type);

    return (
      <Stack gap={2}>
        <group.AppField
          name="type"
          defaultValue="api_key"
          validators={{ onChange: z.enum(["api_key", "access_key"]) }}
          listeners={{
            onChange: ({ value }) => {
              if (value === "api_key") {
                group.resetField("aws_access_key_id");
                group.resetField("aws_secret_access_key");
              } else {
                group.resetField("api_key");
              }
            },
          }}
        >
          {(field) => (
            <ToggleButtonGroup
              exclusive
              value={field.state.value}
              onChange={(_, value) => {
                if (value !== null) field.handleChange(value);
              }}
              fullWidth
            >
              <ToggleButton value="api_key">API Key</ToggleButton>
              <ToggleButton value="access_key">Access Key</ToggleButton>
            </ToggleButtonGroup>
          )}
        </group.AppField>

        {type === "api_key" && (
          <group.AppField name="api_key" validators={{ onChange: z.string().min(1, "API Key is required") }}>
            {(field) => (
              <TextField
                required
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
        )}

        {type === "access_key" && (
          <>
            <group.AppField name="aws_access_key_id" validators={{ onChange: z.string().min(1, "Access Key ID is required") }}>
              {(field) => (
                <TextField
                  required
                  label="Access Key ID"
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

            <group.AppField name="aws_secret_access_key" validators={{ onChange: z.string().min(1, "Secret Access Key is required") }}>
              {(field) => (
                <TextField
                  required
                  label="Secret Access Key"
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
          </>
        )}

        <group.AppField name="aws_bedrock_runtime_endpoint" validators={{ onChange: z.url().or(z.literal("")) }}>
          {(field) => (
            <TextField
              label="Runtime Endpoint"
              type="text"
              fullWidth
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              error={field.state.meta.errors.length > 0}
              helperText={field.state.meta.errors[0]?.message}
            />
          )}
        </group.AppField>

        <group.AppField name="aws_role_name" validators={{ onChange: z.string() }}>
          {(field) => (
            <TextField label="Role Name" type="text" fullWidth value={field.state.value} onChange={(e) => field.handleChange(e.target.value)} />
          )}
        </group.AppField>

        <group.AppField name="aws_session_name" validators={{ onChange: z.string() }}>
          {(field) => (
            <TextField label="Session Name" type="text" fullWidth value={field.state.value} onChange={(e) => field.handleChange(e.target.value)} />
          )}
        </group.AppField>
      </Stack>
    );
  },
});
