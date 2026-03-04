import { createTheme } from "@mui/material/styles";

const commonTypography = {
  fontFamily: '"Geist", sans-serif',
};

const createAppTheme = (mode: "light" | "dark") =>
  createTheme({
    palette: {
      mode,
      background: mode === "light" ? { default: "#f9fafb", paper: "#ffffff" } : { default: "#0a0a0a", paper: "#111827" },
    },
    typography: commonTypography,
    components: {
      MuiTableContainer: {
        styleOverrides: {
          root: ({ theme }) => ({
            backgroundColor: theme.palette.background.paper,
          }),
        },
      },
      MuiTableCell: {
        styleOverrides: {
          head: ({ theme }) => ({
            backgroundColor: theme.palette.mode === "light" ? theme.palette.grey[100] : theme.palette.grey[900],
          }),
          stickyHeader: ({ theme }) => ({
            backgroundColor: theme.palette.mode === "light" ? theme.palette.grey[100] : theme.palette.grey[900],
          }),
        },
      },
    },
  });

export const lightTheme = createAppTheme("light");
export const darkTheme = createAppTheme("dark");
