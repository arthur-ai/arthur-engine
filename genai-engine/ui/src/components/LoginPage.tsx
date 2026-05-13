import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import VpnKeyOutlinedIcon from "@mui/icons-material/VpnKeyOutlined";
import { Alert, Box, Button, CircularProgress, InputAdornment, Stack, TextField, Typography } from "@mui/material";
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { EngineTopNav } from "./onboarding/engine-top-nav";

import { useAuth } from "@/contexts/AuthContext";
import { useDemoMode } from "@/contexts/EngineConfigContext";

export const LoginPage: React.FC = () => {
  const [token, setToken] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login, error, isAuthenticated } = useAuth();
  const { demoMode } = useDemoMode();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token.trim()) return;

    setIsSubmitting(true);
    try {
      const success = await login(token.trim());
      if (!success) {
        console.error("Login failed");
      }
    } catch (err) {
      console.error("Login error:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        backgroundColor: "background.default",
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
        <Box sx={{ width: "100%", maxWidth: 420, textAlign: "center" }}>
          <Box
            sx={{
              width: 56,
              height: 56,
              borderRadius: "999px",
              backgroundColor: "background.paper",
              border: "1px solid",
              borderColor: "divider",
              display: "grid",
              placeItems: "center",
              mx: "auto",
              mb: 2.5,
              color: "text.secondary",
            }}
          >
            <VpnKeyOutlinedIcon sx={{ fontSize: 28 }} />
          </Box>

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
            Sign in with an API token
          </Typography>

          <Typography
            sx={{
              fontSize: 14,
              color: "text.secondary",
              lineHeight: 1.55,
              mb: 3,
            }}
          >
            Authenticate to your Arthur workspace using your existing API token.
          </Typography>

          <Box
            component="form"
            onSubmit={handleSubmit}
            sx={{
              backgroundColor: "background.paper",
              border: "1px solid",
              borderColor: "divider",
              borderRadius: "12px",
              p: 3.5,
              textAlign: "left",
              display: "flex",
              flexDirection: "column",
              gap: 2,
            }}
          >
            <TextField
              id="token"
              name="token"
              type="password"
              autoComplete="current-password"
              fullWidth
              variant="outlined"
              size="small"
              placeholder="Enter your API token"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              disabled={isSubmitting}
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <VpnKeyOutlinedIcon sx={{ fontSize: 16, color: "text.disabled" }} />
                    </InputAdornment>
                  ),
                  sx: { fontSize: 14, borderRadius: "8px", backgroundColor: "background.paper" },
                },
              }}
            />

            {error && (
              <Alert severity="error" icon={<ErrorOutlineIcon fontSize="small" />} sx={{ alignItems: "flex-start", fontSize: 13 }}>
                <Typography component="div" sx={{ fontSize: 13, fontWeight: 600 }}>
                  Authentication error
                </Typography>
                <Typography component="div" sx={{ fontSize: 13, mt: 0.25 }}>
                  {error}
                </Typography>
              </Alert>
            )}

            <Button
              type="submit"
              variant="contained"
              color="primary"
              size="large"
              disableElevation
              disabled={isSubmitting || !token.trim()}
              sx={{ textTransform: "none", fontSize: 15, fontWeight: 600, borderRadius: "8px", py: 1.25 }}
            >
              {isSubmitting ? (
                <Stack direction="row" alignItems="center" spacing={1}>
                  <CircularProgress size={16} thickness={5} sx={{ color: "inherit" }} />
                  <Typography component="span" sx={{ fontSize: 15, fontWeight: 600, color: "inherit" }}>
                    Signing in…
                  </Typography>
                </Stack>
              ) : (
                "Sign in"
              )}
            </Button>

            <Typography
              component="div"
              sx={{
                textAlign: "center",
                fontSize: 12,
                color: "text.disabled",
                mt: 0.5,
              }}
            >
              Don&apos;t have a token? Contact your administrator to get access.
            </Typography>
          </Box>

          {demoMode && (
            <Box sx={{ mt: 2.5 }}>
              <Button
                variant="text"
                color="inherit"
                size="small"
                startIcon={<ArrowBackIcon sx={{ fontSize: 14 }} />}
                onClick={() => navigate("/welcome")}
                sx={{
                  textTransform: "none",
                  fontSize: 13,
                  fontWeight: 500,
                  color: "text.secondary",
                  "&:hover": { color: "text.primary", backgroundColor: "transparent" },
                }}
              >
                Back to start
              </Button>
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );
};
