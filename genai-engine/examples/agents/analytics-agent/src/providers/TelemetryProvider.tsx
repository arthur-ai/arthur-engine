
"use client";

import React, { createContext, useContext, useEffect, useState } from 'react';


interface TelemetryContextType {
  userId: string;
  sessionId: string;
  newSession: () => void;
  getTelemetryHeaders: () => Record<string, string>;
  setTelemetryHeaders: () => void;
}

const TelemetryContext = createContext<TelemetryContextType | null>(null);

export function TelemetryProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      // Try to get existing session ID from localStorage first
      let storedSessionId = localStorage.getItem('analytics-agent-session-id');
      if (!storedSessionId) {
        storedSessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        localStorage.setItem('analytics-agent-session-id', storedSessionId);
      }
      return storedSessionId;
    }
    return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  });
  const [userId] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      let storedUserId = localStorage.getItem('analytics-agent-user-id');
      if (!storedUserId) {
        storedUserId = `user-${Math.random().toString(36).substr(2, 9)}`;
        localStorage.setItem('analytics-agent-user-id', storedUserId);
      }
      return storedUserId;
    }
    return `user-${Math.random().toString(36).substr(2, 9)}`;
  });

  const newSession = () => {
    const newSessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setSessionId(newSessionId);
    if (typeof window !== 'undefined') {
      localStorage.setItem('analytics-agent-session-id', newSessionId);
    }
    setTelemetryHeaders();
    
  };

  const setTelemetryHeaders = () => {
    // Headers are set automatically via getTelemetryHeaders() when making requests
  };

  const getTelemetryHeaders = () => {
    return {
      'x-user-id': userId,
      'x-session-id': sessionId,
    };
  };

  useEffect(() => {
    // Initialize headers on mount with the initialized session ID
    setTelemetryHeaders();
  }, []);

  return (
    <TelemetryContext.Provider value={{ userId, sessionId, newSession, getTelemetryHeaders, setTelemetryHeaders }}>
      {children}
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