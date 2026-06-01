import { createTheme } from "@mui/material/styles";
import { describe, expect, it } from "vitest";

import { createExperimentDropdownTheme, EXPERIMENT_DROPDOWN_Z_INDEX } from "./tourDropdownTheme";

import { DEFAULT_TOUR_LAYERS } from "@/features/tour";

describe("createExperimentDropdownTheme", () => {
  it("floats dropdowns above every task tour overlay layer", () => {
    const highestTourLayer = Math.max(...Object.values(DEFAULT_TOUR_LAYERS));
    expect(EXPERIMENT_DROPDOWN_Z_INDEX).toBeGreaterThan(highestTourLayer);
    // The interaction blocker is the layer that would otherwise swallow clicks.
    expect(EXPERIMENT_DROPDOWN_Z_INDEX).toBeGreaterThan(DEFAULT_TOUR_LAYERS.blocker);
  });

  it("raises Autocomplete poppers and Select menus to the elevated z-index", () => {
    const theme = createExperimentDropdownTheme(createTheme());

    const autocompletePopperSx = theme.components?.MuiAutocomplete?.defaultProps?.slotProps?.popper as { sx?: { zIndex?: number } } | undefined;
    expect(autocompletePopperSx?.sx?.zIndex).toBe(EXPERIMENT_DROPDOWN_Z_INDEX);

    const popoverSx = theme.components?.MuiPopover?.defaultProps?.sx as { zIndex?: number } | undefined;
    expect(popoverSx?.zIndex).toBe(EXPERIMENT_DROPDOWN_Z_INDEX);
  });

  it("preserves the parent theme so unrelated tokens are untouched", () => {
    const parent = createTheme({ palette: { primary: { main: "#123456" } } });
    const theme = createExperimentDropdownTheme(parent);
    expect(theme.palette.primary.main).toBe("#123456");
  });
});
