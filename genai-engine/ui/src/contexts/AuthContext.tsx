"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { AuthService, AuthState } from "@/lib/auth";

interface AuthContextType extends AuthState {
  login: (token: string) => Promise<boolean>;
  logout: () => void;
  validateToken: () => Promise<boolean>;
}

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
    isLoading: true,
    error: null,
  });

  const authService = AuthService.getInstance();

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        setAuthState((prev) => ({ ...prev, isLoading: true, error: null }));

        const token = authService.getToken();
        if (token) {
          // Validate the existing token
          const isValid = await authService.validateToken();
          if (isValid) {
            setAuthState({
              isAuthenticated: true,
              token,
              isLoading: false,
              error: null,
            });
          } else {
            setAuthState({
              isAuthenticated: false,
              token: null,
              isLoading: false,
              error: "Token is invalid or expired",
            });
          }
        } else {
          setAuthState({
            isAuthenticated: false,
            token: null,
            isLoading: false,
            error: null,
          });
        }
      } catch {
        setAuthState({
          isAuthenticated: false,
          token: null,
          isLoading: false,
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
      if (success) {
        setAuthState({
          isAuthenticated: true,
          token,
          isLoading: false,
          error: null,
        });
        return true;
      } else {
        setAuthState((prev) => ({
          ...prev,
          isLoading: false,
          error: "Invalid token or authentication failed",
        }));
        return false;
      }
    } catch {
      setAuthState((prev) => ({
        ...prev,
        isLoading: false,
        error: "Login failed",
      }));
      return false;
    }
  };

  const logout = () => {
    authService.logout();
    setAuthState({
      isAuthenticated: false,
      token: null,
      isLoading: false,
      error: null,
    });
  };

  const validateToken = async (): Promise<boolean> => {
    try {
      const isValid = await authService.validateToken();
      if (!isValid) {
        setAuthState((prev) => ({
          ...prev,
          isAuthenticated: false,
          token: null,
          error: "Token validation failed",
        }));
      }
      return isValid;
    } catch {
      setAuthState((prev) => ({
        ...prev,
        isAuthenticated: false,
        token: null,
        error: "Token validation failed",
      }));
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
