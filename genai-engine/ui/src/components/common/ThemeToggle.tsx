import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import LaptopOutlinedIcon from "@mui/icons-material/LaptopOutlined";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";

import { useThemeStore, type ThemeMode } from "@/stores/theme.store";

const modeLabels: Record<ThemeMode, string> = {
  system: "System",
  light: "Light",
  dark: "Dark",
};

export function ThemeToggle() {
  const mode = useThemeStore((s) => s.mode);
  const setMode = useThemeStore((s) => s.setMode);

  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: "block" }}>
        Preferences ({modeLabels[mode]})
      </Typography>
      <ToggleButtonGroup
        value={mode}
        exclusive
        onChange={(_e, value) => {
          if (value !== null) setMode(value as ThemeMode);
        }}
        size="small"
        aria-label="Theme mode"
      >
        <ToggleButton value="system" aria-label="System theme">
          <LaptopOutlinedIcon fontSize="small" />
        </ToggleButton>
        <ToggleButton value="light" aria-label="Light theme">
          <LightModeOutlinedIcon fontSize="small" />
        </ToggleButton>
        <ToggleButton value="dark" aria-label="Dark theme">
          <DarkModeOutlinedIcon fontSize="small" />
        </ToggleButton>
      </ToggleButtonGroup>
    </Box>
  );
}
