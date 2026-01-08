import React, { useContext, useEffect, useState } from "react";
import { AuthContext } from "./contexts/AuthContext";
import Auth from "./components/Auth";
import Dashboard from "./components/Dashboard";
import ResetPassword from "./components/ResetPassword";
import "./App.css";

function App() {
  const { user, loading } = useContext(AuthContext);
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [resetToken, setResetToken] = useState(null);

  useEffect(() => {
    // Check if we're on a reset-password URL
    const path = window.location.pathname;
    if (path.startsWith("/reset-password/")) {
      const token = path.split("/reset-password/")[1];
      setResetToken(token);
      setShowResetPassword(true);
    }
  }, []);

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (showResetPassword && resetToken) {
    return <ResetPassword token={resetToken} />;
  }

  if (!user) {
    return <Auth />;
  }

  return <Dashboard />;
}

export default App;
