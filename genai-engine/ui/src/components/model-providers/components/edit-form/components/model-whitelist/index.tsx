import InfoOutlined from "@mui/icons-material/InfoOutlined";
import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import FormControlLabel from "@mui/material/FormControlLabel";
import Paper from "@mui/material/Paper";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import React from "react";

import { useModelWhitelist } from "../../../../hooks/useModelWhitelist";

import { ModelProvider } from "@/lib/api-client/api-client";

type Props = {
  provider: ModelProvider;
  providerDisplayName: string;
  providerEnabled: boolean;
  value: string[] | null;
  dirty: boolean;
  onChange: (models: string[] | null) => void;
};

export const ModelWhitelistSection: React.FC<Props> = ({ provider, providerDisplayName, providerEnabled, value, dirty, onChange }) => {
  // vLLM's models live on the server itself and can only be read from a stored
  // api_base. Every other provider has a static catalog.
  const catalogUnavailable = provider === "hosted_vllm" && !providerEnabled;

  const { data, isLoading, error } = useModelWhitelist(provider, !catalogUnavailable);

  const models = dirty ? value : (data?.whitelist ?? null);
  const restricted = models !== null;

  if (catalogUnavailable) {
    return null;
  }

  return (
    <Box sx={{ mt: 2 }}>
      <Divider sx={{ mb: 2 }} />
      <Typography variant="subtitle2" color="text.secondary">
        Visible models
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
        Controls what appears in model pickers across the app.
      </Typography>

      {isLoading && <CircularProgress size={20} />}

      {error && (
        <Alert severity="error" sx={{ mt: 1 }}>
          Couldn&apos;t load {providerDisplayName} models. Save your credentials first, then reopen this dialog to choose which models to show.
        </Alert>
      )}

      {!isLoading && !error && data && (
        <>
          <RadioGroup value={restricted ? "some" : "all"} onChange={(event) => onChange(event.target.value === "all" ? null : [])} sx={{ gap: 0.5 }}>
            <FormControlLabel
              value="all"
              control={<Radio size="small" />}
              label={
                <Stack>
                  <Typography variant="body2">All models</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Show everything {providerDisplayName} offers
                  </Typography>
                </Stack>
              }
            />
            <FormControlLabel
              value="some"
              control={<Radio size="small" />}
              label={
                <Stack>
                  <Typography variant="body2">Only selected</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Pick the models your team uses.
                  </Typography>
                </Stack>
              }
            />
          </RadioGroup>

          {restricted && (
            <Stack spacing={1} sx={{ mt: 1 }}>
              <Autocomplete
                multiple
                size="small"
                options={data.catalog}
                value={models}
                onChange={(_event, next) => onChange(next)}
                disableCloseOnSelect
                // PaperComponent rather than ListboxComponent: the listbox is the
                // scrolling element, so a sticky child of it would scroll away.
                PaperComponent={({ children, ...paperProps }) => (
                  <Paper {...paperProps}>
                    <Stack direction="row" spacing={0.75} sx={{ alignItems: "flex-start", px: 1.5, py: 1, borderBottom: 1, borderColor: "divider" }}>
                      <InfoOutlined sx={{ fontSize: 15, color: "text.disabled", mt: 0.25 }} />
                      <Typography variant="caption" color="text.secondary">
                        This list is everything {providerDisplayName} publishes, including models your account may not have access to.
                      </Typography>
                    </Stack>
                    {children}
                  </Paper>
                )}
                // MUI packs tags into the input by default, displacing the placeholder
                // and reflowing the field. Chips render below it instead.
                renderTags={() => null}
                renderInput={(params) => <TextField {...params} placeholder={`Search ${providerDisplayName} models…`} size="small" />}
              />

              {models.length > 0 && (
                <Stack direction="row" flexWrap="wrap" gap={0.75}>
                  {models.map((model) => (
                    <Chip key={model} label={model} size="small" onDelete={() => onChange(models.filter((m) => m !== model))} />
                  ))}
                </Stack>
              )}

              {models.length === 0 && <Alert severity="warning">Select at least one model</Alert>}
            </Stack>
          )}
        </>
      )}
    </Box>
  );
};
