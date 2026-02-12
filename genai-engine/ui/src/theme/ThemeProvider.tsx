import CssBaseline from "@mui/material/CssBaseline";
import { ThemeProvider as MuiThemeProvider } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useEffect, useMemo } from "react";

import { darkTheme, lightTheme } from "./mui-theme";

import { useThemeStore } from "@/stores/theme.store";

export function AppThemeProvider({ children }: { children: React.ReactNode }) {
  const mode = useThemeStore((s) => s.mode);
  const prefersDark = useMediaQuery("(prefers-color-scheme: dark)");

  const resolvedDark = mode === "dark" || (mode === "system" && prefersDark);

  useEffect(() => {
    const root = document.documentElement;
    if (resolvedDark) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [resolvedDark]);

  const muiTheme = useMemo(() => (resolvedDark ? darkTheme : lightTheme), [resolvedDark]);

  return (
    <MuiThemeProvider theme={muiTheme}>
      <CssBaseline />
      {children}
    </MuiThemeProvider>
  );
}
