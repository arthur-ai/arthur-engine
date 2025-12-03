import AddIcon from "@mui/icons-material/Add";
import { Box, Button, Typography } from "@mui/material";

interface TransformsHeaderProps {
  onCreateTransform: () => void;
}

const TransformsHeader: React.FC<TransformsHeaderProps> = ({ onCreateTransform }) => {
  return (
    <Box
      sx={{
        px: 3,
        py: 2,
        borderBottom: 1,
        borderColor: "divider",
        backgroundColor: "background.paper",
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Box>
          <Typography variant="h5" fontWeight="bold">
            Transforms
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Manage reusable data extraction transforms for this task
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={onCreateTransform}>
          Create Transform
        </Button>
      </Box>
    </Box>
  );
};

export default TransformsHeader;
