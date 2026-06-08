import { useQueryClient } from "@tanstack/react-query";
import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";

import { AuthService, AuthState, deriveIsTenant, MeResponse } from "@/lib/auth";
import { track, clearUser, EVENT_NAMES } from "@/services/amplitude";

interface AuthContextType extends AuthState {
  login: (token: string) => Promise<boolean>;
  logout: () => void;
  validateToken: () => Promise<boolean>;
}

const buildAuthenticatedState = (token: string, me: MeResponse): AuthState => ({
  isAuthenticated: true,
  token,
  me,
  isTenant: deriveIsTenant(me),
  isLoading: false,
  error: null,
});

const unauthenticatedState = (error: string | null = null): AuthState => ({
  isAuthenticated: false,
  token: null,
  me: null,
  isTenant: false,
  isLoading: false,
  error,
});

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    token: null,
    me: null,
    isTenant: false,
    isLoading: true,
    error: null,
  });

  const queryClient = useQueryClient();
  const authService = AuthService.getInstance();

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        setAuthState((prev) => ({ ...prev, isLoading: true, error: null }));

        const token = authService.getToken();
        if (token) {
          const isValid = await authService.validateToken();
          const me = authService.getMe();
          if (isValid && me) {
            setAuthState(buildAuthenticatedState(token, me));
            track(EVENT_NAMES.SESSION_RESTORED, {
              authentication_method: "api_key",
              is_tenant: deriveIsTenant(me),
            });
          } else {
            setAuthState(unauthenticatedState("Token is invalid or expired"));
            track(EVENT_NAMES.TOKEN_VALIDATION_FAILED, {
              authentication_method: "api_key",
              error: "Token is invalid or expired",
            });
          }
        } else {
          setAuthState(unauthenticatedState());
        }
      } catch {
        setAuthState(unauthenticatedState("Failed to initialize authentication"));
        track(EVENT_NAMES.AUTH_INITIALIZATION_FAILED, {
          authentication_method: "api_key",
          error: "Failed to initialize authentication",
        });
      }
    };

    initializeAuth();
  }, [authService]);

  const login = async (token: string): Promise<boolean> => {
    try {
      setAuthState((prev) => ({ ...prev, isLoading: true, error: null }));

      const success = await authService.login(token);
      const me = authService.getMe();
      if (success && me) {
        setAuthState(buildAuthenticatedState(token, me));
        track(EVENT_NAMES.LOGIN, {
          authentication_method: "api_key",
          is_tenant: deriveIsTenant(me),
        });
        return true;
      } else {
        setAuthState((prev) => ({
          ...prev,
          isLoading: false,
          error: "Invalid token or authentication failed",
        }));
        // Track failed login attempt
        track(EVENT_NAMES.LOGIN_FAILED, {
          authentication_method: "api_key",
          error: "Invalid token or authentication failed",
        });
        return false;
      }
    } catch {
      setAuthState((prev) => ({
        ...prev,
        isLoading: false,
        error: "Login failed",
      }));
      // Track login error
      track(EVENT_NAMES.LOGIN_FAILED, {
        authentication_method: "api_key",
        error: "Login failed",
      });
      return false;
    }
  };

  const logout = () => {
    authService.logout();

    queryClient.clear();

    // Track logout event
    track(EVENT_NAMES.LOGOUT, {
      authentication_method: "api_key",
    });
    // Clear user identification in Amplitude
    clearUser();

    setAuthState(unauthenticatedState());
  };

  const validateToken = async (): Promise<boolean> => {
    try {
      const isValid = await authService.validateToken();
      if (isValid) {
        const token = authService.getToken();
        const me = authService.getMe();
        if (token && me) {
          setAuthState(buildAuthenticatedState(token, me));
        }
        return true;
      }
      queryClient.clear();
      setAuthState(unauthenticatedState("Token validation failed"));
      track(EVENT_NAMES.TOKEN_VALIDATION_FAILED, {
        authentication_method: "api_key",
        error: "Token validation failed",
      });
      clearUser();
      return false;
    } catch {
      queryClient.clear();
      setAuthState(unauthenticatedState("Token validation failed"));
      track(EVENT_NAMES.TOKEN_VALIDATION_FAILED, {
        authentication_method: "api_key",
        error: "Token validation failed",
      });
      clearUser();
      return false;
    }
  };

  const value: AuthContextType = {
    ...authState,
    login,
    logout,
    validateToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
