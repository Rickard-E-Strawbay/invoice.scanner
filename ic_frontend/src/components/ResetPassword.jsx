import React, { useState, useEffect } from "react";
import "./Auth.css";
import { validatePasswordStrength, getPasswordStrengthLabel, getPasswordStrengthColor } from "../utils/passwordValidator";
import { API_BASE_URL } from "../utils/api";

function ResetPassword({ token }) {
  const [loading, setLoading] = useState(true);
  const [validating, setValidating] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [password, setPassword] = useState("");
  const [passwordValidation, setPasswordValidation] = useState(null);
  const [confirmPassword, setConfirmPassword] = useState("");
  const [resetError, setResetError] = useState(null);
  const [resetSuccess, setResetSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    // Verify the reset token when component mounts
    verifyToken();
  }, [token]);

  const verifyToken = async () => {
    try {
      setValidating(true);
      const response = await fetch(`${API_BASE_URL}/live/verify-reset-token/${token}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await response.json();

      if (response.ok) {
        setTokenValid(true);
        setUserInfo(data);
      } else {
        setResetError(data.error || "Invalid or expired reset token");
      }
    } catch (err) {
      console.error("Error verifying token:", err);
      setResetError("Failed to verify reset token");
    } finally {
      setValidating(false);
      setLoading(false);
    }
  };

  const handlePasswordChange = (value) => {
    setPassword(value);
    const validation = validatePasswordStrength(value);
    setPasswordValidation(validation);
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setResetError(null);

    // Validation
    if (!password || !confirmPassword) {
      setResetError("Please fill in all fields");
      return;
    }

    // Validate password strength
    const validation = validatePasswordStrength(password);
    if (!validation.isValid) {
      setResetError(validation.errors[0] || "Password does not meet requirements");
      return;
    }

    if (password !== confirmPassword) {
      setResetError("Passwords do not match");
      return;
    }

    try {
      setSubmitting(true);
      const response = await fetch(`${API_BASE_URL}/live/reset-password/${token}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          password: password,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setResetSuccess(true);
        setTimeout(() => {
          window.location.href = "/";
        }, 3000);
      } else {
        setResetError(data.error || "Failed to reset password");
      }
    } catch (err) {
      console.error("Error resetting password:", err);
      setResetError("Failed to reset password. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || validating) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1>Resetting Password</h1>
          <p>Verifying reset link...</p>
        </div>
      </div>
    );
  }

  if (!tokenValid) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1>Invalid Reset Link</h1>
          <p style={{ color: "#ef4444", marginBottom: "1.5rem" }}>{resetError}</p>
          <a
            href="/"
            style={{
              display: "inline-block",
              padding: "0.75rem 1.5rem",
              background: "#7265cf",
              color: "white",
              textDecoration: "none",
              borderRadius: "6px",
              fontWeight: "600",
              transition: "background-color 0.3s",
            }}
            onMouseEnter={(e) => (e.target.style.backgroundColor = "#5e52a3")}
            onMouseLeave={(e) => (e.target.style.backgroundColor = "#7265cf")}
          >
            Back to Login
          </a>
        </div>
      </div>
    );
  }

  if (resetSuccess) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div style={{ textAlign: "center" }}>
            <svg
              width="64"
              height="64"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#10b981"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ marginBottom: "1rem" }}
            >
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <h1 style={{ color: "#10b981" }}>Password Reset Successful</h1>
            <p>Your password has been reset successfully.</p>
            <p>You will be redirected to login in a few seconds...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1>Reset Your Password</h1>
        <p style={{ color: "#666", marginBottom: "1.5rem" }}>
          Enter a new password for <strong>{userInfo?.email}</strong>
        </p>

        <form onSubmit={handleResetPassword}>
          {resetError && (
            <div
              style={{
                background: "#fee",
                color: "#c33",
                padding: "0.75rem",
                borderRadius: "4px",
                marginBottom: "1rem",
                fontSize: "0.9rem",
              }}
            >
              {resetError}
            </div>
          )}

          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "600" }}>
              New Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => handlePasswordChange(e.target.value)}
              placeholder="Enter your new password"
              disabled={submitting}
              style={{
                width: "100%",
                padding: "0.75rem",
                border: "1px solid #ccc",
                borderRadius: "4px",
                fontSize: "1rem",
                boxSizing: "border-box",
                opacity: submitting ? 0.6 : 1,
              }}
            />
            {password && (
              <div style={{ marginTop: "0.5rem" }}>
                <div style={{ marginBottom: "0.5rem" }}>
                  <div style={{
                    display: "flex",
                    gap: "0.25rem",
                    marginBottom: "0.25rem"
                  }}>
                    {[0, 1, 2, 3, 4].map((i) => (
                      <div
                        key={i}
                        style={{
                          flex: 1,
                          height: "4px",
                          background: i < passwordValidation.strength ? getPasswordStrengthColor(passwordValidation.strength) : "#e5e7eb",
                          borderRadius: "2px",
                        }}
                      />
                    ))}
                  </div>
                  <span style={{
                    fontSize: "0.8rem",
                    color: getPasswordStrengthColor(passwordValidation.strength),
                    fontWeight: "600"
                  }}>
                    {getPasswordStrengthLabel(passwordValidation.strength)}
                  </span>
                </div>
                {passwordValidation.errors.length > 0 && (
                  <div style={{ marginTop: "0.5rem" }}>
                    {passwordValidation.errors.map((error, idx) => (
                      <div key={idx} style={{
                        fontSize: "0.8rem",
                        color: "#ef4444",
                        marginBottom: "0.25rem"
                      }}>
                        • {error}
                      </div>
                    ))}
                  </div>
                )}
                {passwordValidation.feedback.length > 0 && passwordValidation.isValid && (
                  <div style={{ marginTop: "0.5rem" }}>
                    {passwordValidation.feedback.map((tip, idx) => (
                      <div key={idx} style={{
                        fontSize: "0.8rem",
                        color: "#10b981",
                        marginBottom: "0.25rem"
                      }}>
                        ✓ {tip}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <div style={{ marginBottom: "1.5rem" }}>
            <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "600" }}>
              Confirm Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm your new password"
              disabled={submitting}
              style={{
                width: "100%",
                padding: "0.75rem",
                border: "1px solid #ccc",
                borderRadius: "4px",
                fontSize: "1rem",
                boxSizing: "border-box",
                opacity: submitting ? 0.6 : 1,
              }}
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            style={{
              width: "100%",
              padding: "0.75rem",
              background: submitting ? "#ccc" : "#7265cf",
              color: "white",
              border: "none",
              borderRadius: "4px",
              fontSize: "1rem",
              fontWeight: "600",
              cursor: submitting ? "not-allowed" : "pointer",
              transition: "background-color 0.3s",
            }}
            onMouseEnter={(e) => {
              if (!submitting) {
                e.target.style.backgroundColor = "#5e52a3";
              }
            }}
            onMouseLeave={(e) => {
              if (!submitting) {
                e.target.style.backgroundColor = "#7265cf";
              }
            }}
          >
            {submitting ? "Resetting..." : "Reset Password"}
          </button>
        </form>

        <p style={{ textAlign: "center", marginTop: "1.5rem", color: "#999", fontSize: "0.9rem" }}>
          <a href="/" style={{ color: "#7265cf", textDecoration: "none" }}>
            Back to Login
          </a>
        </p>
      </div>
    </div>
  );
}

export default ResetPassword;
