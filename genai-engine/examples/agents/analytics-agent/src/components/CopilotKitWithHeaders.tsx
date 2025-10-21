"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { useTelemetry } from "@/providers/TelemetryProvider";
import { ReactNode } from "react";

interface CopilotKitWithHeadersProps {
  children: ReactNode;
}

export function CopilotKitWithHeaders({ children }: CopilotKitWithHeadersProps) {
  const { getTelemetryHeaders } = useTelemetry();

  return (
    <CopilotKit 
      runtimeUrl="/api/copilotkit" 
      agent="dataAnalystAgent"
      headers={getTelemetryHeaders()}
    >
      {children}
    </CopilotKit>
  );
}
