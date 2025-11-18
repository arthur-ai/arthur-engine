import { useQueryClient } from "@tanstack/react-query";
import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";

import { AuthService, AuthState } from "@/lib/auth";
import { track, clearUser } from "@/services/amplitude";

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

  const queryClient = useQueryClient();
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
            // Track successful token validation on app load
            track("Session Restored", {
              authentication_method: "api_key",
            });
          } else {
            setAuthState({
              isAuthenticated: false,
              token: null,
              isLoading: false,
              error: "Token is invalid or expired",
            });
            // Track token validation failure
            track("Token Validation Failed", {
              authentication_method: "api_key",
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
        // Track initialization error
        track("Auth Initialization Failed", {
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
      if (success) {
        setAuthState({
          isAuthenticated: true,
          token,
          isLoading: false,
          error: null,
        });
        // Track successful login with API key authentication
        track("Login", {
          authentication_method: "api_key",
        });
        return true;
      } else {
        setAuthState((prev) => ({
          ...prev,
          isLoading: false,
          error: "Invalid token or authentication failed",
        }));
        // Track failed login attempt
        track("Login Failed", {
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
      track("Login Failed", {
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
    track("Logout", {
      authentication_method: "api_key",
    });
    // Clear user identification in Amplitude
    clearUser();

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
        queryClient.clear();

        setAuthState((prev) => ({
          ...prev,
          isAuthenticated: false,
          token: null,
          error: "Token validation failed",
        }));
        // Track token validation failure
        track("Token Validation Failed", {
          authentication_method: "api_key",
          error: "Token validation failed",
        });
        // Clear user identification when token is invalid
        clearUser();
      }
      return isValid;
    } catch {
      queryClient.clear();

      setAuthState((prev) => ({
        ...prev,
        isAuthenticated: false,
        token: null,
        error: "Token validation failed",
      }));
      // Track token validation error
      track("Token Validation Failed", {
        authentication_method: "api_key",
        error: "Token validation failed",
      });
      // Clear user identification when token validation errors
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
