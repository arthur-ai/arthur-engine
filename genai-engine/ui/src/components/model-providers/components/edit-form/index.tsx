import { Button, DialogActions, DialogContent } from "@mui/material";

import { APIKeyFields } from "./components/api";
import { BedrockFields } from "./components/bedrock";
import { VertexAIFields } from "./components/vertex";
import { BedrockFormValues, editFormOptions, VertexAIFormValues } from "./form";
import { parseCredentials } from "./utils";

import { useAppForm } from "@/components/traces/components/filtering/hooks/form";
import { ModelProvider, PutModelProviderCredentials } from "@/lib/api-client/api-client";

type Props = {
  provider: ModelProvider;
  onSubmit: (data: PutModelProviderCredentials) => Promise<void>;
  onClose: () => void;
};

export const EditForm = ({ provider, onSubmit, onClose }: Props) => {
  const form = useAppForm({
    ...editFormOptions(provider),
    onSubmit: async ({ value, formApi }) => {
      if (provider === "vertex_ai") {
        const { gcp_service_account_credentials, ...rest } = value as VertexAIFormValues;

        if (!gcp_service_account_credentials) return;

        const credentials = await parseCredentials(gcp_service_account_credentials);

        if (!credentials.success) {
          formApi.setFieldMeta("gcp_service_account_credentials", (old) => ({
            ...old,
            errorMap: { onSubmit: { message: "Invalid credentials file" } },
          }));

          return;
        }

        return onSubmit({
          ...rest,
          credentials_file: credentials.data,
        });
      }

      if (provider === "bedrock") {
        const { aws_bedrock_runtime_endpoint, aws_role_name, aws_session_name, ...values } = value as BedrockFormValues;

        if (values.type === "access_key") {
          await onSubmit({
            aws_access_key_id: values.aws_access_key_id,
            aws_secret_access_key: values.aws_secret_access_key,
            aws_bedrock_runtime_endpoint: aws_bedrock_runtime_endpoint,
            aws_role_name: aws_role_name,
            aws_session_name: aws_session_name,
          });
        }

        if (values.type === "api_key") {
          await onSubmit({
            api_key: values.api_key,
            aws_bedrock_runtime_endpoint: aws_bedrock_runtime_endpoint,
            aws_role_name: aws_role_name,
            aws_session_name: aws_session_name,
          });
        }

        return;
      }

      return onSubmit({
        ...value,
      });
    },
  });

  return (
    <form
      className="contents"
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        form.handleSubmit();
      }}
    >
      <DialogContent dividers>
        {["anthropic", "openai", "gemini"].includes(provider) && (
          <APIKeyFields
            form={form}
            fields={{
              api_key: "api_key",
            }}
          />
        )}
        {provider === "vertex_ai" && (
          <VertexAIFields
            form={form}
            fields={{
              project_id: "project_id",
              region: "region",
              gcp_service_account_credentials: "gcp_service_account_credentials",
            }}
          />
        )}
        {provider === "bedrock" && (
          <BedrockFields
            form={form}
            fields={{
              type: "type",
              api_key: "api_key",
              aws_access_key_id: "aws_access_key_id",
              aws_secret_access_key: "aws_secret_access_key",
              aws_bedrock_runtime_endpoint: "aws_bedrock_runtime_endpoint",
              aws_role_name: "aws_role_name",
              aws_session_name: "aws_session_name",
            }}
          />
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <form.Subscribe selector={(state) => [state.canSubmit, state.isSubmitting]}>
          {([canSubmit, isSubmitting]) => (
            <Button type="submit" disabled={!canSubmit} loading={isSubmitting}>
              Save
            </Button>
          )}
        </form.Subscribe>
      </DialogActions>
    </form>
  );
};
