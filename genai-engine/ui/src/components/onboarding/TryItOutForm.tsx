import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import BoltIcon from "@mui/icons-material/Bolt";
import CheckIcon from "@mui/icons-material/Check";
import EmailIcon from "@mui/icons-material/Email";
import PersonIcon from "@mui/icons-material/Person";
import { Box, Button, Paper, Stack, TextField, Typography } from "@mui/material";
import { useForm, type AnyFieldApi } from "@tanstack/react-form";
import { z } from "zod";

import { EngineTopNav } from "./EngineTopNav";
import { ATTRIBUTION_OPTIONS, BRINGS_OPTIONS, COMPETITOR_OPTIONS, MATURITY_OPTIONS } from "./onboardingOptions";

const BRAND_PURPLE = "#7C3AED";
const BLUE_400 = "#3B82F6";
const BLUE_500 = "#2563EB";
const BLUE_600 = "#1D4ED8";
const BLUE_50 = "#EFF6FF";
const RED_600 = "#DC2626";

const onboardingSchema = z
  .object({
    firstName: z.string().trim().min(1, { error: "Required" }),
    lastName: z.string().trim().min(1, { error: "Required" }),
    email: z.string().regex(/.+@.+\..+/, { error: "Enter a valid work email" }),
    jobTitle: z.string().trim().min(1, { error: "Required" }),
    company: z.string().trim().min(1, { error: "Required" }),
    building: z.string().trim().min(1, { error: "Tell us a bit" }),
    maturity: z.string().min(1, { error: "Pick one" }),
    brings: z.string().min(1, { error: "Pick one" }),
    bringsOther: z.string(),
    competitors: z.array(z.string()).min(1, { error: "Pick at least one" }),
    competitorOther: z.string(),
    attribution: z.string().min(1, { error: "Pick one" }),
  })
  .superRefine((data, ctx) => {
    if (data.brings === "other" && !data.bringsOther.trim()) {
      ctx.addIssue({
        code: "custom",
        path: ["bringsOther"],
        message: "Please specify",
      });
    }
    if (data.competitors.includes("other") && !data.competitorOther.trim()) {
      ctx.addIssue({
        code: "custom",
        path: ["competitorOther"],
        message: "Please specify",
      });
    }
  });

export type TryItOutSubmission = z.infer<typeof onboardingSchema>;

interface TryItOutFormProps {
  onBack: () => void;
  onSubmit: (data: TryItOutSubmission) => void;
}

const labelSx = {
  fontSize: 13,
  fontWeight: 500,
  color: "text.primary",
};

