import AppsOutlined from "@mui/icons-material/AppsOutlined";
import ArrowBackOutlined from "@mui/icons-material/ArrowBackOutlined";
import KeyOutlined from "@mui/icons-material/KeyOutlined";
import LogoutOutlined from "@mui/icons-material/LogoutOutlined";
import SettingsIcon from "@mui/icons-material/Settings";
import SettingsApplicationsOutlined from "@mui/icons-material/SettingsApplicationsOutlined";
import { Box, Button, Divider, IconButton, ListItemIcon, ListItemText, Menu, MenuItem } from "@mui/material";
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ArthurLogo } from "../common/ArthurLogo";
import { ThemeToggle } from "../common/ThemeToggle";

import { useAuth } from "@/contexts/AuthContext";

interface SettingsPageProps {
  children: React.ReactNode;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ children }) => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null);
  const isMenuOpen = Boolean(menuAnchorEl);

  const handleMenuClose = () => {
    setMenuAnchorEl(null);
  };

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <Box component="header" sx={{ bgcolor: "background.paper", boxShadow: 1 }}>
        <Box sx={{ maxWidth: "80rem", mx: "auto", px: { xs: 2, sm: 3, lg: 4 } }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", py: 1.5 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, cursor: "pointer" }}>
              <ArthurLogo className="h-20 -ml-5 text-black dark:text-white" onClick={() => navigate("/")} />
            </Box>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
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
                <MenuItem onClick={logout}>
                  <ListItemIcon>
                    <LogoutOutlined />
                  </ListItemIcon>
                  <ListItemText>Logout</ListItemText>
                </MenuItem>
              </Menu>
            </Box>
          </Box>
        </Box>
      </Box>

      <Box component="main" sx={{ maxWidth: "80rem", mx: "auto", py: 1.5, px: { xs: 2, sm: 3, lg: 4 } }}>
        <Box sx={{ px: { xs: 2, sm: 0 }, py: 1.5 }}>
          <Button startIcon={<ArrowBackOutlined />} onClick={() => navigate("/")} sx={{ mb: 2, color: "text.secondary", textTransform: "none" }}>
            Back to All Tasks
          </Button>
          {children}
        </Box>
      </Box>
    </Box>
  );
};
