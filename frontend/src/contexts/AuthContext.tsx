import React, { createContext, useContext, useState, useEffect } from "react";
import { getMe } from "../api/auth";
import type { UserProfile } from "../api/auth";

interface AuthContextType {
  user: UserProfile | null;
  role: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setAuth: (user: UserProfile, access: string, refresh: string) => void;
  clearAuth: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem("access_token");
      if (token) {
        try {
          const profile = await getMe();
          setUser(profile);
        } catch (error) {
          console.error("Failed to restore session", error);
          clearAuth();
        }
      }
      setIsLoading(false);
    };

    initAuth();

    // Listen for the custom event from the axios interceptor
    const handleAuthFailed = () => clearAuth();
    window.addEventListener("auth_refresh_failed", handleAuthFailed);
    return () => window.removeEventListener("auth_refresh_failed", handleAuthFailed);
  }, []);

  const setAuth = (newUser: UserProfile, access: string, refresh: string) => {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
    setUser(newUser);
  };

  const clearAuth = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role: user?.role || null,
        isAuthenticated: !!user,
        isLoading,
        setAuth,
        clearAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
