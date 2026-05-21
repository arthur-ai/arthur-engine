import { Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle } from "@mui/material";

import type { SectionConfig, TourActions } from "../core/types";

export interface DefaultIntroDialogProps {
  open: boolean;
  section: SectionConfig;
  actions: TourActions;
}

/**
 * Default introduction modal shown before the first step of a section that
 * declares `introduction`. Primary action acknowledges the intro and starts the
 * section's first step; secondary action skips the whole section (only shown
 * when the section is skipable).
 */
export function DefaultIntroDialog({ open, section, actions }: DefaultIntroDialogProps) {
  const intro = section.introduction;
  if (!intro) return null;

  const skipable = section.skipable !== false;
  const primaryLabel = intro.primaryActionLabel ?? "Continue";
  const secondaryLabel = intro.secondaryActionLabel ?? "Skip section";

  return (
    <Dialog
      open={open}
      onClose={skipable ? () => actions.skipSection() : undefined}
      maxWidth="sm"
      fullWidth
      aria-labelledby="tour-intro-dialog-title"
    >
      <DialogTitle id="tour-intro-dialog-title">{intro.title}</DialogTitle>
      {intro.description ? (
        <DialogContent>
          <DialogContentText component="div">{intro.description}</DialogContentText>
        </DialogContent>
      ) : null}
      <DialogActions sx={{ px: 3, pb: 2 }}>
        {skipable ? (
          <Button onClick={() => actions.skipSection()} variant="text" color="inherit">
            {secondaryLabel}
          </Button>
        ) : null}
        <Button onClick={() => actions.acknowledgeIntroduction()} variant="contained" color="primary">
          {primaryLabel}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
