import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import EmailIcon from "@mui/icons-material/Email";
import PersonIcon from "@mui/icons-material/Person";
import { Box, Button, FormLabel, Stack, TextField, Typography } from "@mui/material";

import { fieldErrorMessage, labelSx, textFieldSx } from "../../styles";
import { STEP_HEADINGS } from "../options";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyApi = any;

export interface IdentityStepProps {
  form: AnyApi;
  group: AnyApi;
  onBack: () => void;
}

export const TryItOutFormWizardIdentityStep: React.FC<IdentityStepProps> = ({ form, group, onBack }) => {
  const heading = STEP_HEADINGS[0];

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

        <Stack direction="row" spacing={1.5}>
          <form.Field name="identity.firstName">
            {(field: AnyApi) => (
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
          </form.Field>
          <form.Field name="identity.lastName">
            {(field: AnyApi) => (
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
          </form.Field>
        </Stack>

        <form.Field name="identity.email">
          {(field: AnyApi) => (
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
        </form.Field>

        <Stack direction="row" spacing={1.5}>
          <form.Field name="identity.jobTitle">
            {(field: AnyApi) => (
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
          </form.Field>
          <form.Field name="identity.company">
            {(field: AnyApi) => (
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
          </form.Field>
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
  );
};
