import BalanceOutlinedIcon from "@mui/icons-material/BalanceOutlined";
import PrecisionManufacturingOutlinedIcon from "@mui/icons-material/PrecisionManufacturingOutlined";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Typography from "@mui/material/Typography";

type EvalKind = "llm" | "ml";

interface CreateEvalTypeModalProps {
  open: boolean;
  onClose: () => void;
  onSelectType: (type: EvalKind) => void;
}

const TYPE_OPTIONS: { kind: EvalKind; label: string; description: string; Icon: React.ElementType }[] = [
  {
    kind: "llm",
    label: "LLM Evaluator",
    description: "Use a language model as a judge. Write custom instructions to evaluate responses on any criteria.",
    Icon: BalanceOutlinedIcon,
  },
  {
    kind: "ml",
    label: "ML Evaluator",
    description: "Use a built-in ML model for PII detection, toxicity classification, or prompt injection detection.",
    Icon: PrecisionManufacturingOutlinedIcon,
  },
];

const CreateEvalTypeModal = ({ open, onClose, onSelectType }: CreateEvalTypeModalProps) => {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Create New Evaluator</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Choose the type of evaluator to create.
        </Typography>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pb: 1 }}>
          {TYPE_OPTIONS.map(({ kind, label, description, Icon }) => (
            <Card key={kind} variant="outlined" sx={{ "&:hover": { borderColor: "primary.main" } }}>
              <CardActionArea onClick={() => onSelectType(kind)} sx={{ p: 0 }}>
                <CardContent sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
                  <Icon sx={{ fontSize: 36, color: "primary.main", mt: 0.5 }} />
                  <Box>
                    <Typography variant="subtitle1" fontWeight={600}>
                      {label}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {description}
                    </Typography>
                  </Box>
                </CardContent>
              </CardActionArea>
            </Card>
          ))}
        </Box>
        <Box sx={{ display: "flex", justifyContent: "flex-end", pt: 1 }}>
          <Button variant="text" onClick={onClose}>
            Cancel
          </Button>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default CreateEvalTypeModal;
