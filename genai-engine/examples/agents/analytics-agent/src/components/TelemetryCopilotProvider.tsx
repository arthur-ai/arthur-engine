"use client";

import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { CopilotKit } from "@copilotkit/react-core";


interface TelemetryContextType {
  userId: string;
  sessionId: string;
  newSession: () => void;
  getTelemetryHeaders: () => Record<string, string>;
}

function generateId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

function generateUserId() {
  return `user-${generateId()}`;
}
function generateSessionId() {
  return `session-${generateId()}`;
}

const TelemetryContext = createContext<TelemetryContextType | null>(null);

export function TelemetryProvider({ children }: { children: React.ReactNode }) {
  // Use consistent initial state for SSR (empty strings, will be set in useEffect)
  const [sessionId, setSessionId] = useState<string>('');
  const [userId, setUserId] = useState<string>('');
  const [isMounted, setIsMounted] = useState(false);

  // Initialize from localStorage after mount to avoid hydration mismatch
  useEffect(() => {
    // Get or create session ID
    let storedSessionId = sessionStorage.getItem('analytics-agent-session-id');
    if (!storedSessionId) {
      storedSessionId = generateSessionId();
      sessionStorage.setItem('analytics-agent-session-id', storedSessionId);
    }
    setSessionId(storedSessionId);

    // Get or create user ID
    let storedUserId = localStorage.getItem('analytics-agent-user-id');
    if (!storedUserId) {
      storedUserId = generateUserId();
      localStorage.setItem('analytics-agent-user-id', storedUserId);
    }
    setUserId(storedUserId);

    setIsMounted(true);
  }, []);

  const newSession = () => {
    const newSessionId = generateSessionId();
    setSessionId(newSessionId);
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('analytics-agent-session-id', newSessionId);
    }
  };

  const getTelemetryHeaders = () => {
    return {
      'x-user-id': userId,
      'x-session-id': sessionId,
    };
  };

  // Create headers object that updates when sessionId or userId changes
  // Use empty headers during SSR to avoid hydration mismatch
  const headers = useMemo((): Record<string, string> => {
    if (!isMounted || !userId || !sessionId) {
      return {};
    }
    return {
      'x-user-id': userId,
      'x-session-id': sessionId,
    };
  }, [userId, sessionId, isMounted]);

  return (
    <TelemetryContext.Provider value={{ userId, sessionId, newSession, getTelemetryHeaders }}>
      <CopilotKit 
        runtimeUrl="/api/copilotkit" 
        agent="dataAnalystAgent"
        headers={headers}
      >
        {children}
      </CopilotKit>
    </TelemetryContext.Provider>
  );
}

export const useTelemetry = () => {
  const context = useContext(TelemetryContext);
  if (!context) {
    throw new Error('useTelemetry must be used within TelemetryProvider');
  }
  return context;
};
