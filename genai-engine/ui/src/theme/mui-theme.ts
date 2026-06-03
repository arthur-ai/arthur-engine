import { createTheme } from "@mui/material/styles";

/**
 * Layout tokens for the onboarding tour's docked side panel ({@link
 * import('../features/task-tour/components/TourSidePanel').TourSidePanel}).
 * Centralized here so the collapsed-rail and expanded-content widths live
 * with the rest of the design system rather than as loose component constants.
 */
declare module "@mui/material/styles" {
  interface Theme {
    tour: { railWidth: number; contentWidth: number };
  }
  interface ThemeOptions {
    tour?: { railWidth: number; contentWidth: number };
  }
}

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
    tour: { railWidth: 44, contentWidth: 312 },
    components: {
      // Overlays escape document flow (portaled to body / position:fixed) and
      // anchor to the viewport, so they ignore the in-flow `TourSidePanel` that
      // shrinks the content area from the right. `--app-inset-right` carries the
      // panel's current width (0px whenever it is absent — see TourSidePanel),
      // and these overrides subtract it so centered dialogs and right-anchored
      // drawers stay within the usable content region rather than under the
      // panel. Inert outside the tour, where the variable is 0.
      MuiDialog: {
        styleOverrides: {
          // The container flex-centers the paper; trimming its right padding
          // re-centers within the reduced region without touching the backdrop.
          container: {
            paddingRight: "var(--app-inset-right, 0px)",
            boxSizing: "border-box",
          },
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paperAnchorRight: {
            // Anchor to the content edge (panel's left) instead of the window edge…
            right: "var(--app-inset-right, 0px)",
            // …and cap the width so a drawer sized as a viewport percentage
            // (e.g. width: "80%"/"90%") resolves against the content region
            // rather than the full window and overflows under the panel.
            // Capping below 100% leaves a left gutter of exposed backdrop —
            // clicking it is a primary way to close the drawer, so it must never
            // be fully covered. Defaults to `none` (TRULY inert off-tour, so a
            // drawer's own maxWidth — e.g. the 95% PromptVersionDrawer — is
            // untouched); TourSidePanel sets the 90%-content calc only while the
            // panel reserves space.
            maxWidth: "var(--app-drawer-max-width, none)",
          },
        },
      },
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
