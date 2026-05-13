import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import BoltIcon from "@mui/icons-material/Bolt";
import CheckIcon from "@mui/icons-material/Check";
import EmailIcon from "@mui/icons-material/Email";
import PersonIcon from "@mui/icons-material/Person";
import {
  Box,
  Button,
  Chip,
  FormControl,
  FormControlLabel,
  FormHelperText,
  FormLabel,
  Paper,
  Radio,
  RadioGroup,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import { useForm, type AnyFieldApi } from "@tanstack/react-form";

import { EngineTopNav } from "../engine-top-nav";
import { ATTRIBUTION_OPTIONS, BRINGS_OPTIONS, COMPETITOR_OPTIONS, MATURITY_OPTIONS } from "../onboarding-options";

import { onboardingSchema } from "./schema";
import type { TryItOutFormProps } from "./types";

export type { TryItOutSubmission } from "./schema";

const labelSx = { fontSize: 13, fontWeight: 500, color: "text.primary" };
const sectionLabelSx = { fontSize: 13, fontWeight: 600, color: "text.primary" };

const textFieldSx = {
  "& .MuiOutlinedInput-root": { borderRadius: "8px", fontSize: 14 },
  "& .MuiOutlinedInput-input": { py: "10px" },
};

const fieldErrorMessage = (field: AnyFieldApi): string | undefined => {
  const err = field.state.meta.errors[0];
  if (!err) return undefined;
  if (typeof err === "string") return err;
  if (typeof err === "object" && err !== null && "message" in err) {
    return String((err as { message: unknown }).message ?? "");
  }
  return undefined;
};

const radioCardSx = (selected: boolean) => (theme: import("@mui/material").Theme) => ({
  m: 0,
  px: 1.5,
  py: 1.25,
  width: "100%",
  border: "1px solid",
  borderRadius: "8px",
  borderColor: selected ? theme.palette.primary.main : theme.palette.divider,
  backgroundColor: selected ? alpha(theme.palette.primary.main, 0.08) : theme.palette.background.paper,
  cursor: "pointer",
  transition: "border-color 0.12s, background 0.12s",
  "&:hover": selected ? {} : { backgroundColor: theme.palette.action.hover },
  "& .MuiFormControlLabel-label": { width: "100%", fontSize: 13, color: theme.palette.text.primary },
});

const chipSx = (selected: boolean) => (theme: import("@mui/material").Theme) => ({
  fontSize: 13,
  fontWeight: 500,
  height: "auto",
  py: 0.875,
  borderRadius: "999px",
  backgroundColor: selected ? alpha(theme.palette.primary.main, 0.08) : theme.palette.background.paper,
  color: selected ? theme.palette.primary.main : theme.palette.text.primary,
  borderColor: selected ? theme.palette.primary.main : theme.palette.divider,
  "& .MuiChip-label": { px: 1.25 },
  "&:hover": selected ? { backgroundColor: alpha(theme.palette.primary.main, 0.08) } : { backgroundColor: theme.palette.action.hover },
});

export const TryItOutForm: React.FC<TryItOutFormProps> = ({ onBack, onSubmit }) => {
  const form = useForm({
    defaultValues: {
      firstName: "",
      lastName: "",
      email: "",
      jobTitle: "",
      company: "",
      building: "",
      maturity: "",
      brings: "",
      bringsOther: "",
      competitors: [] as string[],
      competitorOther: "",
      attribution: "",
    },
    validators: { onSubmit: onboardingSchema },
    onSubmit: ({ value }) => {
      onSubmit(value);
    },
  });

  return (
    <Box sx={{ display: "flex", flexDirection: "column", minHeight: "100vh", backgroundColor: "background.default" }}>
      <EngineTopNav />
      <Box
        sx={{
          flex: 1,
          display: "flex",
          alignItems: "safe center",
          justifyContent: "safe center",
          px: 3,
          py: 4,
          overflowY: "auto",
        }}
      >
        <Box sx={{ width: "100%", maxWidth: 520 }}>
          <Button
            onClick={onBack}
            startIcon={<ArrowBackIcon sx={{ fontSize: 16 }} />}
            sx={{
              textTransform: "none",
              fontSize: 13,
              fontWeight: 500,
              color: "text.secondary",
              p: 0,
              mb: 2.5,
              minWidth: 0,
              "&:hover": { backgroundColor: "transparent", color: "text.primary" },
            }}
          >
            Back
          </Button>

          <Typography component="h1" sx={{ fontSize: 22, fontWeight: 700, color: "text.primary", letterSpacing: "-0.01em", lineHeight: 1.25, mb: 1 }}>
            Try Arthur Engine
          </Typography>
          <Typography sx={{ fontSize: 14, color: "text.secondary", lineHeight: 1.55, mb: 3 }}>
            Tell us who you are and we&apos;ll spin up a demo task scoped just to you.
          </Typography>

          <Paper
            component="form"
            onSubmit={(e) => {
              e.preventDefault();
              e.stopPropagation();
              void form.handleSubmit();
            }}
            elevation={0}
            sx={{
              border: "1px solid",
              borderColor: "divider",
              borderRadius: "12px",
              p: 3.5,
              mt: 1,
              display: "flex",
              flexDirection: "column",
              gap: 2.25,
            }}
          >
            <Stack direction="row" spacing={1.5}>
              <form.Field name="firstName">
                {(field) => (
                  <Stack spacing={0.75} sx={{ flex: 1 }}>
                    <FormLabel htmlFor="eo-firstname" sx={labelSx}>
                      First name
                    </FormLabel>
                    <TextField
                      id="eo-firstname"
                      placeholder="Ada"
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => field.handleChange(e.target.value)}
                      error={field.state.meta.errors.length > 0}
                      helperText={fieldErrorMessage(field)}
                      size="small"
                      fullWidth
                      slotProps={{
                        input: {
                          startAdornment: <PersonIcon sx={{ fontSize: 16, color: "text.disabled", mr: 1 }} />,
                        },
                      }}
                      sx={textFieldSx}
                    />
                  </Stack>
                )}
              </form.Field>
              <form.Field name="lastName">
                {(field) => (
                  <Stack spacing={0.75} sx={{ flex: 1 }}>
                    <FormLabel htmlFor="eo-lastname" sx={labelSx}>
                      Last name
                    </FormLabel>
                    <TextField
                      id="eo-lastname"
                      placeholder="Lovelace"
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => field.handleChange(e.target.value)}
                      error={field.state.meta.errors.length > 0}
                      helperText={fieldErrorMessage(field)}
                      size="small"
                      fullWidth
                      sx={textFieldSx}
                    />
                  </Stack>
                )}
              </form.Field>
            </Stack>

            <form.Field name="email">
              {(field) => (
                <Stack spacing={0.75}>
                  <FormLabel htmlFor="eo-email" sx={labelSx}>
                    Work email
                  </FormLabel>
                  <TextField
                    id="eo-email"
                    placeholder="ada@company.com"
                    value={field.state.value}
                    onBlur={field.handleBlur}
                    onChange={(e) => field.handleChange(e.target.value)}
                    error={field.state.meta.errors.length > 0}
                    helperText={fieldErrorMessage(field)}
                    size="small"
                    fullWidth
                    slotProps={{
                      input: {
                        startAdornment: <EmailIcon sx={{ fontSize: 16, color: "text.disabled", mr: 1 }} />,
                      },
                    }}
                    sx={textFieldSx}
                  />
                </Stack>
              )}
            </form.Field>

            <Stack direction="row" spacing={1.5}>
              <form.Field name="jobTitle">
                {(field) => (
                  <Stack spacing={0.75} sx={{ flex: 1 }}>
                    <FormLabel htmlFor="eo-jobtitle" sx={labelSx}>
                      Job title
                    </FormLabel>
                    <TextField
                      id="eo-jobtitle"
                      placeholder="ML Engineer"
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => field.handleChange(e.target.value)}
                      error={field.state.meta.errors.length > 0}
                      helperText={fieldErrorMessage(field)}
                      size="small"
                      fullWidth
                      sx={textFieldSx}
                    />
                  </Stack>
                )}
              </form.Field>
              <form.Field name="company">
                {(field) => (
                  <Stack spacing={0.75} sx={{ flex: 1 }}>
                    <FormLabel htmlFor="eo-company" sx={labelSx}>
                      Company
                    </FormLabel>
                    <TextField
                      id="eo-company"
                      placeholder="Analytical Engines, Inc."
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => field.handleChange(e.target.value)}
                      error={field.state.meta.errors.length > 0}
                      helperText={fieldErrorMessage(field)}
                      size="small"
                      fullWidth
                      sx={textFieldSx}
                    />
                  </Stack>
                )}
              </form.Field>
            </Stack>

            <form.Field name="building">
              {(field) => (
                <Stack spacing={0.75}>
                  <FormLabel htmlFor="eo-building" sx={labelSx}>
                    What are you building?
                  </FormLabel>
                  <TextField
                    id="eo-building"
                    placeholder="e.g. A customer-support agent that summarises tickets and drafts replies."
                    value={field.state.value}
                    onBlur={field.handleBlur}
                    onChange={(e) => field.handleChange(e.target.value)}
                    error={field.state.meta.errors.length > 0}
                    helperText={fieldErrorMessage(field)}
                    multiline
                    rows={3}
                    fullWidth
                    sx={textFieldSx}
                  />
                </Stack>
              )}
            </form.Field>

            <form.Field name="maturity">
              {(field) => {
                const errorMessage = fieldErrorMessage(field);
                return (
                  <FormControl error={!!errorMessage} component="fieldset" sx={{ width: "100%" }}>
                    <FormLabel component="legend" sx={{ ...sectionLabelSx, mb: 1, "&.Mui-focused": { color: sectionLabelSx.color } }}>
                      Where are you in your AI journey?
                    </FormLabel>
                    <RadioGroup value={field.state.value} onChange={(_, value) => field.handleChange(value)} sx={{ gap: 0.75 }}>
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
            </form.Field>

            <form.Field name="brings">
              {(field) => {
                const errorMessage = fieldErrorMessage(field);
                return (
                  <FormControl error={!!errorMessage} component="fieldset" sx={{ width: "100%" }}>
                    <FormLabel component="legend" sx={{ ...sectionLabelSx, mb: 1, "&.Mui-focused": { color: sectionLabelSx.color } }}>
                      What brings you to Arthur today?
                    </FormLabel>
                    <RadioGroup value={field.state.value} onChange={(_, value) => field.handleChange(value)} sx={{ gap: 0.75 }}>
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
            </form.Field>

            <form.Subscribe selector={(s) => s.values.brings === "other"}>
              {(show) =>
                show ? (
                  <form.Field name="bringsOther">
                    {(field) => (
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

            <form.Field name="competitors">
              {(field) => {
                const value = field.state.value;
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

            <form.Subscribe selector={(s) => s.values.competitors.includes("other")}>
              {(show) =>
                show ? (
                  <form.Field name="competitorOther">
                    {(field) => (
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

            <form.Field name="attribution">
              {(field) => {
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
                          <Chip
                            key={opt.id}
                            label={opt.label}
                            clickable
                            onClick={() => field.handleChange(opt.id)}
                            variant="outlined"
                            sx={chipSx(on)}
                          />
                        );
                      })}
                    </Stack>
                    {errorMessage && <FormHelperText sx={{ mx: 0, mt: 0.75, fontSize: 12, fontWeight: 500 }}>{errorMessage}</FormHelperText>}
                  </FormControl>
                );
              }}
            </form.Field>

            <Button
              type="submit"
              variant="contained"
              color="primary"
              size="large"
              disableElevation
              endIcon={<ArrowForwardIcon sx={{ fontSize: 16 }} />}
              fullWidth
              sx={{ textTransform: "none", fontSize: 15, fontWeight: 600, borderRadius: "8px", mt: 0.5 }}
            >
              Start the demo
            </Button>

            <Stack direction="row" alignItems="center" spacing={1} sx={{ mt: 0.25 }}>
              <BoltIcon sx={{ fontSize: 14, color: "secondary.main" }} />
              <Typography sx={{ fontSize: 12, color: "text.secondary" }}>Your demo task is yours alone. The API key is scoped to it.</Typography>
            </Stack>
          </Paper>
        </Box>
      </Box>
    </Box>
  );
};
