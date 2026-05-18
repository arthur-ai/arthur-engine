import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import CheckIcon from "@mui/icons-material/Check";
import {
  Box,
  Button,
  FormControl,
  FormControlLabel,
  FormHelperText,
  FormLabel,
  Radio,
  RadioGroup,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { BRINGS_OPTIONS, MATURITY_OPTIONS } from "../../../onboarding-options";
import { fieldErrorMessage, radioCardSx, sectionLabelSx, textFieldSx } from "../../styles";
import { STEP_HEADINGS } from "../options";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyGroup = any;

export interface AboutStepProps {
  group: AnyGroup;
  onBack: () => void;
}

export const TryItOutFormWizardAboutStep: React.FC<AboutStepProps> = ({ group, onBack }) => {
  const heading = STEP_HEADINGS[1];

  return (
    <Stack spacing={2.25}>
      <Box>
        <Typography component="h2" sx={{ fontSize: 18, fontWeight: 700, color: "text.primary", lineHeight: 1.3, mb: 0.5 }}>
          {heading.title}
        </Typography>
        <Typography sx={{ fontSize: 13, color: "text.secondary", lineHeight: 1.5 }}>{heading.subtitle}</Typography>
      </Box>

      <group.Field name="maturity">
        {(field: AnyGroup) => {
          const errorMessage = fieldErrorMessage(field);
          return (
            <FormControl error={!!errorMessage} component="fieldset" sx={{ width: "100%" }}>
              <FormLabel component="legend" sx={{ ...sectionLabelSx, mb: 1, "&.Mui-focused": { color: sectionLabelSx.color } }}>
                Where are you in your AI journey?
              </FormLabel>
              <RadioGroup value={field.state.value} onChange={(_, v) => field.handleChange(v)} sx={{ gap: 0.75 }}>
                {MATURITY_OPTIONS.map((opt) => {
                  const selected = field.state.value === opt.id;
                  return (
                    <FormControlLabel
                      key={opt.id}
                      value={opt.id}
                      control={<Radio sx={{ position: "absolute", opacity: 0, pointerEvents: "none" }} />}
                      label={
                        <Stack direction="row" alignItems="center" spacing={1.25} sx={{ width: "100%" }}>
                          <Box
                            sx={{
                              width: 10,
                              height: 10,
                              borderRadius: "999px",
                              backgroundColor: opt.dot,
                              flexShrink: 0,
                            }}
                          />
                          <Box sx={{ flex: 1 }}>{opt.label}</Box>
                          {selected && <CheckIcon sx={{ fontSize: 14, color: "primary.main" }} />}
                        </Stack>
                      }
                      sx={radioCardSx(selected)}
                    />
                  );
                })}
              </RadioGroup>
              {errorMessage && <FormHelperText sx={{ mx: 0, mt: 0.5, fontSize: 12, fontWeight: 500 }}>{errorMessage}</FormHelperText>}
            </FormControl>
          );
        }}
      </group.Field>

      <group.Field name="brings">
        {(field: AnyGroup) => {
          const errorMessage = fieldErrorMessage(field);
          return (
            <FormControl error={!!errorMessage} component="fieldset" sx={{ width: "100%" }}>
              <FormLabel component="legend" sx={{ ...sectionLabelSx, mb: 1, "&.Mui-focused": { color: sectionLabelSx.color } }}>
                What brings you to Arthur today?
              </FormLabel>
              <RadioGroup value={field.state.value} onChange={(_, v) => field.handleChange(v)} sx={{ gap: 0.75 }}>
                {BRINGS_OPTIONS.map((opt) => {
                  const selected = field.state.value === opt.id;
                  return (
                    <FormControlLabel
                      key={opt.id}
                      value={opt.id}
                      control={<Radio size="small" color="primary" sx={{ p: 0, mr: 1.25, "& .MuiSvgIcon-root": { fontSize: 18 } }} />}
                      label={<Box sx={{ flex: 1 }}>{opt.label}</Box>}
                      sx={radioCardSx(selected)}
                    />
                  );
                })}
              </RadioGroup>
              {errorMessage && <FormHelperText sx={{ mx: 0, mt: 0.5, fontSize: 12, fontWeight: 500 }}>{errorMessage}</FormHelperText>}
            </FormControl>
          );
        }}
      </group.Field>

      <group.Subscribe selector={(s: { values: { brings: string } }) => s.values.brings === "other"}>
        {(show: boolean) =>
          show ? (
            <group.Field name="bringsOther">
              {(field: AnyGroup) => (
                <TextField
                  placeholder="Please specify…"
                  value={field.state.value}
                  onBlur={field.handleBlur}
                  onChange={(e) => field.handleChange(e.target.value)}
                  error={field.state.meta.errors.length > 0}
                  helperText={fieldErrorMessage(field)}
                  size="small"
                  fullWidth
                  sx={{ ...textFieldSx, mt: -1 }}
                />
              )}
            </group.Field>
          ) : null
        }
      </group.Subscribe>

      <Stack direction="row" spacing={1.5} sx={{ mt: 0.5 }}>
        <Button
          onClick={onBack}
          variant="text"
          startIcon={<ArrowBackIcon sx={{ fontSize: 16 }} />}
          sx={{ textTransform: "none", fontSize: 14, fontWeight: 500, color: "text.secondary" }}
        >
          Back
        </Button>
        <Box sx={{ flex: 1 }} />
        <Button
          onClick={() => void group.handleSubmit()}
          variant="contained"
          color="primary"
          disableElevation
          endIcon={<ArrowForwardIcon sx={{ fontSize: 16 }} />}
          sx={{ textTransform: "none", fontSize: 14, fontWeight: 600, borderRadius: "8px", px: 2.5 }}
        >
          Continue
        </Button>
      </Stack>
    </Stack>
  );
};
