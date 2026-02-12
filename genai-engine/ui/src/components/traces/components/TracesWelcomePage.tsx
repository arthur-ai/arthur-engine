import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import ArticleOutlinedIcon from "@mui/icons-material/ArticleOutlined";
import BoltIcon from "@mui/icons-material/Bolt";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import KeyIcon from "@mui/icons-material/Key";
import RocketLaunchIcon from "@mui/icons-material/RocketLaunch";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import { Box, Button, Link, Paper, Stack, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import React from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useShallow } from "zustand/react/shallow";

import { useWelcomeStore } from "../stores/welcome.store";

import { useTask } from "@/hooks/useTask";
import { EVENT_NAMES, track } from "@/services/amplitude";

export const TracesWelcomePage: React.FC = () => {
  const { task } = useTask();
  const navigate = useNavigate();
  const { id: taskId } = useParams<{ id: string }>();
  const { enqueueSnackbar } = useSnackbar();

  const welcomeStore = useWelcomeStore(taskId || "");
  const stepStatus = welcomeStore(
    useShallow((state) => ({
      apiKeyClicked: state.apiKeyClicked,
      taskIdCopied: state.taskIdCopied,
    }))
  );

  const handleApiKeyClick = () => {
    welcomeStore.getState().setApiKeyClicked(true);
    track(EVENT_NAMES.ONBOARDING_API_KEY_CLICKED, {
      task_id: task?.id ?? taskId ?? "",
      source: "traces_welcome",
    });
    navigate(`/tasks/${taskId}/api-keys`);
  };

  const handleCopyTaskId = async () => {
    if (task?.id) {
      try {
        await navigator.clipboard.writeText(task.id);
        welcomeStore.getState().setTaskIdCopied(true);
        enqueueSnackbar("Task ID copied to clipboard", { variant: "success" });
        track(EVENT_NAMES.ONBOARDING_TASK_ID_COPIED, {
          task_id: task.id,
          source: "traces_welcome",
        });
      } catch (_err) {
        enqueueSnackbar("Failed to copy Task ID", { variant: "error" });
      }
    }
  };

  const handleSkip = () => {
    welcomeStore.getState().setDismissed(true);
    track(EVENT_NAMES.ONBOARDING_SKIP_SETUP_CLICKED, {
      task_id: task?.id ?? taskId ?? "",
      source: "traces_welcome",
    });
  };

  return (
    <Box
      sx={{
        width: "100%",
        display: "flex",
        justifyContent: "center",
        alignItems: "flex-start",
        py: 2,
      }}
    >
      <Paper
        elevation={0}
        sx={{
          width: "100%",
          maxWidth: 750,
          borderRadius: 3,
          p: { xs: 2.5, sm: 3, md: 3.5 },
          backgroundColor: "background.paper",
          boxShadow: (theme) => (theme.palette.mode === "dark" ? "0 4px 24px rgba(0, 0, 0, 0.3)" : "0 4px 24px rgba(0, 0, 0, 0.06)"),
          border: "1px solid",
          borderColor: "divider",
        }}
      >
        <Box
          sx={{
            width: "100%",
            mx: "auto",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          {/* Header Section */}
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              width: "100%",
              mb: 1,
            }}
          >
            {/* Rocket Icon */}
            <Box
              sx={{
                width: 42,
                height: 42,
                borderRadius: "50%",
                background: (theme) =>
                  theme.palette.mode === "dark"
                    ? "linear-gradient(135deg, #1A237E 0%, #283593 100%)"
                    : "linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                mb: 0.75,
                boxShadow: (theme) => (theme.palette.mode === "dark" ? "0 4px 12px rgba(33, 150, 243, 0.3)" : "0 4px 12px rgba(33, 150, 243, 0.2)"),
                transition: "transform 0.3s ease-in-out",
                "&:hover": {
                  transform: "scale(1.05)",
                },
              }}
            >
              <RocketLaunchIcon sx={{ fontSize: 24, color: "primary.main" }} />
            </Box>

            {/* Title */}
            <Typography
              variant="h4"
              component="h1"
              sx={{
                fontWeight: 700,
                mb: 0.375,
                fontSize: { xs: "1.25rem", sm: "1.375rem", md: "1.5rem" },
                textAlign: "center",
                color: "text.primary",
                letterSpacing: "-0.02em",
              }}
            >
              Ready to start monitoring
            </Typography>

            {/* Subtitle */}
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{
                mb: 0,
                fontWeight: 400,
                textAlign: "center",
                maxWidth: 480,
                fontSize: { xs: "0.75rem", sm: "0.8125rem" },
                lineHeight: 1.25,
              }}
            >
              Connect your AI agent to Arthur and start capturing traces
            </Typography>
          </Box>

          {/* Quick Start Guide Section */}
          <Box sx={{ width: "100%", maxWidth: 750 }}>
            <Typography
              variant="h6"
              sx={{
                fontWeight: 600,
                mb: 1,
                fontSize: { xs: "0.9375rem", sm: "1rem" },
                color: "text.primary",
              }}
            >
              Quick Start Guide
            </Typography>

            {/* Steps Container */}
            <Stack spacing={0.625} sx={{ width: "100%", mb: 1 }}>
              {/* Step 1: Install the Arthur Engine - Completed */}
              <Paper
                elevation={0}
                sx={{
                  p: { xs: 1, sm: 1.25 },
                  border: "2px solid",
                  borderColor: "success.main",
                  backgroundColor: (theme) => (theme.palette.mode === "dark" ? "rgba(46, 125, 50, 0.08)" : "#F1F8F4"),
                  borderRadius: 2,
                  transition: "all 0.3s ease-in-out",
                  "&:hover": {
                    boxShadow: "0 6px 16px rgba(46, 125, 50, 0.2)",
                    transform: "translateY(-1px)",
                  },
                }}
              >
                <Stack direction="row" spacing={1} alignItems="flex-start">
                  <Box
                    sx={{
                      width: 28,
                      height: 28,
                      borderRadius: "50%",
                      backgroundColor: "success.main",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      boxShadow: "0 2px 8px rgba(46, 125, 50, 0.3)",
                    }}
                  >
                    <CheckCircleIcon sx={{ color: "white", fontSize: 18 }} />
                  </Box>
                  <Box sx={{ flex: 1 }}>
                    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>
                        Install the Arthur Engine
                      </Typography>
                      <Box
                        sx={{
                          px: 0.875,
                          py: 0.25,
                          borderRadius: 1,
                          backgroundColor: "success.main",
                          color: "white",
                          display: "flex",
                          alignItems: "center",
                        }}
                      >
                        <Typography variant="caption" sx={{ fontWeight: 700, fontSize: "0.5625rem", lineHeight: 1 }}>
                          Completed
                        </Typography>
                      </Box>
                    </Stack>
                    <Typography variant="body2" color="text.secondary" sx={{ fontSize: "0.6875rem" }}>
                      Successfully connected to the engine
                    </Typography>
                  </Box>
                </Stack>
              </Paper>

              {/* Step 2: Configure API Keys */}
              <Paper
                elevation={0}
                sx={{
                  p: { xs: 1, sm: 1.25 },
                  border: "2px solid",
                  borderColor: stepStatus.apiKeyClicked ? "success.main" : "divider",
                  backgroundColor: (theme) =>
                    stepStatus.apiKeyClicked
                      ? theme.palette.mode === "dark"
                        ? "rgba(46, 125, 50, 0.08)"
                        : "#F1F8F4"
                      : theme.palette.background.paper,
                  borderRadius: 2,
                  transition: "all 0.3s ease-in-out",
                  cursor: stepStatus.apiKeyClicked ? "default" : "pointer",
                  "&:hover": {
                    boxShadow: stepStatus.apiKeyClicked ? "0 6px 16px rgba(46, 125, 50, 0.2)" : "0 6px 16px rgba(33, 150, 243, 0.15)",
                    borderColor: stepStatus.apiKeyClicked ? "success.main" : "primary.main",
                    transform: "translateY(-1px)",
                  },
                }}
                onClick={!stepStatus.apiKeyClicked ? handleApiKeyClick : undefined}
              >
                <Stack direction="row" spacing={1} alignItems="flex-start">
                  <Box
                    sx={{
                      width: 28,
                      height: 28,
                      borderRadius: "50%",
                      backgroundColor: stepStatus.apiKeyClicked ? "success.main" : "primary.main",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      boxShadow: stepStatus.apiKeyClicked ? "0 2px 8px rgba(46, 125, 50, 0.25)" : "0 2px 8px rgba(33, 150, 243, 0.25)",
                    }}
                  >
                    {stepStatus.apiKeyClicked ? (
                      <CheckCircleIcon sx={{ color: "white", fontSize: 18 }} />
                    ) : (
                      <KeyIcon sx={{ color: "white", fontSize: 14 }} />
                    )}
                  </Box>
                  <Box sx={{ flex: 1 }}>
                    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>
                        Configure your API Keys
                      </Typography>
                      {!stepStatus.apiKeyClicked ? (
                        <Box
                          sx={{
                            px: 0.875,
                            py: 0.25,
                            borderRadius: 1,
                            backgroundColor: (theme) => (theme.palette.mode === "dark" ? "grey.800" : "#F5F5F5"),
                            color: "text.primary",
                            display: "flex",
                            alignItems: "center",
                          }}
                        >
                          <Typography variant="caption" sx={{ fontWeight: 700, fontSize: "0.5625rem", lineHeight: 1 }}>
                            Step 2
                          </Typography>
                        </Box>
                      ) : (
                        <Box
                          sx={{
                            px: 0.875,
                            py: 0.25,
                            borderRadius: 1,
                            backgroundColor: "success.main",
                            color: "white",
                            display: "flex",
                            alignItems: "center",
                          }}
                        >
                          <Typography variant="caption" sx={{ fontWeight: 700, fontSize: "0.5625rem", lineHeight: 1 }}>
                            Completed
                          </Typography>
                        </Box>
                      )}
                    </Stack>
                    <Link
                      component="button"
                      variant="body2"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleApiKeyClick();
                      }}
                      sx={{
                        textDecoration: "none",
                        color: "primary.main",
                        fontWeight: 500,
                        fontSize: "0.6875rem",
                        "&:hover": {
                          textDecoration: "underline",
                        },
                      }}
                    >
                      Click here to find your API keys.
                    </Link>
                  </Box>
                </Stack>
              </Paper>

              {/* Step 3: Copy Task ID */}
              <Paper
                elevation={0}
                sx={{
                  p: { xs: 1, sm: 1.25 },
                  border: "2px solid",
                  borderColor: stepStatus.taskIdCopied ? "success.main" : "divider",
                  backgroundColor: (theme) =>
                    stepStatus.taskIdCopied
                      ? theme.palette.mode === "dark"
                        ? "rgba(46, 125, 50, 0.08)"
                        : "#F1F8F4"
                      : theme.palette.background.paper,
                  borderRadius: 2,
                  transition: "all 0.3s ease-in-out",
                  "&:hover": {
                    boxShadow: stepStatus.taskIdCopied ? "0 6px 16px rgba(46, 125, 50, 0.2)" : "0 6px 16px rgba(156, 39, 176, 0.15)",
                    transform: "translateY(-1px)",
                  },
                }}
              >
                <Stack direction="row" spacing={1} alignItems="flex-start">
                  <Box
                    sx={{
                      width: 28,
                      height: 28,
                      borderRadius: "50%",
                      backgroundColor: stepStatus.taskIdCopied ? "success.main" : "#9C27B0",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      boxShadow: stepStatus.taskIdCopied ? "0 2px 8px rgba(46, 125, 50, 0.25)" : "0 2px 8px rgba(156, 39, 176, 0.25)",
                    }}
                  >
                    {stepStatus.taskIdCopied ? (
                      <CheckCircleIcon sx={{ color: "white", fontSize: 18 }} />
                    ) : (
                      <BoltIcon sx={{ color: "white", fontSize: 14 }} />
                    )}
                  </Box>
                  <Box sx={{ flex: 1 }}>
                    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>
                        Copy your Task ID
                      </Typography>
                      {!stepStatus.taskIdCopied ? (
                        <Box
                          sx={{
                            px: 0.875,
                            py: 0.25,
                            borderRadius: 1,
                            backgroundColor: (theme) => (theme.palette.mode === "dark" ? "grey.800" : "#F5F5F5"),
                            color: "text.primary",
                            display: "flex",
                            alignItems: "center",
                          }}
                        >
                          <Typography variant="caption" sx={{ fontWeight: 700, fontSize: "0.5625rem", lineHeight: 1 }}>
                            Step 3
                          </Typography>
                        </Box>
                      ) : (
                        <Box
                          sx={{
                            px: 0.875,
                            py: 0.25,
                            borderRadius: 1,
                            backgroundColor: "success.main",
                            color: "white",
                            display: "flex",
                            alignItems: "center",
                          }}
                        >
                          <Typography variant="caption" sx={{ fontWeight: 700, fontSize: "0.5625rem", lineHeight: 1 }}>
                            Completed
                          </Typography>
                        </Box>
                      )}
                    </Stack>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5, fontSize: "0.6875rem", lineHeight: 1.25 }}>
                      You can pass the task ID as a resource attribute{" "}
                      <Box
                        component="code"
                        sx={{
                          px: 0.3,
                          py: 0.05,
                          backgroundColor: (theme) => (theme.palette.mode === "dark" ? "grey.700" : "grey.200"),
                          borderRadius: 0.5,
                          fontFamily: "monospace",
                          fontSize: "0.625rem",
                        }}
                      >
                        arthur.task
                      </Box>{" "}
                      when instrumenting your app.
                    </Typography>
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 0.4,
                        p: 0.75,
                        backgroundColor: (theme) => (theme.palette.mode === "dark" ? "grey.800" : "#F5F5F5"),
                        border: "1px solid",
                        borderColor: "divider",
                        borderRadius: 1,
                        transition: "all 0.2s ease-in-out",
                        "&:hover": {
                          backgroundColor: (theme) => (theme.palette.mode === "dark" ? "grey.700" : "#EEEEEE"),
                          borderColor: "primary.light",
                        },
                      }}
                    >
                      <Typography
                        variant="body2"
                        sx={{
                          flex: 1,
                          fontFamily: "monospace",
                          fontSize: "0.625rem",
                          wordBreak: "break-all",
                          color: "text.primary",
                          fontWeight: 500,
                        }}
                      >
                        {task?.id || taskId || "Loading..."}
                      </Typography>
                      <Button
                        size="small"
                        onClick={handleCopyTaskId}
                        startIcon={<ContentCopyIcon sx={{ fontSize: 12 }} />}
                        sx={{
                          flexShrink: 0,
                          textTransform: "none",
                          fontWeight: 600,
                          minWidth: 55,
                          fontSize: "0.5625rem",
                          py: 0.375,
                        }}
                        variant={stepStatus.taskIdCopied ? "outlined" : "contained"}
                        color={stepStatus.taskIdCopied ? "success" : "primary"}
                      >
                        {stepStatus.taskIdCopied ? "Copied" : "Copy"}
                      </Button>
                    </Box>
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 0.375, display: "block", fontSize: "0.5625rem" }}>
                      Need help?{" "}
                      <Link href="https://docs.arthur.ai/" target="_blank" rel="noopener noreferrer" sx={{ fontWeight: 500, color: "primary.main" }}>
                        See other options here
                      </Link>
                    </Typography>
                  </Box>
                </Stack>
              </Paper>

              {/* Step 4: Start Tracing */}
              <Paper
                elevation={0}
                sx={{
                  p: { xs: 1, sm: 1.25 },
                  border: "2px solid",
                  borderColor: stepStatus.taskIdCopied ? "success.main" : "divider",
                  backgroundColor: (theme) =>
                    stepStatus.taskIdCopied
                      ? theme.palette.mode === "dark"
                        ? "rgba(46, 125, 50, 0.08)"
                        : "#F1F8F4"
                      : theme.palette.background.paper,
                  borderRadius: 2,
                  transition: "all 0.3s ease-in-out",
                  "&:hover": {
                    boxShadow: stepStatus.taskIdCopied ? "0 6px 16px rgba(46, 125, 50, 0.2)" : "0 6px 16px rgba(255, 152, 0, 0.15)",
                    transform: "translateY(-1px)",
                  },
                }}
              >
                <Stack direction="row" spacing={1} alignItems="flex-start">
                  <Box
                    sx={{
                      width: 28,
                      height: 28,
                      borderRadius: "50%",
                      backgroundColor: stepStatus.taskIdCopied ? "success.main" : "#FF9800",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      boxShadow: stepStatus.taskIdCopied ? "0 2px 8px rgba(46, 125, 50, 0.25)" : "0 2px 8px rgba(255, 152, 0, 0.25)",
                    }}
                  >
                    {stepStatus.taskIdCopied ? (
                      <CheckCircleIcon sx={{ color: "white", fontSize: 18 }} />
                    ) : (
                      <ShowChartIcon sx={{ color: "white", fontSize: 14 }} />
                    )}
                  </Box>
                  <Box sx={{ flex: 1 }}>
                    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>
                        Start tracing
                      </Typography>
                      {!stepStatus.taskIdCopied ? (
                        <Box
                          sx={{
                            px: 0.875,
                            py: 0.25,
                            borderRadius: 1,
                            backgroundColor: (theme) => (theme.palette.mode === "dark" ? "grey.800" : "#F5F5F5"),
                            color: "text.primary",
                            display: "flex",
                            alignItems: "center",
                          }}
                        >
                          <Typography variant="caption" sx={{ fontWeight: 700, fontSize: "0.5625rem", lineHeight: 1 }}>
                            Step 4
                          </Typography>
                        </Box>
                      ) : (
                        <Box
                          sx={{
                            px: 0.875,
                            py: 0.25,
                            borderRadius: 1,
                            backgroundColor: "success.main",
                            color: "white",
                            display: "flex",
                            alignItems: "center",
                          }}
                        >
                          <Typography variant="caption" sx={{ fontWeight: 700, fontSize: "0.5625rem", lineHeight: 1 }}>
                            Completed
                          </Typography>
                        </Box>
                      )}
                    </Stack>
                    <Typography variant="body2" color="text.secondary" sx={{ fontSize: "0.6875rem", lineHeight: 1.25 }}>
                      Once you've configured these steps, your agent calls will automatically start to capture traces here.
                    </Typography>
                  </Box>
                </Stack>
              </Paper>
            </Stack>
          </Box>

          {/* View Traces Button */}
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              mt: 1.5,
              mb: 1,
              gap: 1,
            }}
          >
            <Button
              variant="contained"
              size="medium"
              startIcon={<ArrowForwardIcon sx={{ fontSize: 16 }} />}
              sx={{
                px: 3,
                py: 0.75,
                textTransform: "none",
                fontSize: "0.875rem",
                fontWeight: 600,
                borderRadius: 1.5,
                boxShadow: "0 2px 8px rgba(33, 150, 243, 0.25)",
                transition: "all 0.2s ease-in-out",
                "&:hover": {
                  boxShadow: "0 4px 12px rgba(33, 150, 243, 0.35)",
                  transform: "translateY(-1px)",
                },
                "&.Mui-disabled": {
                  backgroundColor: "action.disabledBackground",
                  color: "action.disabled",
                },
              }}
              disabled={!stepStatus.taskIdCopied}
              onClick={() => {
                welcomeStore.getState().setDismissed(true);
                track(EVENT_NAMES.ONBOARDING_VIEW_TRACES_CLICKED, {
                  task_id: task?.id ?? taskId ?? "",
                  source: "traces_welcome",
                });
              }}
            >
              View Traces
            </Button>
            <Link
              component="button"
              variant="body2"
              onClick={handleSkip}
              sx={{
                color: "text.secondary",
                fontSize: "0.75rem",
                textDecoration: "none",
                "&:hover": {
                  textDecoration: "underline",
                  color: "text.primary",
                },
              }}
            >
              Skip setup
            </Link>
          </Box>

          {/* Footer Links */}
          <Stack direction="row" spacing={0.75} alignItems="center" justifyContent="center" sx={{ mt: 0.75, mb: 0.75 }}>
            <Link
              href="https://docs.arthur.ai/"
              target="_blank"
              rel="noopener noreferrer"
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                textDecoration: "none",
                color: "text.secondary",
                transition: "all 0.2s ease-in-out",
                "&:hover": {
                  color: "primary.main",
                },
              }}
            >
              <ArticleOutlinedIcon sx={{ fontSize: 16 }} />
              <Typography variant="body2" sx={{ fontWeight: 500, fontSize: "0.875rem" }}>
                Platform Documentation
              </Typography>
            </Link>
            <Typography variant="body2" sx={{ color: "text.secondary", fontSize: "0.875rem", mx: 0.5 }}>
              •
            </Typography>
            <Link
              href="mailto:support@arthur.ai"
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                textDecoration: "none",
                color: "text.secondary",
                transition: "all 0.2s ease-in-out",
                "&:hover": {
                  color: "primary.main",
                },
              }}
            >
              <HelpOutlineIcon sx={{ fontSize: 16 }} />
              <Typography variant="body2" sx={{ fontWeight: 500, fontSize: "0.875rem" }}>
                Support & Help
              </Typography>
            </Link>
          </Stack>
        </Box>
      </Paper>
    </Box>
  );
};
