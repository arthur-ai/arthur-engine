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
  /** null means every model is exposed. An array — including empty — means restricted. */
  value: string[] | null;
  onChange: (models: string[] | null) => void;
  /** Fired once when the stored whitelist arrives, so the parent can seed its state. */
  onInitialValue: (models: string[] | null) => void;
};

export const ModelWhitelistSection: React.FC<Props> = ({ provider, providerDisplayName, value, onChange, onInitialValue }) => {
  const { data, isLoading, error } = useModelWhitelist(provider, true);

  // Seed the parent from the fetch exactly once. A ref rather than an effect: this
  // is a one-shot handoff, not a subscription to an external system.
  const seeded = React.useRef(false);
  if (data && !seeded.current) {
    seeded.current = true;
    onInitialValue(data.whitelist ?? null);
  }

  const restricted = value !== null;
  const hiddenCount = restricted && data ? data.catalog.length - value.length : 0;

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
          <RadioGroup value={restricted ? "some" : "all"} onChange={(event) => onChange(event.target.value === "all" ? null : [])}>
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
                value={value}
                onChange={(_event, next) => onChange(next)}
                disableCloseOnSelect
                // The catalog is LiteLLM's static model map, which says nothing about what
                // this account is entitled to. It lives inside the dropdown, pinned above
                // the options, so it is read at the moment of choosing rather than skimmed
                // past. PaperComponent rather than ListboxComponent: the listbox is the
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
                renderTags={(selected, getTagProps) =>
                  selected.map((model, index) => {
                    const { key, ...tagProps } = getTagProps({ index });
                    return <Chip key={key} label={model} size="small" {...tagProps} />;
                  })
                }
                renderInput={(params) => <TextField {...params} placeholder={`Search ${providerDisplayName} models…`} size="small" />}
              />
              {value.length === 0 && <Alert severity="warning">Select at least one model</Alert>}
              {hiddenCount > 0 && (
                <Alert severity="info">
                  {hiddenCount} {hiddenCount === 1 ? "model" : "models"} will be hidden. Existing configurations using them keep working, but the
                  model will no longer appear in pickers.
                </Alert>
              )}
            </Stack>
          )}
        </>
      )}
    </Box>
  );
};
