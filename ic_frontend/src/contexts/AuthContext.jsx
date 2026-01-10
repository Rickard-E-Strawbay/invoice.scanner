import React, { createContext, useState, useEffect } from "react";
import { apiGet, apiPost } from "../utils/api";

export const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check if user is already logged in on mount
  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const res = await apiGet("/live/me");
      if (res.ok) {
        try {
          const data = await res.json();
          setUser(data);
        } catch (jsonErr) {
          console.error("Failed to parse JSON response:", jsonErr);
          console.error("Response text:", await res.clone().text());
        }
      }
    } catch (err) {
      console.error("Auth check failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const login = (userData) => {
    setUser(userData);
  };

  const signup = (userData) => {
    setUser(userData);
  };

  const logout = async () => {
    try {
      await apiPost("/auth/logout");
    } catch (err) {
      console.error("Logout failed:", err);
    } finally {
      setUser(null);
    }
  };

  const isAdmin = () => {
    return user?.role_key === 1000 || user?.role_key === 50;
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout, checkAuth, isAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}
