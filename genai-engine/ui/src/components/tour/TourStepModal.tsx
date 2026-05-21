import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Typography,
} from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import LoopIcon from "@mui/icons-material/Loop";
import TrackChangesIcon from "@mui/icons-material/TrackChanges";

import { useAdvanceTourStep } from "@/components/tour/hooks/useAdvanceTourStep";
import { useCurrentTourStep } from "@/components/tour/hooks/useCurrentTourStep";
import { useTourStore } from "@/stores/tour.store";

export function TourStepModal() {
  const currentStep = useCurrentTourStep();
  const { advance } = useAdvanceTourStep();
  const guidanceVisible = useTourStore((state) => state.guidanceVisible);
  const minimizeGuidance = useTourStore((state) => state.actions.minimizeGuidance);

  if (!currentStep || currentStep.type !== "modal" || !guidanceVisible) {
    return null;
  }

  const isIntroStep = currentStep.id === "intro-adlc";

  return (
    <Dialog open maxWidth="sm" fullWidth onClose={minimizeGuidance}>
      <DialogTitle>{currentStep.title}</DialogTitle>
      <DialogContent>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
          {currentStep.description}
        </Typography>

        {isIntroStep && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 1,
                py: 2,
                px: 2,
                borderRadius: 2,
                bgcolor: "action.hover",
              }}
            >
              <LoopIcon color="primary" />
              <Typography variant="subtitle2" color="text.primary">
                ADLC flywheel: Observe → Evaluate → Improve → Deploy
              </Typography>
            </Box>

            <List dense disablePadding>
              <ListItem disableGutters>
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <TrackChangesIcon fontSize="small" color="primary" />
                </ListItemIcon>
                <ListItemText
                  primary="Why Arthur advocates for this"
                  secondary="Continuous measurement closes the loop between production behavior and agent quality—so improvements are evidence-based, not guesswork."
                />
              </ListItem>
              <ListItem disableGutters>
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <CheckCircleOutlineIcon fontSize="small" color="primary" />
                </ListItemIcon>
                <ListItemText
                  primary="What you'll get from this walkthrough"
                  secondary="You'll interact with a demo agent, send a test message, and set up evaluators so you can measure readability and response quality."
                />
              </ListItem>
            </List>
          </Box>
        )}

        {currentStep.content && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {currentStep.content}
          </Typography>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button variant="contained" onClick={advance}>
          Continue
        </Button>
      </DialogActions>
    </Dialog>
  );
}
