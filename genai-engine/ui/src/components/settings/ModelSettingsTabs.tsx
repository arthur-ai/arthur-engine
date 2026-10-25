import { Tab, Tabs } from "@mui/material";
import { Link, useLocation } from "react-router";

import { useGuardrailPermissions } from "@/components/model-providers/hooks/useGuardrailConfiguration";

export const ModelSettingsTabs = () => {
  const { pathname } = useLocation();
  const { canRead } = useGuardrailPermissions();
  if (!["/settings/model-providers", "/settings/guardrails"].includes(pathname)) return null;
  return (
    <Tabs value={pathname} aria-label="Model settings" sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
      <Tab label="Model Providers" value="/settings/model-providers" component={Link} to="/settings/model-providers" />
      {canRead && <Tab label="Guardrail Settings" value="/settings/guardrails" component={Link} to="/settings/guardrails" />}
    </Tabs>
  );
};
