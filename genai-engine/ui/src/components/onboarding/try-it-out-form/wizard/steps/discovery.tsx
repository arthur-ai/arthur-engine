import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import BoltIcon from "@mui/icons-material/Bolt";
import { Box, Button, Chip, FormControl, FormHelperText, FormLabel, Stack, TextField, Typography } from "@mui/material";

import { ATTRIBUTION_OPTIONS, COMPETITOR_OPTIONS } from "../../../onboarding-options";
import { chipSx, fieldErrorMessage, sectionLabelSx, textFieldSx } from "../../styles";
import { STEP_HEADINGS } from "../options";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyApi = any;

export interface DiscoveryStepProps {
  form: AnyApi;
  group: AnyApi;
  onBack: () => void;
  isSubmitting: boolean;
}

export const TryItOutFormWizardDiscoveryStep: React.FC<DiscoveryStepProps> = ({ form, group, onBack, isSubmitting }) => {
  const heading = STEP_HEADINGS[2];

  return (
    <Box
      component="form"
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void group.handleSubmit();
      }}
    >
      <Stack spacing={2.25}>
        <Box>
          <Typography component="h2" sx={{ fontSize: 18, fontWeight: 700, color: "text.primary", lineHeight: 1.3, mb: 0.5 }}>
            {heading.title}
          </Typography>
          <Typography sx={{ fontSize: 13, color: "text.secondary", lineHeight: 1.5 }}>{heading.subtitle}</Typography>
        </Box>

        <form.Field name="discovery.competitors">
          {(field: AnyApi) => {
            const value: string[] = field.state.value;
            const errorMessage = fieldErrorMessage(field);
            const toggle = (id: string) => {
              const opt = COMPETITOR_OPTIONS.find((o) => o.id === id);
              if (!opt) return;
              if (opt.exclusive) {
                field.handleChange(value.includes(id) ? [] : [id]);
                return;
              }
              const next = value.includes(id) ? value.filter((x) => x !== id) : [...value, id];
              field.handleChange(
                next.filter((x) => {
                  const o = COMPETITOR_OPTIONS.find((c) => c.id === x);
                  return !o?.exclusive;
                })
              );
            };
            return (
              <FormControl error={!!errorMessage} component="fieldset" sx={{ width: "100%" }}>
                <Stack direction="row" alignItems="baseline" spacing={1} sx={{ mb: 1 }}>
                  <FormLabel component="legend" sx={{ ...sectionLabelSx, "&.Mui-focused": { color: sectionLabelSx.color } }}>
                    Have you used any of these tools before?
                  </FormLabel>
                  <Typography sx={{ fontSize: 11, fontWeight: 400, color: "text.secondary" }}>Select all that apply</Typography>
                </Stack>
                <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1 }}>
                  {COMPETITOR_OPTIONS.map((opt) => {
                    const on = value.includes(opt.id);
                    return <Chip key={opt.id} label={opt.label} clickable onClick={() => toggle(opt.id)} variant="outlined" sx={chipSx(on)} />;
                  })}
                </Stack>
                {errorMessage && <FormHelperText sx={{ mx: 0, mt: 0.75, fontSize: 12, fontWeight: 500 }}>{errorMessage}</FormHelperText>}
              </FormControl>
            );
          }}
        </form.Field>

        <form.Subscribe selector={(s: AnyApi) => s.values.discovery.competitors.includes("other")}>
          {(show: boolean) =>
            show ? (
              <form.Field name="discovery.competitorOther">
                {(field: AnyApi) => (
                  <TextField
                    placeholder="Which other tool(s)?"
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
              </form.Field>
            ) : null
          }
        </form.Subscribe>

        <form.Field name="discovery.attribution">
          {(field: AnyApi) => {
            const errorMessage = fieldErrorMessage(field);
            return (
              <FormControl error={!!errorMessage} component="fieldset" sx={{ width: "100%" }}>
                <FormLabel component="legend" sx={{ ...sectionLabelSx, mb: 1, "&.Mui-focused": { color: sectionLabelSx.color } }}>
                  How did you hear about Arthur?
                </FormLabel>
                <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1 }}>
                  {ATTRIBUTION_OPTIONS.map((opt) => {
                    const on = field.state.value === opt.id;
                    return (
                      <Chip key={opt.id} label={opt.label} clickable onClick={() => field.handleChange(opt.id)} variant="outlined" sx={chipSx(on)} />
                    );
                  })}
                </Stack>
                {errorMessage && <FormHelperText sx={{ mx: 0, mt: 0.75, fontSize: 12, fontWeight: 500 }}>{errorMessage}</FormHelperText>}
              </FormControl>
            );
          }}
        </form.Field>

        <form.Subscribe selector={(s: AnyApi) => s.values.discovery.attribution === "other"}>
          {(show: boolean) =>
            show ? (
              <form.Field name="discovery.attributionOther">
                {(field: AnyApi) => (
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
              </form.Field>
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
          <Button
            type="submit"
            variant="contained"
            color="primary"
            size="large"
            disabled={isSubmitting}
            disableElevation
            endIcon={<ArrowForwardIcon sx={{ fontSize: 16 }} />}
            sx={{ textTransform: "none", fontSize: 15, fontWeight: 600, borderRadius: "8px", px: 3 }}
          >
            Start the demo
          </Button>
        </Stack>

        <Stack direction="row" alignItems="center" spacing={1} sx={{ mt: 0.25 }}>
          <BoltIcon sx={{ fontSize: 14, color: "secondary.main" }} />
          <Typography sx={{ fontSize: 12, color: "text.secondary" }}>Your demo task is yours alone. The API key is scoped to it.</Typography>
        </Stack>
      </Stack>
    </Box>
  );
};
