import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import FormControl from "@mui/material/FormControl";
import FormLabel from "@mui/material/FormLabel";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { ALWAYS_THINKING_HINT, reasoningSettingsError, type ReasoningSettings, type ThinkingMode } from "./reasoningSettings";

import { MIN_THINKING_BUDGET_TOKENS, REASONING_EFFORT_OPTIONS, takesThinking, thinkingAlwaysOn } from "@/constants/reasoning";
import type { ModelProvider, ReasoningEffortEnum } from "@/lib/api-client/api-client";

// "default" means the same as leaving the setting unset, and litellm rejects it
// for Claude, so the eval editor offers only the unset option for it.
const EFFORT_CHOICES = REASONING_EFFORT_OPTIONS.filter((effort) => effort !== "default");

const THINKING_CHOICES: { value: Exclude<ThinkingMode, "">; label: string }[] = [
  { value: "disabled", label: "Off" },
  { value: "adaptive", label: "Adaptive" },
  { value: "enabled", label: "On, with a token budget" },
];

const UNSET_LABEL = "Provider default";

interface ReasoningSettingsFieldsProps {
  value: ReasoningSettings;
  onChange: (value: ReasoningSettings) => void;
  provider: ModelProvider | "";
  modelName: string;
  disabled?: boolean;
}

const ReasoningSettingsFields = ({ value, onChange, provider, modelName, disabled = false }: ReasoningSettingsFieldsProps) => {
  const showThinking = takesThinking(provider, modelName);
  // On always-thinking models "none" and "Off" are kept visible but disabled, so a
  // saved eval that has one still shows it, with the error explaining why.
  const alwaysOn = thinkingAlwaysOn(modelName);
  const settingsError = reasoningSettingsError(value, provider, modelName);
  const budgetError = value.thinkingMode === "enabled" && settingsError !== ALWAYS_THINKING_HINT ? settingsError : null;

  return (
    <FormControl fullWidth>
      <FormLabel>
        <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
          Reasoning
        </Typography>
      </FormLabel>
      <Box sx={{ display: "flex", gap: 2 }}>
        <TextField
          select
          fullWidth
          size="small"
          label="Reasoning effort"
          value={value.reasoningEffort}
          onChange={(e) => onChange({ ...value, reasoningEffort: e.target.value as ReasoningEffortEnum | "" })}
          disabled={disabled}
          slotProps={{ select: { displayEmpty: true }, inputLabel: { shrink: true } }}
          sx={{ backgroundColor: "background.paper" }}
        >
          <MenuItem value="">
            <Typography component="span" sx={{ color: "text.secondary" }}>
              {UNSET_LABEL}
            </Typography>
          </MenuItem>
          {EFFORT_CHOICES.map((effort) => (
            <MenuItem key={effort} value={effort} disabled={alwaysOn && effort === "none"}>
              {effort}
            </MenuItem>
          ))}
        </TextField>
        {showThinking && (
          <TextField
            select
            fullWidth
            size="small"
            label="Thinking"
            value={value.thinkingMode}
            onChange={(e) => onChange({ ...value, thinkingMode: e.target.value as ThinkingMode })}
            disabled={disabled}
            slotProps={{ select: { displayEmpty: true }, inputLabel: { shrink: true } }}
            sx={{ backgroundColor: "background.paper" }}
          >
            <MenuItem value="">
              <Typography component="span" sx={{ color: "text.secondary" }}>
                {UNSET_LABEL}
              </Typography>
            </MenuItem>
            {THINKING_CHOICES.map((choice) => (
              <MenuItem key={choice.value} value={choice.value} disabled={alwaysOn && choice.value === "disabled"}>
                {choice.label}
              </MenuItem>
            ))}
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
      <Typography variant="caption" sx={{ color: "text.secondary", mt: 0.5 }}>
        Leave a setting on {UNSET_LABEL.toLowerCase()} to use the model provider&apos;s default for evals, or the model&apos;s own default if the
        provider has none.{showThinking && !alwaysOn ? " Thinking off turns extended thinking off explicitly." : ""}
      </Typography>
      {alwaysOn && (
        <Alert severity={settingsError === ALWAYS_THINKING_HINT ? "error" : "info"} sx={{ mt: 1 }}>
          {ALWAYS_THINKING_HINT}
        </Alert>
      )}
    </FormControl>
  );
};

export default ReasoningSettingsFields;
