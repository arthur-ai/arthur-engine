import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import EmailIcon from "@mui/icons-material/Email";
import PersonIcon from "@mui/icons-material/Person";
import { Box, Button, FormLabel, Stack, TextField, Typography } from "@mui/material";

import { fieldErrorMessage, labelSx, textFieldSx } from "../../styles";
import { STEP_HEADINGS } from "../options";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyGroup = any;

export interface IdentityStepProps {
  group: AnyGroup;
  onBack: () => void;
}

export const TryItOutFormWizardIdentityStep: React.FC<IdentityStepProps> = ({ group, onBack }) => {
  const heading = STEP_HEADINGS[0];

  return (
    <Stack spacing={2.25}>
      <Box>
        <Typography component="h2" sx={{ fontSize: 18, fontWeight: 700, color: "text.primary", lineHeight: 1.3, mb: 0.5 }}>
          {heading.title}
        </Typography>
        <Typography sx={{ fontSize: 13, color: "text.secondary", lineHeight: 1.5 }}>{heading.subtitle}</Typography>
      </Box>

      <Stack direction="row" spacing={1.5}>
        <group.Field name="firstName">
          {(field: AnyGroup) => (
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
        </group.Field>
        <group.Field name="lastName">
          {(field: AnyGroup) => (
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
        </group.Field>
      </Stack>

      <group.Field name="email">
        {(field: AnyGroup) => (
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
      </group.Field>

      <Stack direction="row" spacing={1.5}>
        <group.Field name="jobTitle">
          {(field: AnyGroup) => (
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
        </group.Field>
        <group.Field name="company">
          {(field: AnyGroup) => (
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
        </group.Field>
      </Stack>

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