const inputFieldSx = {
  "& .MuiOutlinedInput-root": {
    borderRadius: "8px",
    backgroundColor: "background.paper",
    fontSize: 14,
    "& fieldset": { borderColor: "grey.300" },
    "&:hover fieldset": { borderColor: "grey.400" },
    "&.Mui-focused fieldset": {
      borderColor: BLUE_400,
      boxShadow: "0 0 0 3px rgba(59,130,246,0.12)",
    },
  },
  "& .MuiOutlinedInput-input": {
    py: "10px",
  },
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
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        backgroundColor: "grey.50",
      }}
    >
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

          <Typography
            component="h1"
            sx={{
              fontSize: 22,
              fontWeight: 700,
              color: "text.primary",
              letterSpacing: "-0.01em",
              lineHeight: 1.25,
              mb: 1,
            }}
          >
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
              borderColor: "grey.200",
              borderRadius: "12px",
              p: 3.5,
              mt: 1,
              display: "flex",
              flexDirection: "column",
              gap: 2.25,
            }}
          >
            {/* Name row */}
            <Stack direction="row" spacing={1.5}>
              <form.Field name="firstName">
                {(field) => (
                  <Stack spacing={0.75} sx={{ flex: 1 }}>
                    <Typography component="label" htmlFor="eo-firstname" sx={labelSx}>
                      First name
                    </Typography>
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
                          startAdornment: <PersonIcon sx={{ fontSize: 16, color: "grey.400", mr: 1 }} />,
                        },
                      }}
                      sx={inputFieldSx}
                    />
                  </Stack>
                )}
              </form.Field>
              <form.Field name="lastName">
                {(field) => (
                  <Stack spacing={0.75} sx={{ flex: 1 }}>
                    <Typography component="label" htmlFor="eo-lastname" sx={labelSx}>
                      Last name
                    </Typography>
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
                      sx={inputFieldSx}
                    />
                  </Stack>
                )}
              </form.Field>
            </Stack>

            {/* Email */}
            <form.Field name="email">
              {(field) => (
                <Stack spacing={0.75}>
                  <Typography component="label" htmlFor="eo-email" sx={labelSx}>
                    Work email
                  </Typography>
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
                        startAdornment: <EmailIcon sx={{ fontSize: 16, color: "grey.400", mr: 1 }} />,
                      },
                    }}
                    sx={inputFieldSx}
                  />
                </Stack>
              )}
            </form.Field>

            {/* Title / Company */}
            <Stack direction="row" spacing={1.5}>
              <form.Field name="jobTitle">
                {(field) => (
                  <Stack spacing={0.75} sx={{ flex: 1 }}>
                    <Typography component="label" htmlFor="eo-jobtitle" sx={labelSx}>
                      Job title
                    </Typography>
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
                      sx={inputFieldSx}
                    />
                  </Stack>
                )}
              </form.Field>
              <form.Field name="company">
                {(field) => (
                  <Stack spacing={0.75} sx={{ flex: 1 }}>
                    <Typography component="label" htmlFor="eo-company" sx={labelSx}>
                      Company
                    </Typography>
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
                      sx={inputFieldSx}
                    />
                  </Stack>
                )}
              </form.Field>
            </Stack>

            {/* What are you building */}
            <form.Field name="building">
              {(field) => (
                <Stack spacing={0.75}>
                  <Typography component="label" htmlFor="eo-building" sx={labelSx}>
                    What are you building?
                  </Typography>
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
                    sx={inputFieldSx}
                  />
                </Stack>
              )}
            </form.Field>

            {/* Maturity */}
            <form.Field name="maturity">
              {(field) => (
                <Stack spacing={1}>
                  <Typography sx={{ fontSize: 13, fontWeight: 600, color: "text.primary" }}>Where are you in your AI journey?</Typography>
                  <Stack spacing={0.75}>
                    {MATURITY_OPTIONS.map((opt) => {
                      const selected = field.state.value === opt.id;
                      return (
                        <Box
                          key={opt.id}
                          component="button"
                          type="button"
                          onClick={() => field.handleChange(opt.id)}
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 1.25,
                            px: 1.5,
                            py: 1.25,
                            backgroundColor: selected ? BLUE_50 : "background.paper",
                            border: "1px solid",
                            borderColor: selected ? BLUE_400 : "grey.200",
                            borderRadius: "8px",
                            fontFamily: "inherit",
                            fontSize: 13,
                            color: "text.primary",
                            cursor: "pointer",
                            textAlign: "left",
                            transition: "border-color 0.12s, background 0.12s",
                            "&:hover": selected ? {} : { borderColor: "grey.300", backgroundColor: "grey.50" },
                          }}
                        >
                          <Box
                            sx={{
                              width: 10,
                              height: 10,
                              borderRadius: "999px",
                              backgroundColor: opt.dot,
                              flexShrink: 0,
                              boxShadow: opt.dot === "#D1D5DB" ? "inset 0 0 0 1px #9CA3AF" : "none",
                            }}
                          />
                          <Box sx={{ flex: 1 }}>{opt.label}</Box>
                          {selected && <CheckIcon sx={{ fontSize: 14, color: BLUE_600 }} />}
                        </Box>
                      );
                    })}
                  </Stack>
                  {fieldErrorMessage(field) && (
                    <Typography sx={{ fontSize: 12, color: RED_600, fontWeight: 500 }}>{fieldErrorMessage(field)}</Typography>
                  )}
                </Stack>
              )}
            </form.Field>

            {/* Brings */}
            <form.Field name="brings">
              {(field) => (
                <Stack spacing={1}>
                  <Typography sx={{ fontSize: 13, fontWeight: 600, color: "text.primary" }}>What brings you to Arthur today?</Typography>
                  <Stack spacing={0.75}>
                    {BRINGS_OPTIONS.map((opt) => {
                      const selected = field.state.value === opt.id;
                      return (
                        <Box
                          key={opt.id}
                          component="button"
                          type="button"
                          onClick={() => field.handleChange(opt.id)}
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 1.25,
                            px: 1.5,
                            py: 1.25,
                            backgroundColor: selected ? BLUE_50 : "background.paper",
                            border: "1px solid",
                            borderColor: selected ? BLUE_400 : "grey.200",
                            borderRadius: "8px",
                            fontFamily: "inherit",
                            fontSize: 13,
                            color: "text.primary",
                            cursor: "pointer",
                            textAlign: "left",
                            transition: "border-color 0.12s, background 0.12s",
                            "&:hover": selected ? {} : { borderColor: "grey.300", backgroundColor: "grey.50" },
                          }}
                        >
                          <Box
                            sx={{
                              width: 16,
                              height: 16,
                              borderRadius: "999px",
                              border: "1.5px solid",
                              borderColor: selected ? BLUE_500 : "grey.300",
                              flexShrink: 0,
                              display: "grid",
                              placeItems: "center",
                              backgroundColor: "background.paper",
                            }}
                          >
                            {selected && (
                              <Box
                                sx={{
                                  width: 8,
                                  height: 8,
                                  borderRadius: "999px",
                                  backgroundColor: BLUE_500,
                                }}
                              />
                            )}
                          </Box>
                          <Box sx={{ flex: 1 }}>{opt.label}</Box>
                        </Box>
                      );
                    })}
                  </Stack>
                  {fieldErrorMessage(field) && (
                    <Typography sx={{ fontSize: 12, color: RED_600, fontWeight: 500 }}>{fieldErrorMessage(field)}</Typography>
                  )}
                </Stack>
              )}
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
                        sx={{ ...inputFieldSx, mt: -1 }}
                      />
                    )}
                  </form.Field>
                ) : null
              }
            </form.Subscribe>

            {/* Competitors */}
            <form.Field name="competitors">
              {(field) => {
                const value = field.state.value;
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
                  <Stack spacing={1}>
                    <Stack direction="row" alignItems="baseline" spacing={1}>
                      <Typography sx={{ fontSize: 13, fontWeight: 600, color: "text.primary" }}>Have you used any of these tools before?</Typography>
                      <Typography sx={{ fontSize: 11, fontWeight: 400, color: "text.secondary" }}>Select all that apply</Typography>
                    </Stack>
                    <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1 }}>
                      {COMPETITOR_OPTIONS.map((opt) => {
                        const on = value.includes(opt.id);
                        return (
                          <Box
                            key={opt.id}
                            component="button"
                            type="button"
                            onClick={() => toggle(opt.id)}
                            sx={{
                              display: "inline-flex",
                              alignItems: "center",
                              justifyContent: "center",
                              px: 1.75,
                              py: 0.875,
                              backgroundColor: on ? BLUE_50 : "background.paper",
                              border: "1px solid",
                              borderColor: on ? BLUE_500 : "grey.300",
                              borderRadius: "999px",
                              fontFamily: "inherit",
                              fontSize: 13,
                              fontWeight: 500,
                              color: on ? BLUE_600 : "text.primary",
                              cursor: "pointer",
                              whiteSpace: "nowrap",
                              transition: "border-color 0.12s, background 0.12s, color 0.12s",
                              "&:hover": on ? {} : { borderColor: "grey.400", backgroundColor: "grey.50" },
                            }}
                          >
                            {opt.label}
                          </Box>
                        );
                      })}
                    </Stack>
                    {fieldErrorMessage(field) && (
                      <Typography sx={{ fontSize: 12, color: RED_600, fontWeight: 500 }}>{fieldErrorMessage(field)}</Typography>
                    )}
                  </Stack>
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
                        sx={{ ...inputFieldSx, mt: -1 }}
                      />
                    )}
                  </form.Field>
                ) : null
              }
            </form.Subscribe>

            {/* Attribution */}
            <form.Field name="attribution">
              {(field) => (
                <Stack spacing={1}>
                  <Typography sx={{ fontSize: 13, fontWeight: 600, color: "text.primary" }}>How did you hear about Arthur?</Typography>
                  <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1 }}>
                    {ATTRIBUTION_OPTIONS.map((opt) => {
                      const on = field.state.value === opt.id;
                      return (
                        <Box
                          key={opt.id}
                          component="button"
                          type="button"
                          onClick={() => field.handleChange(opt.id)}
                          sx={{
                            display: "inline-flex",
                            alignItems: "center",
                            justifyContent: "center",
                            px: 1.75,
                            py: 0.875,
                            backgroundColor: on ? BLUE_50 : "background.paper",
                            border: "1px solid",
                            borderColor: on ? BLUE_500 : "grey.300",
                            borderRadius: "999px",
                            fontFamily: "inherit",
                            fontSize: 13,
                            fontWeight: 500,
                            color: on ? BLUE_600 : "text.primary",
                            cursor: "pointer",
                            whiteSpace: "nowrap",
                            transition: "border-color 0.12s, background 0.12s, color 0.12s",
                            "&:hover": on ? {} : { borderColor: "grey.400", backgroundColor: "grey.50" },
                          }}
                        >
                          {opt.label}
                        </Box>
                      );
                    })}
                  </Stack>
                  {fieldErrorMessage(field) && (
                    <Typography sx={{ fontSize: 12, color: RED_600, fontWeight: 500 }}>{fieldErrorMessage(field)}</Typography>
                  )}
                </Stack>
              )}
            </form.Field>

            {/* Submit */}
            <Button
              type="submit"
              variant="contained"
              disableElevation
              endIcon={<ArrowForwardIcon sx={{ fontSize: 16 }} />}
              fullWidth
              sx={{
                backgroundColor: BLUE_500,
                color: "common.white",
                textTransform: "none",
                fontSize: 15,
                fontWeight: 600,
                borderRadius: "8px",
                py: 1.5,
                mt: 0.5,
                "&:hover": { backgroundColor: BLUE_600 },
              }}
            >
              Start the demo
            </Button>

            <Stack direction="row" alignItems="center" spacing={1} sx={{ mt: 0.25 }}>
              <BoltIcon sx={{ fontSize: 14, color: BRAND_PURPLE }} />
              <Typography sx={{ fontSize: 12, color: "text.secondary" }}>Your demo task is yours alone. The API key is scoped to it.</Typography>
            </Stack>
          </Paper>
        </Box>
      </Box>
    </Box>
  );
};
