
"use client";

import React, { createContext, useContext, useEffect, useState } from 'react';


interface TelemetryContextType {
  userId: string;
  sessionId: string;
  newSession: () => void;
  getTelemetryHeaders: () => Record<string, string>;
  setTelemetryCookies: () => void;
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
    setTelemetryCookies();
    
    console.log('🔄 New session created:', {
      userId,
      newSessionId,
      timestamp: new Date().toISOString()
    });
  };

  const setTelemetryCookies = () => {
    if (typeof window !== 'undefined') {
      // Set cookies that will be sent with requests
      document.cookie = `analytics-user-id=${userId}; path=/; max-age=31536000`; // 1 year
      document.cookie = `analytics-session-id=${sessionId}; path=/; max-age=86400`; // 1 day
      
      console.log('🍪 Telemetry cookies set:', {
        userId,
        sessionId,
        cookies: document.cookie
      });
    }
  };

  const getTelemetryHeaders = () => {
    return {
      'x-user-id': userId,
      'x-session-id': sessionId,
    };
  };

  useEffect(() => {
    // Set cookies on mount with the initialized session ID
    setTelemetryCookies();
  }, []);

  return (
    <TelemetryContext.Provider value={{ userId, sessionId, newSession, getTelemetryHeaders, setTelemetryCookies }}>
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