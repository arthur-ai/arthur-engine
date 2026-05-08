import {
  Alert,
  Autocomplete,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import React, { useMemo, useState } from "react";

import { PII_ENTITY_VALUES, RULE_TYPES_ORDERED, RULE_TYPE_META } from "./ruleTypeConfig";

import type { ExampleConfig, KeywordsConfig, NewRuleRequest, PIIConfig, PIIEntityTypes, RegexConfig, RuleType } from "@/lib/api-client/api-client";

interface CreateRuleDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (rule: NewRuleRequest) => Promise<void>;
  submitting: boolean;
  error: string | null;
}

const splitLines = (raw: string): string[] =>
  raw
    .split("\n")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);

export const CreateRuleDialog: React.FC<CreateRuleDialogProps> = ({ open, onClose, onSubmit, submitting, error }) => {
  const [name, setName] = useState("");
  const [type, setType] = useState<RuleType>("KeywordRule");
  const [applyToPrompt, setApplyToPrompt] = useState(RULE_TYPE_META.KeywordRule.apply_to_prompt.default);
  const [applyToResponse, setApplyToResponse] = useState(RULE_TYPE_META.KeywordRule.apply_to_response.default);

  const [keywordsRaw, setKeywordsRaw] = useState("");
  const [regexRaw, setRegexRaw] = useState("");
  const [disabledPiiEntities, setDisabledPiiEntities] = useState<PIIEntityTypes[]>([]);
  const [allowListRaw, setAllowListRaw] = useState("");
  const [examplesJsonRaw, setExamplesJsonRaw] = useState("");

  const [localError, setLocalError] = useState<string | null>(null);

  const meta = RULE_TYPE_META[type];

  const handleTypeChange = (next: RuleType) => {
    const nextMeta = RULE_TYPE_META[next];
    setType(next);
    setApplyToPrompt(nextMeta.apply_to_prompt.default);
    setApplyToResponse(nextMeta.apply_to_response.default);
    setLocalError(null);
  };

  const buildPayload = (): NewRuleRequest | null => {
    const trimmedName = name.trim();
    if (!trimmedName) {
      setLocalError("Name is required");
      return null;
    }

    const base: NewRuleRequest = {
      name: trimmedName,
      type,
      apply_to_prompt: applyToPrompt,
      apply_to_response: applyToResponse,
    };

    switch (meta.configKind) {
      case "none":
        return base;
      case "keywords": {
        const keywords = splitLines(keywordsRaw);
        if (keywords.length === 0) {
          setLocalError("Add at least one keyword (one per line)");
          return null;
        }
        const config: KeywordsConfig = { keywords };
        return { ...base, config };
      }
      case "regex": {
        const regex_patterns = splitLines(regexRaw);
        if (regex_patterns.length === 0) {
          setLocalError("Add at least one regex pattern (one per line)");
          return null;
        }
        const config: RegexConfig = { regex_patterns };
        return { ...base, config };
      }
      case "pii": {
        const allow_list = splitLines(allowListRaw);
        const config: PIIConfig = {
          disabled_pii_entities: disabledPiiEntities,
          ...(allow_list.length > 0 ? { allow_list } : {}),
        };
        return { ...base, config };
      }
      case "examples_json": {
        const raw = examplesJsonRaw.trim();
        if (!raw) {
          setLocalError("Examples JSON is required for ModelSensitiveDataRule");
          return null;
        }
        try {
          const parsed = JSON.parse(raw) as unknown;
          if (!Array.isArray(parsed)) {
            setLocalError("Examples must be a JSON array");
            return null;
          }
          for (const item of parsed) {
            if (
              typeof item !== "object" ||
              item === null ||
              typeof (item as Record<string, unknown>).example !== "string" ||
              typeof (item as Record<string, unknown>).result !== "boolean"
            ) {
              setLocalError('Each example must be {"example": string, "result": boolean}');
              return null;
            }
          }
          const examples = parsed as ExampleConfig[];
          return { ...base, config: { examples } };
        } catch (e) {
          setLocalError(`Invalid JSON: ${e instanceof Error ? e.message : "parse error"}`);
          return null;
        }
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    const payload = buildPayload();
    if (!payload) return;
    await onSubmit(payload);
  };

  const displayError = localError ?? error;

  const configBlock = useMemo(() => {
    switch (meta.configKind) {
      case "none":
        return (
          <Typography variant="body2" color="text.secondary">
            No additional configuration required for this rule type.
          </Typography>
        );
      case "keywords":
        return (
          <TextField
            label="Keywords"
            placeholder={"one keyword per line\nexample: alert\nexample: warning"}
            value={keywordsRaw}
            onChange={(e) => setKeywordsRaw(e.target.value)}
            multiline
            minRows={4}
            fullWidth
            disabled={submitting}
          />
        );
      case "regex":
        return (
          <TextField
            label="Regex patterns"
            placeholder={"one pattern per line\n\\d{3}-\\d{2}-\\d{4}"}
            value={regexRaw}
            onChange={(e) => setRegexRaw(e.target.value)}
            multiline
            minRows={4}
            fullWidth
            disabled={submitting}
          />
        );
      case "pii":
        return (
          <Stack spacing={2}>
            <Autocomplete
              multiple
              options={PII_ENTITY_VALUES}
              value={disabledPiiEntities}
              onChange={(_, next) => setDisabledPiiEntities(next)}
              renderTags={(values, getTagProps) =>
                values.map((option, index) => {
                  const { key, ...tagProps } = getTagProps({ index });
                  return <Chip key={key} label={option} size="small" {...tagProps} />;
                })
              }
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Disabled PII entities"
                  placeholder="Select entity types to ignore"
                  helperText="Selected entities will NOT trigger a rule failure"
                />
              )}
              disabled={submitting}
            />
            <TextField
              label="Allow list"
              placeholder={"one allowed string per line\narthur.ai"}
              value={allowListRaw}
              onChange={(e) => setAllowListRaw(e.target.value)}
              multiline
              minRows={3}
              fullWidth
              disabled={submitting}
            />
          </Stack>
        );
      case "examples_json":
        return (
          <TextField
            label="Examples (JSON array)"
            placeholder={
              '[\n  {"example": "John has O negative blood group", "result": true},\n  {"example": "Most people have A positive blood group", "result": false}\n]'
            }
            value={examplesJsonRaw}
            onChange={(e) => setExamplesJsonRaw(e.target.value)}
            multiline
            minRows={6}
            fullWidth
            disabled={submitting}
            helperText='Each example: {"example": string, "result": boolean}. result=true means the example is sensitive data.'
            slotProps={{ htmlInput: { style: { fontFamily: "monospace", fontSize: 13 } } }}
          />
        );
    }
  }, [meta.configKind, keywordsRaw, regexRaw, disabledPiiEntities, allowListRaw, examplesJsonRaw, submitting]);

  return (
    <Dialog open={open} onClose={submitting ? undefined : onClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit}>
        <DialogTitle>Create rule</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <TextField label="Name" value={name} onChange={(e) => setName(e.target.value)} fullWidth autoFocus disabled={submitting} />

            <FormControl fullWidth disabled={submitting}>
              <InputLabel id="rule-type-label">Type</InputLabel>
              <Select labelId="rule-type-label" label="Type" value={type} onChange={(e) => handleTypeChange(e.target.value as RuleType)}>
                {RULE_TYPES_ORDERED.map((t) => (
                  <MenuItem key={t} value={t}>
                    {RULE_TYPE_META[t].label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Typography variant="caption" color="text.secondary">
              {meta.description}
            </Typography>

            <Stack direction="row" spacing={2}>
              <FormControlLabel
                control={
                  <Switch
                    checked={applyToPrompt}
                    onChange={(e) => setApplyToPrompt(e.target.checked)}
                    disabled={!meta.apply_to_prompt.allowed || submitting}
                  />
                }
                label="Apply to prompt"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={applyToResponse}
                    onChange={(e) => setApplyToResponse(e.target.checked)}
                    disabled={!meta.apply_to_response.allowed || submitting}
                  />
                }
                label="Apply to response"
              />
            </Stack>

            {configBlock}

            {displayError && <Alert severity="error">{displayError}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button type="submit" variant="contained" disabled={submitting} sx={{ minWidth: 120 }}>
            {submitting ? "Creating..." : "Create rule"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};
