import AppsOutlined from "@mui/icons-material/AppsOutlined";
import ArrowBackOutlined from "@mui/icons-material/ArrowBackOutlined";
import KeyOutlined from "@mui/icons-material/KeyOutlined";
import LogoutOutlined from "@mui/icons-material/LogoutOutlined";
import SettingsIcon from "@mui/icons-material/Settings";
import { Box, Button, IconButton } from "@mui/material";
import React, { useEffect, useState } from "react";
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
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (isMenuOpen) {
        const target = event.target as Element;
        if (!target.closest(".relative")) {
          setIsMenuOpen(false);
        }
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isMenuOpen]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <header className="bg-white dark:bg-gray-900 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-3">
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <ArthurLogo className="h-20 -ml-5 text-black dark:text-white" onClick={() => navigate("/")} style={{ cursor: "pointer" }} />
            </Box>
            <div className="flex items-center space-x-4">
              <div className="relative">
                <IconButton
                  aria-label="settings"
                  onClick={() => setIsMenuOpen((prev) => !prev)}
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
                {isMenuOpen && (
                  <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-md shadow-lg py-2 z-50 border border-gray-200 dark:border-gray-700">
                    <div>
                      <Button
                        variant="text"
                        fullWidth
                        startIcon={<AppsOutlined />}
                        onClick={() => {
                          setIsMenuOpen(false);
                          navigate("/settings/model-providers");
                        }}
                        sx={{ color: "text.primary", justifyContent: "flex-start", textTransform: "none" }}
                      >
                        Model Providers
                      </Button>
                      <Button
                        variant="text"
                        fullWidth
                        startIcon={<KeyOutlined />}
                        onClick={() => {
                          setIsMenuOpen(false);
                          navigate("/settings/api-keys");
                        }}
                        sx={{ color: "text.primary", justifyContent: "flex-start", textTransform: "none" }}
                      >
                        API Keys
                      </Button>
                    </div>
                    <div className="border-t border-gray-200 dark:border-gray-700 mt-1 pt-1 px-4 py-2">
                      <ThemeToggle />
                    </div>
                    <div className="border-t border-gray-200 dark:border-gray-700 mt-1 pt-1">
                      <Button
                        variant="text"
                        fullWidth
                        startIcon={<LogoutOutlined />}
                        onClick={logout}
                        sx={{ color: "text.primary", justifyContent: "flex-start", textTransform: "none" }}
                      >
                        Logout
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-3 sm:px-6 lg:px-8">
        <div className="px-4 py-3 sm:px-0">
          <Button startIcon={<ArrowBackOutlined />} onClick={() => navigate("/")} sx={{ mb: 2, color: "text.secondary", textTransform: "none" }}>
            Back to All Tasks
          </Button>
          {children}
        </div>
      </main>
    </div>
  );
};
