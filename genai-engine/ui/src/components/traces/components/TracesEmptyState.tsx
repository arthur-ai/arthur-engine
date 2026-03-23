import FolderOpenIcon from "@mui/icons-material/FolderOpen";
import { Stack, Typography } from "@mui/material";

type Props = {
  title: string;
  children?: React.ReactNode;
};

export const TracesEmptyState = ({ title, children }: Props) => {
  return (
    <Stack
      gap={2}
      alignItems="center"
      justifyContent="center"
      sx={{
        backgroundColor: "background.paper",
        borderRadius: 2,
        borderColor: "divider",
      }}
      className="p-8 border"
    >
      <FolderOpenIcon sx={{ fontSize: 48, color: "text.primary" }} />
      <Typography variant="h5" sx={{ fontWeight: 500, color: "text.primary" }}>
        {title}
      </Typography>
      {children}
    </Stack>
  );
};
