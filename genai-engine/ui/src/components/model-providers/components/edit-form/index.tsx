import { useAppForm } from "@arthur/shared-components";
import { Button, Dialog, DialogActions, DialogContent } from "@mui/material";
import { useState } from "react";

import { APIKeyFields } from "./components/api";
import { BedrockFields } from "./components/bedrock";
import { ConfirmationDialog } from "./components/confirmation-dialog";
import { VertexAIFields } from "./components/vertex";
import { VllmFields } from "./components/vllm";
import { BedrockFormValues, editFormOptions, VertexAIFormValues, VllmFormValues } from "./form";
import { parseCredentials } from "./utils";

import { ModelProvider, PutModelProviderCredentials } from "@/lib/api-client/api-client";

type Props = {
  provider: ModelProvider;
  onSubmit: (data: PutModelProviderCredentials) => Promise<void>;
  onClose: () => void;
};

export const EditForm = ({ provider, onSubmit, onClose }: Props) => {
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [pendingSubmitData, setPendingSubmitData] = useState<PutModelProviderCredentials | null>(null);

  const handleConfirmedSubmit = async () => {
    if (pendingSubmitData) {
      await onSubmit(pendingSubmitData);
      setShowConfirmDialog(false);
      setPendingSubmitData(null);
    }
  };

  const form = useAppForm({
    ...editFormOptions(provider),
    onSubmit: async ({ value, formApi }) => {
      if (provider === "vertex_ai") {
        const { gcp_service_account_credentials, ...rest } = value as VertexAIFormValues;

        // If no credentials file provided, show confirmation dialog
        if (!gcp_service_account_credentials) {
          setPendingSubmitData({
            ...rest,
          });
          setShowConfirmDialog(true);
          return;
        }

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
          if (!values.aws_access_key_id || !values.aws_secret_access_key) {
            setPendingSubmitData({
              ...values,
            });
            setShowConfirmDialog(true);
            return;
          }

          await onSubmit({
            aws_access_key_id: values.aws_access_key_id,
            aws_secret_access_key: values.aws_secret_access_key,
            aws_bedrock_runtime_endpoint: aws_bedrock_runtime_endpoint,
            aws_role_name: aws_role_name,
            aws_session_name: aws_session_name,
          });
        }

        if (values.type === "api_key") {
          if (!values.api_key) {
            setPendingSubmitData({
              ...values,
            });
            setShowConfirmDialog(true);
            return;
          }

          await onSubmit({
            api_key: values.api_key,
            aws_bedrock_runtime_endpoint: aws_bedrock_runtime_endpoint,
            aws_role_name: aws_role_name,
            aws_session_name: aws_session_name,
          });
        }

        return;
      }

      if (provider === "hosted_vllm") {
        const values = value as VllmFormValues;

        if (!values.api_base) {
          formApi.setFieldMeta("api_base", (old) => ({
            ...old,
            errorMap: { onSubmit: { message: "API Base URL is required" } },
          }));
          return;
        }

        return onSubmit({
          api_base: values.api_base,
          api_key: values.api_key || undefined,
        });
      }

      return onSubmit({
        ...value,
      });
    },
  });

  return (
    <>
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
          {provider === "hosted_vllm" && (
            <VllmFields
              form={form}
              fields={{
                api_base: "api_base",
                api_key: "api_key",
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

      {/* Confirmation Dialog for Application Default Credentials */}
      <Dialog open={showConfirmDialog} onClose={() => setShowConfirmDialog(false)} maxWidth="sm" fullWidth>
        <ConfirmationDialog provider={provider} />
        <DialogActions>
          <Button onClick={() => setShowConfirmDialog(false)}>Cancel</Button>
          <Button onClick={handleConfirmedSubmit} variant="contained" color="primary">
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
