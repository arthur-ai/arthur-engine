import AppsOutlined from "@mui/icons-material/AppsOutlined";
import KeyOutlined from "@mui/icons-material/KeyOutlined";
import LogoutOutlined from "@mui/icons-material/LogoutOutlined";
import SettingsIcon from "@mui/icons-material/Settings";
import SettingsApplicationsOutlined from "@mui/icons-material/SettingsApplicationsOutlined";
import { Box, Divider, IconButton, ListItemIcon, ListItemText, Menu, MenuItem } from "@mui/material";
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ThemeToggle } from "../common/ThemeToggle";

import { UserSettingsModal } from "@/components/UserSettingsModal";
import { useAuth } from "@/contexts/AuthContext";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";

export const SettingsMenuButton: React.FC = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { timezone, use24Hour, setTimezone, setUse24Hour } = useDisplaySettings();
  const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null);
  const [userSettingsModalOpen, setUserSettingsModalOpen] = useState(false);

  const isMenuOpen = Boolean(menuAnchorEl);

  const handleMenuClose = () => {
    setMenuAnchorEl(null);
  };

  const handleLogout = () => {
    logout();
  };

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
          <ListItemText>User settings</ListItemText>
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
        <MenuItem
          onClick={() => {
            handleMenuClose();
            navigate("/settings/application-config");
          }}
        >
          <ListItemIcon>
            <SettingsApplicationsOutlined />
          </ListItemIcon>
          <ListItemText>Application config</ListItemText>
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
        initialSettings={{ timezone, use24Hour }}
        onSave={(settings) => {
          if (settings.timezone !== undefined) setTimezone(settings.timezone);
          if (settings.use24Hour !== undefined) setUse24Hour(settings.use24Hour);
          setUserSettingsModalOpen(false);
        }}
      />
    </>
  );
};
