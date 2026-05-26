import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import EmailIcon from "@mui/icons-material/Email";
import PersonIcon from "@mui/icons-material/Person";
import { Box, Button, FormLabel, Stack, TextField, Typography } from "@mui/material";

import { fieldErrorMessage, labelSx, textFieldSx } from "../../styles";
import { withForm } from "../hooks/form";
import { STEP_HEADINGS } from "../options";
import { identitySchema, wizardFormOpts } from "../schema";

export const TryItOutFormWizardIdentityStep = withForm({
  ...wizardFormOpts,
  props: {
    onBack: () => {},
    onAdvance: () => {},
    onInvalid: () => {},
  },
  render: function Render({ form, onBack, onAdvance, onInvalid }) {
    const heading = STEP_HEADINGS[0];

    return (
      <form.FormGroup name="identity" validators={{ onDynamic: identitySchema }} onGroupSubmit={onAdvance} onGroupSubmitInvalid={onInvalid}>
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

              <Stack direction="row" spacing={1.5}>
                <form.AppField name="identity.firstName">
                  {(field) => (
                    <Stack spacing={0.75} sx={{ flex: 1 }}>
                      <FormLabel htmlFor="eow-firstname" sx={labelSx}>
                        First name
                      </FormLabel>
                      <TextField
                        id="eow-firstname"
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
                </form.AppField>
                <form.AppField name="identity.lastName">
                  {(field) => (
                    <Stack spacing={0.75} sx={{ flex: 1 }}>
                      <FormLabel htmlFor="eow-lastname" sx={labelSx}>
                        Last name
                      </FormLabel>
                      <TextField
                        id="eow-lastname"
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
                </form.AppField>
              </Stack>

              <form.AppField name="identity.email">
                {(field) => (
                  <Stack spacing={0.75}>
                    <FormLabel htmlFor="eow-email" sx={labelSx}>
                      Work email
                    </FormLabel>
                    <TextField
                      id="eow-email"
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
              </form.AppField>

              <Stack direction="row" spacing={1.5}>
                <form.AppField name="identity.jobTitle">
                  {(field) => (
                    <Stack spacing={0.75} sx={{ flex: 1 }}>
                      <FormLabel htmlFor="eow-jobtitle" sx={labelSx}>
                        Job title
                      </FormLabel>
                      <TextField
                        id="eow-jobtitle"
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
                </form.AppField>
                <form.AppField name="identity.company">
                  {(field) => (
                    <Stack spacing={0.75} sx={{ flex: 1 }}>
                      <FormLabel htmlFor="eow-company" sx={labelSx}>
                        Company
                      </FormLabel>
                      <TextField
                        id="eow-company"
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
                </form.AppField>
              </Stack>

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
                  disableElevation
                  endIcon={<ArrowForwardIcon sx={{ fontSize: 16 }} />}
                  sx={{ textTransform: "none", fontSize: 14, fontWeight: 600, borderRadius: "8px", px: 2.5 }}
                >
                  Continue
                </Button>
              </Stack>
            </Stack>
          </Box>
        )}
      </form.FormGroup>
    );
  },
});
