import { DEFAULT_TOUR_LAYERS } from "@arthur/shared-components/tour";
import { createTheme, type Theme } from "@mui/material/styles";

/**
 * Dropdown popups — Autocomplete's `Popper` and Select's `Menu` — default to
 * `theme.zIndex.modal` (1300). During the guided "Create Experiment" tour step
 * the task tour paints a backdrop (spotlight, 1399) and a click-blocker (1401)
 * above this dialog, so a default dropdown opens *underneath* the tour overlay:
 * the backdrop clips it and the blocker swallows its clicks (UP-4482).
 *
 * Sit one tier above every tour layer so dropdowns stay visible and clickable
 * during the tour — and behave exactly as before when no tour is running, since
 * a dropdown above a 1300 dialog is already the expected stacking order.
 */
export const EXPERIMENT_DROPDOWN_Z_INDEX = Math.max(...Object.values(DEFAULT_TOUR_LAYERS)) + 1;

/**
 * Returns a theme derived from `parent` that lifts every dropdown popup inside
 * the Create Experiment modal above the tour overlay. Applied via a scoped
 * `ThemeProvider` so the override only touches this modal's subtree — the
 * portaled popups still read it through React context.
 */
export function createExperimentDropdownTheme(parent: Theme): Theme {
  return createTheme(parent, {
    components: {
      MuiAutocomplete: {
        defaultProps: { slotProps: { popper: { sx: { zIndex: EXPERIMENT_DROPDOWN_Z_INDEX } } } },
      },
      // MUI Select renders its menu as a Popover; lifting the Popover covers it.
      MuiPopover: {
        defaultProps: { sx: { zIndex: EXPERIMENT_DROPDOWN_Z_INDEX } },
      },
    },
  });
}
