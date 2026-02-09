import { Box, Paper, Skeleton, Stack, Typography } from "@mui/material";

export interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  subLabel: string;
  color: string;
  bgColor: string;
  borderColor: string;
  isLoading: boolean;
}

export const MetricCard = ({ icon, label, value, subLabel, color, bgColor, borderColor, isLoading }: MetricCardProps) => {
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2.5,
        bgcolor: bgColor,
        borderColor: borderColor,
      }}
    >
      <Stack spacing={1}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Box sx={{ color, display: "flex", alignItems: "center", fontSize: 18 }}>{icon}</Box>
          <Typography variant="body2" fontWeight={500} sx={{ color }}>
            {label}
          </Typography>
        </Stack>
        {isLoading ? (
          <Skeleton variant="text" width={80} height={40} />
        ) : (
          <Typography variant="h4" fontWeight={700} color="text.primary">
            {value}
          </Typography>
        )}
        <Typography variant="caption" color="text.secondary">
          {subLabel}
        </Typography>
      </Stack>
    </Paper>
  );
};
