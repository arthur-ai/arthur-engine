import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Link from "@mui/material/Link";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import { Link as RouterLink } from "react-router-dom";

import type { ContinuousEvalResponse } from "@/lib/api-client/api-client";

interface TransformImpactedCEsDialogProps {
  open: boolean;
  onClose: () => void;
  impactedCEs: ContinuousEvalResponse[];
  transformName: string;
}

const TransformImpactedCEsDialog = ({ open, onClose, impactedCEs, transformName }: TransformImpactedCEsDialogProps) => {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          Continuous Evals May Need Review
        </Typography>
      </DialogTitle>
      <DialogContent>
        <Alert severity="info" sx={{ mb: 2 }}>
          <strong>{transformName}</strong> was updated. The following Continuous Evals use this transform and may need to be reviewed.
        </Alert>
        <List disablePadding>
          {impactedCEs.map((ce) => (
            <ListItem
              key={ce.id}
              sx={{
                border: 1,
                borderColor: "divider",
                borderRadius: 1,
                mb: 1,
                "&:last-child": { mb: 0 },
              }}
              secondaryAction={
                <Link component={RouterLink} to={`/tasks/${ce.task_id}/continuous-evals/${ce.id}`} underline="hover">
                  <Button size="small" variant="text" endIcon={<OpenInNewIcon sx={{ fontSize: 16 }} />}>
                    Review
                  </Button>
                </Link>
              }
            >
              <ListItemText
                primary={
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Typography variant="body1" sx={{ fontWeight: 500 }}>
                      {ce.name}
                    </Typography>
                  </Box>
                }
              />
            </ListItem>
          ))}
        </List>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} variant="contained">
          Dismiss
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TransformImpactedCEsDialog;
