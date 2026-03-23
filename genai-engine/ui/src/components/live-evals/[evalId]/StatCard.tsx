import { Box, Paper, Stack, Typography } from "@mui/material";

export interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  subValue?: string;
  color?: "default" | "success" | "error" | "warning" | "info";
}

const colorMap = {
  default: "text.secondary",
  success: "success.main",
  error: "error.main",
  warning: "warning.main",
  info: "info.main",
};

export const StatCard = ({ icon, label, value, subValue, color = "default" }: StatCardProps) => {
  return (
    <Paper variant="outlined" sx={{ p: 2.5, flex: 1, minWidth: 160 }}>
      <Stack direction="row" spacing={1.5} alignItems="flex-start">
        <Box sx={{ color: colorMap[color], mt: 0.5 }}>{icon}</Box>
        <Stack spacing={0.5}>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: 0.5, fontSize: "0.65rem" }}>
            {label}
          </Typography>
          <Typography variant="h5" fontWeight={600} color={colorMap[color]}>
            {value}
          </Typography>
          {subValue && (
            <Typography variant="caption" color="text.secondary">
              {subValue}
            </Typography>
          )}
        </Stack>
      </Stack>
    </Paper>
  );
};
