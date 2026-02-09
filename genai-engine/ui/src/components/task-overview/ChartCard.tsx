import { Box, Card, CardContent, Divider, Skeleton, Stack, Typography } from "@mui/material";

export interface ChartCardProps {
  icon: React.ReactNode;
  title: string;
  iconColor: string;
  isLoading: boolean;
  children: React.ReactNode;
}

export const ChartCard = ({ icon, title, iconColor, isLoading, children }: ChartCardProps) => {
  return (
    <Card variant="outlined">
      <Box sx={{ px: 3, py: 2 }}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Box sx={{ color: iconColor, display: "flex", alignItems: "center", fontSize: 18 }}>{icon}</Box>
          <Typography variant="subtitle1" fontWeight={600} color="text.primary">
            {title}
          </Typography>
        </Stack>
      </Box>
      <Divider />
      <CardContent sx={{ p: 3 }}>{isLoading ? <Skeleton variant="rectangular" height={256} sx={{ borderRadius: 1 }} /> : children}</CardContent>
    </Card>
  );
};
