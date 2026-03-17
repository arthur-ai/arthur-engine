import ArrowBackOutlined from "@mui/icons-material/ArrowBackOutlined";
import { Box, Button } from "@mui/material";
import React from "react";
import { useNavigate } from "react-router-dom";

import { ArthurLogo } from "../common/ArthurLogo";

import { SettingsMenuButton } from "@/components/settings/SettingsMenuButton";

interface SettingsPageProps {
  children: React.ReactNode;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ children }) => {
  const navigate = useNavigate();

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <Box component="header" sx={{ bgcolor: "background.paper", boxShadow: 1 }}>
        <Box sx={{ maxWidth: "80rem", mx: "auto", px: { xs: 2, sm: 3, lg: 4 } }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", py: 1.5 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, cursor: "pointer" }}>
              <ArthurLogo className="h-20 -ml-5 text-black dark:text-white" onClick={() => navigate("/")} />
            </Box>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
              <SettingsMenuButton />
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
