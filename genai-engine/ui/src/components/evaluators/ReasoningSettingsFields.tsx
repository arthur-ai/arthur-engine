import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import FormControl from "@mui/material/FormControl";
import FormLabel from "@mui/material/FormLabel";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import {
  effortChoices,
  reasoningSettingsError,
  thinkingCannotBeDisabled,
  thinkingChoices,
  thinkingOffHint,
  thinkingShown,
  type ReasoningSettings,
  type ThinkingMode,
} from "./reasoningSettings";

import { MIN_THINKING_BUDGET_TOKENS } from "@/constants/reasoning";
import type { ModelReasoningOptions, ModelThinkingOptionsTypesEnum, ReasoningEffortEnum } from "@/lib/api-client/api-client";

const THINKING_LABELS: Record<ModelThinkingOptionsTypesEnum, string> = {
  disabled: "Off",
  adaptive: "Adaptive",
  enabled: "On, with a token budget",
};

const UNSET_LABEL = "Provider default";

interface ReasoningSettingsFieldsProps {
  value: ReasoningSettings;
  onChange: (value: ReasoningSettings) => void;
  // Undefined until a model is chosen and its options load.
  options: ModelReasoningOptions | undefined;
  modelChosen: boolean;
  disabled?: boolean;
}

const ReasoningSettingsFields = ({ value, onChange, options, modelChosen, disabled = false }: ReasoningSettingsFieldsProps) => {
  const efforts = effortChoices(options);
  const showEffort = efforts.length > 0 || value.reasoningEffort !== "";
  const showThinking = thinkingShown(options);
  const thinkingTypes = thinkingChoices(options);
  const settingsError = reasoningSettingsError(value, options);
  const budgetError = value.thinkingMode === "enabled" && thinkingTypes.includes("enabled") ? settingsError : null;
  // A saved value the model no longer accepts stays visible, disabled, with the error.
  const staleEffort = value.reasoningEffort !== "" && !efforts.includes(value.reasoningEffort) ? value.reasoningEffort : null;
  const staleThinking = value.thinkingMode !== "" && !thinkingTypes.includes(value.thinkingMode) ? value.thinkingMode : null;
  const unknownModel = modelChosen && options !== undefined && options.reasoning_efforts === null && options.thinking.supported === null;

  if (!modelChosen) {
    return null;
  }

  return (
    <FormControl fullWidth>
      <FormLabel>
        <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
          Reasoning
        </Typography>
      </FormLabel>
      {!showEffort && !showThinking ? (
        <Typography variant="body2" sx={{ color: "text.secondary" }}>
          This model doesn&apos;t take reasoning settings.
        </Typography>
      ) : (
        <Box sx={{ display: "flex", gap: 2 }}>
          {showEffort && (
            <TextField
              select
              fullWidth
              size="small"
              label="Reasoning effort"
              value={value.reasoningEffort}
              onChange={(e) => onChange({ ...value, reasoningEffort: e.target.value as ReasoningEffortEnum | "" })}
              disabled={disabled}
              error={staleEffort !== null}
              slotProps={{ select: { displayEmpty: true }, inputLabel: { shrink: true } }}
              sx={{ backgroundColor: "background.paper" }}
            >
              <MenuItem value="">
                <Typography component="span" sx={{ color: "text.secondary" }}>
                  {UNSET_LABEL}
                </Typography>
              </MenuItem>
              {efforts.map((effort) => (
                <MenuItem key={effort} value={effort}>
                  {effort}
                </MenuItem>
              ))}
              {staleEffort && (
                <MenuItem value={staleEffort} disabled>
                  {staleEffort}
                </MenuItem>
              )}
            </TextField>
          )}
          {showThinking && (
            <TextField
              select
              fullWidth
              size="small"
              label="Thinking"
              value={value.thinkingMode}
              onChange={(e) => onChange({ ...value, thinkingMode: e.target.value as ThinkingMode })}
              disabled={disabled}
              error={staleThinking !== null}
              slotProps={{ select: { displayEmpty: true }, inputLabel: { shrink: true } }}
              sx={{ backgroundColor: "background.paper" }}
            >
              <MenuItem value="">
                <Typography component="span" sx={{ color: "text.secondary" }}>
                  {UNSET_LABEL}
                </Typography>
              </MenuItem>
              {thinkingTypes.map((type) => (
                <MenuItem key={type} value={type}>
                  {THINKING_LABELS[type]}
                </MenuItem>
              ))}
              {staleThinking && (
                <MenuItem value={staleThinking} disabled>
                  {THINKING_LABELS[staleThinking]}
                </MenuItem>
              )}
            </TextField>
          )}
          {showThinking && value.thinkingMode === "enabled" && (
            <TextField
              fullWidth
              size="small"
              type="number"
              label="Thinking budget (tokens)"
              value={value.budgetTokens}
              onChange={(e) => onChange({ ...value, budgetTokens: e.target.value })}
              disabled={disabled}
              error={budgetError !== null}
              helperText={budgetError}
              slotProps={{ htmlInput: { min: MIN_THINKING_BUDGET_TOKENS, step: 256 } }}
              sx={{ backgroundColor: "background.paper" }}
            />
          )}
        </Box>
      )}
      <Typography variant="caption" sx={{ color: "text.secondary", mt: 0.5 }}>
        Leave a setting on {UNSET_LABEL.toLowerCase()} to use the model provider&apos;s default for evals, or the model&apos;s own default if the
        provider has none.
        {thinkingTypes.includes("disabled") && showThinking ? " Thinking off turns extended thinking off explicitly." : ""}
        {unknownModel ? " The settings this model accepts aren't known, so they are sent as set." : ""}
      </Typography>
      {settingsError && settingsError !== budgetError ? (
        <Alert severity="error" sx={{ mt: 1 }}>
          {settingsError}
        </Alert>
      ) : (
        thinkingCannotBeDisabled(options) && (
          <Alert severity="info" sx={{ mt: 1 }}>
            {thinkingOffHint(options)}
          </Alert>
        )
      )}
    </FormControl>
  );
};

export default ReasoningSettingsFields;
