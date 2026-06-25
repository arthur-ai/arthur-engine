import { type StatusPaletteKey, StatusBadge } from "@arthur/shared-components";
import type { SvgIconComponent } from "@mui/icons-material";
import CenterFocusStrongIcon from "@mui/icons-material/CenterFocusStrong";
import GppBadOutlinedIcon from "@mui/icons-material/GppBadOutlined";
import GppGoodOutlinedIcon from "@mui/icons-material/GppGoodOutlined";
import GppMaybeOutlinedIcon from "@mui/icons-material/GppMaybeOutlined";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import type { GuardrailInvocation, GuardrailStatus } from "../../utils/guardrails";

type StatusVisual = {
  Icon: SvgIconComponent;
  iconColor: string;
  paletteKey: StatusPaletteKey;
  label: string;
};

const STATUS_VISUALS: Record<GuardrailStatus, StatusVisual> = {
  passed: { Icon: GppGoodOutlinedIcon, iconColor: "success.main", paletteKey: "success", label: "Pass" },
  failed: { Icon: GppBadOutlinedIcon, iconColor: "error.main", paletteKey: "error", label: "Fail" },
  degraded: { Icon: GppMaybeOutlinedIcon, iconColor: "warning.main", paletteKey: "warning", label: "Degraded" },
};

type Props = {
  invocation: GuardrailInvocation;
  selected: boolean;
  onJump: () => void;
};

export function GuardrailInvocationRow({ invocation, selected, onJump }: Props) {
  const { Icon, iconColor, paletteKey, label } = STATUS_VISUALS[invocation.status];

  return (
    <Stack
      direction="row"
      alignItems="center"
      spacing={1.5}
      sx={{
        px: 1.5,
        py: 1,
        borderRadius: 1,
        bgcolor: selected ? "action.selected" : "transparent",
        "&:hover": { bgcolor: selected ? "action.selected" : "action.hover" },
      }}
    >
      <Icon sx={{ fontSize: 20, color: iconColor, flexShrink: 0 }} />

      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography variant="body2" fontWeight={600} noWrap>
          {invocation.name}
        </Typography>
        {invocation.parentSpanName && (
          <Typography variant="caption" color="text.secondary" component="div" noWrap>
            under {invocation.parentSpanName}
          </Typography>
        )}
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: "nowrap", flexShrink: 0 }}>
        {invocation.ruleCount} {invocation.ruleCount === 1 ? "rule" : "rules"}
      </Typography>

      <StatusBadge paletteKey={paletteKey} label={label} size="small" />

      <Button variant="text" size="small" startIcon={<CenterFocusStrongIcon />} onClick={onJump} sx={{ whiteSpace: "nowrap", flexShrink: 0 }}>
        Jump to span
      </Button>
    </Stack>
  );
}
