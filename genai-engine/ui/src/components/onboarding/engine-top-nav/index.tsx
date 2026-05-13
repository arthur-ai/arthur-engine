import { Box, Link, Stack, Typography } from "@mui/material";

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
    <Stack direction="row" alignItems="center" spacing={1}>
      <ArthurLogo style={{ width: 22, height: 22 }} />
      <Typography component="span" sx={{ fontSize: 16, fontWeight: 700, color: "text.primary", letterSpacing: "-0.01em" }}>
        Arthur
      </Typography>
      <Typography component="span" aria-hidden="true" sx={{ color: "text.disabled", fontWeight: 400, fontSize: 16, mx: 0.25 }}>
        /
      </Typography>
      <Box
        component="span"
        sx={{
          fontFamily: "Geist Mono, SF Mono, Menlo, Consolas, monospace",
          fontSize: 13,
          color: "text.secondary",
          backgroundColor: "action.hover",
          px: 1,
          py: "2px",
          borderRadius: "4px",
          letterSpacing: "-0.01em",
        }}
      >
        engine
      </Box>
    </Stack>
    <Stack direction="row" spacing={2.5}>
      <Link href="#" underline="hover" sx={{ fontSize: 13, color: "text.secondary", fontWeight: 500, "&:hover": { color: "text.primary" } }}>
        Docs
      </Link>
      <Link href="#" underline="hover" sx={{ fontSize: 13, color: "text.secondary", fontWeight: 500, "&:hover": { color: "text.primary" } }}>
        Status
      </Link>
    </Stack>
  </Box>
);
