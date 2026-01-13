import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import { Box, Button, ButtonGroup, Chip, CircularProgress, Stack, Typography } from "@mui/material";
import { Link as MuiLink } from "@mui/material";
import { Link } from "react-router-dom";

import { agentNotebookStateFormOpts } from "../../form";
import { useMetaStore } from "../../store/meta.store";
import { SubmitButton } from "../submit-button";

import { withForm } from "@/components/traces/components/filtering/hooks/form";
import { AgenticNotebookDetail } from "@/lib/api-client/api-client";
import { formatDate } from "@/utils/formatters";

type Props = {
  notebook: AgenticNotebookDetail;
  onLoadConfig: () => void;
  isSaving: boolean;
};

export const Header = withForm({
  ...agentNotebookStateFormOpts,
  props: {} as Props,
  render: function Render({ form, notebook, onLoadConfig, isSaving }) {
    const edited = useMetaStore((state) => state.edited);

    return (
      <Box
        sx={{
          px: 3,
          pt: 3,
          pb: 2,
          borderBottom: 1,
          borderColor: "divider",
          backgroundColor: "background.paper",
        }}
      >
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Stack alignItems="flex-start">
            <Button
              size="small"
              component={Link}
              to=".."
              variant="text"
              startIcon={<ArrowBackIcon />}
              color="inherit"
              sx={{ color: "text.primary", mb: 2 }}
            >
              Back to Notebooks
            </Button>
            <Stack mb={1}>
              <Typography variant="h5" color="text.primary" fontWeight="bold">
                {notebook.name}
              </Typography>
              <Stack direction="row" alignItems="center" gap={1}>
                {edited && (
                  <Chip
                    label={
                      <Stack direction="row" alignItems="center" gap={1}>
                        {isSaving ? <CircularProgress size={12} color="inherit" /> : null}
                        Edited
                      </Stack>
                    }
                    color="primary"
                    size="small"
                  />
                )}
                <Typography variant="body2" color="text.secondary">
                  {notebook.description}
                </Typography>
              </Stack>
              <Stack direction="row" gap={2}>
                <Typography variant="body2" color="text.secondary">
                  <span className="font-bold">Created:</span> {formatDate(notebook?.created_at)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <span className="font-bold">Updated:</span> {formatDate(notebook.updated_at)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <span className="font-bold">Runs:</span>{" "}
                  <MuiLink component={Link} to={`?show=history`}>
                    {notebook.experiments.length} run(s)
                  </MuiLink>
                </Typography>
              </Stack>
            </Stack>
          </Stack>

          <ButtonGroup size="small" disabled={isSaving}>
            <SubmitButton form={form} />
            <Button onClick={onLoadConfig} startIcon={<FileDownloadIcon />}>
              Load Config
            </Button>
          </ButtonGroup>
        </Stack>
      </Box>
    );
  },
});
