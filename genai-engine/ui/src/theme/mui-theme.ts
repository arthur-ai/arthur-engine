import { createTheme } from "@mui/material/styles";

const commonTypography = {
  fontFamily: '"Geist", sans-serif',
};

export const lightTheme = createTheme({
  palette: {
    mode: "light",
    background: {
      default: "#f9fafb",
      paper: "#ffffff",
    },
  },
  typography: commonTypography,
});

export const darkTheme = createTheme({
  palette: {
    mode: "dark",
    background: {
      default: "#0a0a0a",
      paper: "#111827", // matches Tailwind gray-900
    },
  },
  typography: commonTypography,
});
