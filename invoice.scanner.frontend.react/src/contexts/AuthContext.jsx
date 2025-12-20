import React, { createContext, useState, useEffect } from "react";

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
      const res = await fetch("http://localhost:8000/auth/me", {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
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
      await fetch("http://localhost:8000/auth/logout", {
        method: "POST",
        credentials: "include",
      });
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
