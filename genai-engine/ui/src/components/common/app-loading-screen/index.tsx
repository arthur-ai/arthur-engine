import { Box, CircularProgress } from "@mui/material";

export const AppLoadingScreen: React.FC = () => (
  <Box
    sx={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    }}
  >
    <CircularProgress color="primary" />
  </Box>
);
