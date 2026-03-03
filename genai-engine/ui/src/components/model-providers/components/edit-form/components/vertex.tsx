import UploadFileIcon from "@mui/icons-material/UploadFile";
import { Button, Link, Stack, styled, TextField, Typography } from "@mui/material";
import z from "zod";

import { VertexAIFormValues } from "../form";

import { withFieldGroup } from "@arthur/shared-components";

export const VertexAIFields = withFieldGroup({
  defaultValues: {
    project_id: "",
    region: "",
    gcp_service_account_credentials: null,
  } as VertexAIFormValues,
  render: function Render({ group }) {
    return (
      <Stack gap={2}>
        <group.AppField name="project_id" validators={{ onChange: z.string() }}>
          {(field) => (
            <TextField
              label="Project ID"
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
        <group.AppField name="region" validators={{ onChange: z.string() }}>
          {(field) => (
            <TextField
              label="Region"
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

        <group.AppField name="gcp_service_account_credentials" validators={{ onChange: z.instanceof(File).nullable() }}>
          {(field) => (
            <Stack gap={1}>
              <Button component="label" variant="contained" color="primary" disableElevation tabIndex={-1} startIcon={<UploadFileIcon />}>
                Upload Credentials (Optional)
                <VisuallyHiddenInput
                  type="file"
                  accept=".json,application/json"
                  onChange={(e) => field.handleChange(e.target.files?.[0] ?? null)}
                  onBlur={field.handleBlur}
                />
              </Button>
              {field.state.meta.errors.length > 0 ? (
                <Typography variant="body2" color="error">
                  {field.state.meta.errors[0]?.message}
                </Typography>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  <group.Subscribe selector={(state) => state.values.gcp_service_account_credentials?.name}>
                    {(name) => name ?? "No file selected"}
                  </group.Subscribe>
                </Typography>
              )}
              <Typography variant="caption" color="text.secondary">
                If no credentials file is provided, the engine will use{" "}
                <Link href="https://cloud.google.com/docs/authentication/application-default-credentials" target="_blank" rel="noopener">
                  Application Default Credentials
                </Link>
                .
              </Typography>
            </Stack>
          )}
        </group.AppField>
      </Stack>
    );
  },
});

const VisuallyHiddenInput = styled("input")({
  clip: "rect(0 0 0 0)",
  clipPath: "inset(50%)",
  height: 1,
  overflow: "hidden",
  position: "absolute",
  bottom: 0,
  left: 0,
  whiteSpace: "nowrap",
  width: 1,
});
