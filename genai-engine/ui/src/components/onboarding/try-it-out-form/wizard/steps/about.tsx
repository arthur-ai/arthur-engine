import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import CheckIcon from "@mui/icons-material/Check";
import { Box, Button, FormControl, FormControlLabel, FormHelperText, FormLabel, Radio, RadioGroup, Stack, Typography } from "@mui/material";

import { BRINGS_OPTIONS, MATURITY_OPTIONS } from "../../../onboarding-options";
import { withForm } from "../../hooks/form";
import { OtherSpecifyField } from "../../other-specify-field";
import { fieldErrorMessage, radioCardSx, sectionLabelSx } from "../../styles";
import { STEP_HEADINGS } from "../options";
import { aboutSchema, wizardFormOpts } from "../schema";

export const TryItOutFormWizardAboutStep = withForm({
  ...wizardFormOpts,
  props: {
    onBack: () => {},
    onAdvance: () => {},
    onInvalid: () => {},
  },
  render: function Render({ form, onBack, onAdvance, onInvalid }) {
    const heading = STEP_HEADINGS[1];

    return (
      <form.FormGroup name="about" validators={{ onDynamic: aboutSchema }} onGroupSubmit={onAdvance} onGroupSubmitInvalid={onInvalid}>
        {(formGroup) => (
          <Box
            component="form"
            onSubmit={(e) => {
              e.preventDefault();
              e.stopPropagation();
              void formGroup.handleSubmit();
            }}
          >
            <Stack spacing={2.25}>
              <Box>
                <Typography component="h2" sx={{ fontSize: 18, fontWeight: 700, color: "text.primary", lineHeight: 1.3, mb: 0.5 }}>
                  {heading.title}
                </Typography>
                <Typography sx={{ fontSize: 13, color: "text.secondary", lineHeight: 1.5 }}>{heading.subtitle}</Typography>
              </Box>

              <form.AppField name="about.maturity">
                {(field) => {
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
              </form.AppField>

              <form.AppField name="about.brings">
                {(field) => {
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
              </form.AppField>

              <form.Subscribe selector={(s) => s.values.about.brings === "other"}>
                {(show) =>
                  show ? (
                    <form.AppField name="about.bringsOther">
                      {(field) => <OtherSpecifyField field={field} placeholder="Please specify…" />}
                    </form.AppField>
                  ) : null
                }
              </form.Subscribe>

              <Stack direction="row" spacing={1.5} sx={{ mt: 0.5 }}>
                <Button
                  type="button"
                  onClick={onBack}
                  variant="text"
                  startIcon={<ArrowBackIcon sx={{ fontSize: 16 }} />}
                  sx={{ textTransform: "none", fontSize: 14, fontWeight: 500, color: "text.secondary" }}
                >
                  Back
                </Button>
                <Box sx={{ flex: 1 }} />
                <form.Subscribe selector={(s) => aboutSchema.safeParse(s.values.about).success}>
                  {(isValid) => (
                    <Button
                      type="submit"
                      variant="contained"
                      color="primary"
                      disabled={!isValid}
                      disableElevation
                      endIcon={<ArrowForwardIcon sx={{ fontSize: 16 }} />}
                      sx={{ textTransform: "none", fontSize: 14, fontWeight: 600, borderRadius: "8px", px: 2.5 }}
                    >
                      Continue
                    </Button>
                  )}
                </form.Subscribe>
              </Stack>
            </Stack>
          </Box>
        )}
      </form.FormGroup>
    );
  },
});
