import { DialogContent, DialogContentText, DialogTitle, Link } from "@mui/material";

import { ModelProvider } from "@/lib/api-client/api-client";

export const ConfirmationDialog = ({ provider }: { provider: ModelProvider }) => {
  const config = CONFIRMATIONS[provider as keyof typeof CONFIRMATIONS] ?? null;

  if (!config) {
    return null;
  }

  const { title, body } = config;

  return (
    <>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>{body}</DialogContent>
    </>
  );
};

const CONFIRMATIONS = {
  bedrock: {
    title: "Fallback to default credentials?",
    body: (
      <>
        <DialogContentText>No API Key or AWS Credentials were provided. The engine will attempt to use default credentials.</DialogContentText>
        <DialogContentText sx={{ mt: 2 }}>
          This requires that your environment has valid AWS credentials configured. If no valid credentials are available, calls to Bedrock will fail.
        </DialogContentText>
        <DialogContentText sx={{ mt: 2 }}>Do you want to proceed with this configuration?</DialogContentText>
      </>
    ),
  },
  vertex_ai: {
    title: "Use Application Default Credentials?",
    body: (
      <>
        <DialogContentText>
          No credentials file was provided. The engine will attempt to use{" "}
          <Link href="https://cloud.google.com/docs/authentication/application-default-credentials" target="_blank" rel="noopener">
            Application Default Credentials
          </Link>
          .
        </DialogContentText>
        <DialogContentText sx={{ mt: 2 }}>
          This requires that your environment has valid GCP credentials configured (e.g., through gcloud CLI or an attached service account). If no
          valid credentials are available, calls to Vertex AI will fail.
        </DialogContentText>
        <DialogContentText sx={{ mt: 2 }}>Do you want to proceed with this configuration?</DialogContentText>
      </>
    ),
  },
};
