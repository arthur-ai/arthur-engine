import AppsOutlined from "@mui/icons-material/AppsOutlined";
import KeyOutlined from "@mui/icons-material/KeyOutlined";
import LogoutOutlined from "@mui/icons-material/LogoutOutlined";
import SettingsIcon from "@mui/icons-material/Settings";
import { Box, Divider, IconButton, ListItemIcon, ListItemText, Menu, MenuItem } from "@mui/material";
import { useSnackbar } from "notistack";
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ThemeToggle } from "../common/ThemeToggle";

import { UserSettingsModal } from "@/components/UserSettingsModal";
import { useAuth } from "@/contexts/AuthContext";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useApi } from "@/hooks/useApi";
import { useApplicationConfiguration } from "@/hooks/useApplicationConfiguration";
import { useAvailableModels, useModelProviders } from "@/hooks/useModelProviders";
import type { ModelProvider } from "@/lib/api-client/api-client";

export const SettingsMenuButton: React.FC = () => {
  const navigate = useNavigate();
  const api = useApi();
  const { logout } = useAuth();
  const { timezone, use24Hour, setTimezone, setUse24Hour, serverChatbotEnabled, enableChatbot, setEnableChatbot } = useDisplaySettings();
  const { providers: enabledProviders } = useModelProviders();
  const { availableModels: availableModelsMap } = useAvailableModels(enabledProviders);
  const { data: appConfig, isLoading: isLoadingAppConfig, error: appConfigError, updateConfiguration } = useApplicationConfiguration();
  const { enqueueSnackbar } = useSnackbar();
  const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null);
  const [userSettingsModalOpen, setUserSettingsModalOpen] = useState(false);
  const [chatbotModelProvider, setChatbotModelProvider] = useState<ModelProvider | "">("");
  const [chatbotModelName, setChatbotModelName] = useState("");
  const [blacklistEndpoints, setBlacklistEndpoints] = useState<string[]>([]);
  const [availableEndpoints, setAvailableEndpoints] = useState<string[]>([]);
  const [isSavingSettings, setIsSavingSettings] = useState(false);

  const isMenuOpen = Boolean(menuAnchorEl);

  const handleMenuClose = () => {
    setMenuAnchorEl(null);
  };

  const handleLogout = () => {
    logout();
  };

  useEffect(() => {
    if (api && userSettingsModalOpen) {
      api.api
        .getChatbotConfigApiV1ChatbotConfigGet()
        .then((res) => {
          setChatbotModelProvider(res.data.model_provider);
          setChatbotModelName(res.data.model_name);
          setBlacklistEndpoints(res.data.blacklist_endpoints ?? []);
          setAvailableEndpoints(res.data.available_endpoints ?? []);
        })
        .catch(() => {
          // Chatbot config not available (e.g. feature disabled)
        });
    }
  }, [api, userSettingsModalOpen]);

  return (
    <>
      <IconButton
        aria-label="settings"
        onClick={(e) => setMenuAnchorEl(e.currentTarget)}
        sx={{
          bgcolor: "background.paper",
          border: 1,
          borderColor: "divider",
          borderRadius: "4px",
          padding: "8px",
          width: "40px",
          height: "40px",
        }}
      >
        <SettingsIcon />
      </IconButton>
      <Menu
        anchorEl={menuAnchorEl}
        open={isMenuOpen}
        onClose={handleMenuClose}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
      >
        <MenuItem
          onClick={() => {
            handleMenuClose();
            setUserSettingsModalOpen(true);
          }}
        >
          <ListItemIcon>
            <SettingsIcon />
          </ListItemIcon>
          <ListItemText>Settings</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={() => {
            handleMenuClose();
            navigate("/settings/model-providers");
          }}
        >
          <ListItemIcon>
            <AppsOutlined />
          </ListItemIcon>
          <ListItemText>Model Providers</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={() => {
            handleMenuClose();
            navigate("/settings/api-keys");
          }}
        >
          <ListItemIcon>
            <KeyOutlined />
          </ListItemIcon>
          <ListItemText>API Keys</ListItemText>
        </MenuItem>
        <Divider />
        <Box sx={{ px: 2, py: 1 }}>
          <ThemeToggle />
        </Box>
        <Divider />
        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <LogoutOutlined />
          </ListItemIcon>
          <ListItemText>Logout</ListItemText>
        </MenuItem>
      </Menu>
      <UserSettingsModal
        open={userSettingsModalOpen}
        onClose={() => setUserSettingsModalOpen(false)}
        initialSettings={{
          timezone,
          use24Hour,
          enableChatbot,
          chatbotModelProvider,
          chatbotModelName,
          blacklistEndpoints,
        }}
        chatbotEnabled={serverChatbotEnabled}
        enabledProviders={enabledProviders}
        availableModelsMap={availableModelsMap}
        availableEndpoints={availableEndpoints}
        traceRetentionEnabled={!appConfigError && !!appConfig}
        initialTraceRetentionDays={appConfig?.trace_retention_days}
        isLoadingTraceRetention={isLoadingAppConfig}
        isSaving={isSavingSettings}
        onSave={async (settings) => {
          if (settings.timezone !== undefined) setTimezone(settings.timezone);
          if (settings.use24Hour !== undefined) setUse24Hour(settings.use24Hour);
          if (settings.enableChatbot !== undefined) setEnableChatbot(settings.enableChatbot);

          setIsSavingSettings(true);
          try {
            const providerChanged = settings.chatbotModelProvider && settings.chatbotModelProvider !== chatbotModelProvider;
            const modelChanged = settings.chatbotModelName && settings.chatbotModelName !== chatbotModelName;
            const blacklistChanged = JSON.stringify(settings.blacklistEndpoints ?? []) !== JSON.stringify(blacklistEndpoints);

            if (api && (providerChanged || modelChanged || blacklistChanged)) {
              const prevProvider = chatbotModelProvider;
              const prevModel = chatbotModelName;
              const prevBlacklist = blacklistEndpoints;
              if (settings.chatbotModelProvider) setChatbotModelProvider(settings.chatbotModelProvider as ModelProvider);
              if (settings.chatbotModelName) setChatbotModelName(settings.chatbotModelName);
              if (settings.blacklistEndpoints) setBlacklistEndpoints(settings.blacklistEndpoints);
              try {
                await api.api.updateChatbotConfigApiV1ChatbotConfigPut({
                  model_provider: (settings.chatbotModelProvider || chatbotModelProvider) as ModelProvider,
                  model_name: settings.chatbotModelName || chatbotModelName,
                  blacklist_endpoints: settings.blacklistEndpoints,
                });
              } catch (err) {
                console.error("Failed to update chatbot config:", err);
                setChatbotModelProvider(prevProvider);
                setChatbotModelName(prevModel);
                setBlacklistEndpoints(prevBlacklist);
              }
            }

            if (settings.traceRetentionDays !== undefined && settings.traceRetentionDays !== appConfig?.trace_retention_days) {
              try {
                await updateConfiguration({ trace_retention_days: settings.traceRetentionDays });
                enqueueSnackbar("Application configuration updated", { variant: "success" });
              } catch (err) {
                const message = err instanceof Error ? err.message : "Failed to update configuration";
                enqueueSnackbar(message, { variant: "error" });
              }
            }
          } finally {
            setIsSavingSettings(false);
          }

          setUserSettingsModalOpen(false);
        }}
      />
    </>
  );
};
