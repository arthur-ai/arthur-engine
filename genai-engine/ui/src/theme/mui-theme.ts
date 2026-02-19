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
  components: {
    MuiTableContainer: {
      styleOverrides: {
        root: {
          backgroundColor: "#ffffff",
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          backgroundColor: "#f1f5f9",
        },
        stickyHeader: {
          backgroundColor: "#f1f5f9",
        },
      },
    },
  },
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
  components: {
    MuiTableContainer: {
      styleOverrides: {
        root: {
          backgroundColor: "#111827",
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          backgroundColor: "#1e293b",
        },
        stickyHeader: {
          backgroundColor: "#1e293b",
        },
      },
    },
  },
});
