import { Box, Link as MuiLink, Stack } from "@mui/material";
import { Link } from "react-router-dom";

import { ArthurLogo } from "../../common/ArthurLogo";

export const EngineTopNav: React.FC = () => (
  <Box
    sx={{
      height: 56,
      borderBottom: "1px solid",
      borderColor: "divider",
      backgroundColor: "background.paper",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      px: 3,
      flexShrink: 0,
    }}
  >
    <MuiLink to="/" underline="none" component={Link}>
      <ArthurLogo className="size-6" />
    </MuiLink>
    <Stack direction="row" spacing={2.5}>
      <MuiLink
        to="#"
        underline="hover"
        component={Link}
        sx={{ fontSize: 13, color: "text.secondary", fontWeight: 500, "&:hover": { color: "text.primary" } }}
      >
        Docs
      </MuiLink>
      <MuiLink
        to="#"
        underline="hover"
        component={Link}
        sx={{ fontSize: 13, color: "text.secondary", fontWeight: 500, "&:hover": { color: "text.primary" } }}
      >
        Status
      </MuiLink>
    </Stack>
  </Box>
);
