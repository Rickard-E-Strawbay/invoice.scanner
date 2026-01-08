import React, { useState, useContext } from "react";
import "./Auth.css";
import { AuthContext } from "../contexts/AuthContext";
import TermsOfService from "./TermsOfService";
import { validatePasswordStrength, getPasswordStrengthLabel, getPasswordStrengthColor } from "../utils/passwordValidator";
import { apiGet, apiPost } from "../utils/api";

function Auth() {
  const [mode, setMode] = useState("login"); // "login", "signup", or "forgot-password"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordValidation, setPasswordValidation] = useState(null);
  const [companyName, setCompanyName] = useState("");
  const [organizationId, setOrganizationId] = useState("");
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [tosVersion, setTosVersion] = useState("");
  const [showTermsModal, setShowTermsModal] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [companySuggestions, setCompanySuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [companyExists, setCompanyExists] = useState(false);
  const [showPendingApprovalDialog, setShowPendingApprovalDialog] = useState(false);
  const [pendingCompanyInfo, setPendingCompanyInfo] = useState(null);
  const [forgotPasswordSuccess, setForgotPasswordSuccess] = useState(false);
  const { login, signup } = useContext(AuthContext);

  const handleCompanyNameChange = async (value) => {
    setCompanyName(value);
    
    if (value.length < 2) {
      setCompanySuggestions([]);
      setShowSuggestions(false);
      setCompanyExists(false);
      return;
    }

    try {
      const endpoint = `/auth/search-companies?q=${encodeURIComponent(value)}`;
      console.log("Searching companies with:", endpoint);
      const res = await apiGet(endpoint);
      const data = await res.json();
      console.log("Search results:", data);
      setCompanySuggestions(data.companies || []);
      // Company exists if we got any suggestions
      setCompanyExists(data.companies && data.companies.length > 0);
      if (data.companies && data.companies.length > 0) {
        setShowSuggestions(true);
      }
    } catch (err) {
      console.error("Error searching companies:", err);
      setCompanySuggestions([]);
      setCompanyExists(false);
    }
  };

  const handleSelectCompany = (company) => {
    setCompanyName(company.company_name);
    setOrganizationId(company.organization_id);
    setShowSuggestions(false);
    setCompanySuggestions([]);
    setCompanyExists(true);
  };

  const handlePasswordChange = (value) => {
    setPassword(value);
    if (mode === "signup" || mode === "forgot-password") {
      const validation = validatePasswordStrength(value);
      setPasswordValidation(validation);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (mode === "signup" && !termsAccepted) {
      setError("You must accept the Terms of Service");
      return;
    }

    // Validate password strength for signup and forgot-password modes
    if ((mode === "signup" || mode === "forgot-password") && password) {
      const validation = validatePasswordStrength(password);
      if (!validation.isValid) {
        setError(validation.errors[0] || "Password does not meet requirements");
        setLoading(false);
        return;
      }
    }
    
    setError("");
    setLoading(true);

    try {
      if (mode === "login") {
        const res = await apiPost("/auth/login", { email, password });

        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.error || "Login failed");
        }

        const data = await res.json();
        login(data.user);
        setEmail("");
        setPassword("");
      } else if (mode === "forgot-password") {
        const res = await apiPost("/auth/request-password-reset", { email });

        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.error || "Request failed");
        }

        setForgotPasswordSuccess(true);
        setEmail("");
      } else {
        const res = await apiPost("/auth/signup", {
          email,
          password,
          company_name: companyName,
          organization_id: organizationId,
          terms_accepted: termsAccepted,
          terms_version: tosVersion
        });

        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.error || "Signup failed");
        }

        const data = await res.json();
        
        // Check if company is not enabled (either new company or existing company waiting approval)
        if (data.is_new_company || data.company_enabled === false) {
          setPendingCompanyInfo(data);
          setShowPendingApprovalDialog(true);
          setEmail("");
          setPassword("");
          setCompanyName("");
          setOrganizationId("");
          setTermsAccepted(false);
          return;
        }
        
        signup(data.user);
        setEmail("");
        setPassword("");
        setCompanyName("");
        setOrganizationId("");
        setTermsAccepted(false);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTermsAccept = (version) => {
    setTermsAccepted(true);
    setTosVersion(version);
    setShowTermsModal(false);
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        {forgotPasswordSuccess ? (
          <>
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
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="16 12 12 8 8 12"></polyline>
                <polyline points="12 16 12 8"></polyline>
              </svg>
              <h1 style={{ color: "#10b981" }}>Check Your Email</h1>
              <p style={{ color: "#666", marginBottom: "1.5rem" }}>
                If an account exists for <strong>{email}</strong>, a password reset link has been sent. Please check your email and follow the link to reset your password.
              </p>
              <button
                type="button"
                onClick={() => {
                  setForgotPasswordSuccess(false);
                  setMode("login");
                  setError("");
                }}
                style={{
                  padding: "0.75rem 1.5rem",
                  background: "#7265cf",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontWeight: "600",
                }}
                onMouseEnter={(e) => (e.target.style.backgroundColor = "#5e52a3")}
                onMouseLeave={(e) => (e.target.style.backgroundColor = "#7265cf")}
              >
                Back to Login
              </button>
            </div>
          </>
        ) : (
          <>
            <h1>
              {mode === "login" ? "Login" : mode === "forgot-password" ? "Reset Password" : "Sign Up"}
            </h1>

            {error && <div className="auth-error">{error}</div>}

            <form onSubmit={handleSubmit} className="auth-form">
              <div className="form-group">
                <label htmlFor="email">Email:</label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={loading}
                />
              </div>

              {mode !== "forgot-password" && (
                <div className="form-group">
                  <label htmlFor="password">Password:</label>
                  <input
                    type="password"
                    id="password"
                    value={password}
                    onChange={(e) => handlePasswordChange(e.target.value)}
                    required
                    disabled={loading}
                  />
                  {(mode === "signup") && password && (
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
              )}

              {mode === "forgot-password" && (
                <div className="form-group">
                  <label htmlFor="password">New Password:</label>
                  <input
                    type="password"
                    id="password"
                    value={password}
                    onChange={(e) => handlePasswordChange(e.target.value)}
                    required
                    disabled={loading}
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
              )}

              {mode === "signup" && (
                <>
                  <div className="form-group">
                    <label htmlFor="company-name">Company Name:</label>
                    <div className="company-search-container">
                      <input
                        type="text"
                        id="company-name"
                        value={companyName}
                        onChange={(e) => handleCompanyNameChange(e.target.value)}
                        onFocus={() => {
                          if (companyName.length >= 2 && companySuggestions.length > 0) {
                            setShowSuggestions(true);
                          }
                        }}
                        onBlur={() => setTimeout(() => setShowSuggestions(false), 300)}
                        required
                        disabled={loading}
                        placeholder="Search or enter company name"
                      />
                      {showSuggestions && companySuggestions.length > 0 && (
                        <ul className="company-suggestions">
                          {companySuggestions.map((company, index) => (
                            <li key={index} onClick={() => handleSelectCompany(company)}>
                              <strong>{company.company_name}</strong>
                              <span className="org-id"> ({company.organization_id})</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>

                  <div className="form-group">
                    <label htmlFor="organization-id">Organization ID:</label>
                    <input
                      type="text"
                      id="organization-id"
                      value={organizationId}
                      onChange={(e) => setOrganizationId(e.target.value)}
                      required
                      disabled={loading || !companyName || companyExists}
                      placeholder={companyExists ? "Auto-filled when selecting a company" : "Enter organization ID for new company"}
                    />
                  </div>

                  <div className="form-group terms-group">
                    <label className="terms-label">
                      <input
                        type="checkbox"
                        checked={termsAccepted}
                        onChange={(e) => setTermsAccepted(e.target.checked)}
                        disabled={true}
                      />
                      <span>
                        I accept the{" "}
                        <button
                          type="button"
                          className="terms-link"
                          onClick={() => setShowTermsModal(true)}
                        >
                          Terms of Service
                        </button>
                      </span>
                    </label>
                  </div>
                </>
              )}

              <button type="submit" disabled={loading} className="auth-button">
                {loading
                  ? "Loading..."
                  : mode === "login"
                  ? "Login"
                  : mode === "forgot-password"
                  ? "Send Reset Link"
                  : "Sign Up"}
              </button>
            </form>

            <div style={{ marginTop: "1.5rem" }}>
              <p className="auth-toggle">
                {mode === "login" ? (
                  <>
                    Don't have an account?{" "}
                    <button
                      type="button"
                      onClick={() => {
                        setMode("signup");
                        setError("");
                        setTermsAccepted(false);
                        setCompanyExists(false);
                      }}
                      className="auth-toggle-btn"
                    >
                      Sign Up
                    </button>
                  </>
                ) : mode === "signup" ? (
                  <>
                    Already have an account?{" "}
                    <button
                      type="button"
                      onClick={() => {
                        setMode("login");
                        setError("");
                        setTermsAccepted(false);
                        setCompanyExists(false);
                      }}
                      className="auth-toggle-btn"
                    >
                      Login
                    </button>
                  </>
                ) : (
                  <>
                    Remember your password?{" "}
                    <button
                      type="button"
                      onClick={() => {
                        setMode("login");
                        setError("");
                      }}
                      className="auth-toggle-btn"
                    >
                      Login
                    </button>
                  </>
                )}
              </p>

              {mode === "login" && (
                <p className="auth-toggle">
                  <button
                    type="button"
                    onClick={() => {
                      setMode("forgot-password");
                      setError("");
                    }}
                    className="auth-toggle-btn"
                  >
                    Forgot Password?
                  </button>
                </p>
              )}
            </div>
          </>
        )}
      </div>

      {showTermsModal && (
        <TermsOfService
          onAccept={handleTermsAccept}
          onClose={() => setShowTermsModal(false)}
        />
      )}

      {showPendingApprovalDialog && (
        <div className="auth-modal-overlay">
          <div className="auth-modal">
            <div className="auth-modal-content">
              {pendingCompanyInfo?.is_new_company ? (
                <>
                  <h2>Company Registration Pending</h2>
                  <div className="pending-approval-icon">✓</div>
                  <p>
                    Thank you for registering! Your company <strong>{pendingCompanyInfo?.company_name}</strong> has been created successfully.
                  </p>
                  <p>
                    A system administrator will review and approve your company registration shortly. 
                    Once approved, you'll receive a confirmation email at <strong>{pendingCompanyInfo?.email}</strong>.
                  </p>
                  <p className="pending-approval-info">
                    You will then be able to log in and access the system.
                  </p>
                </>
              ) : (
                <>
                  <h2>Your Account is Under Review</h2>
                  <div className="pending-approval-icon">📋</div>
                  <p>
                    Thank you for registering! Your account has been created for <strong>{pendingCompanyInfo?.company_name}</strong>.
                  </p>
                  {pendingCompanyInfo?.company_enabled === false ? (
                    <>
                      <p>
                        Your company is currently pending approval from Strawbay. Once your company has been approved, your account will be reviewed by your company administrator.
                      </p>
                      <p className="pending-approval-info">
                        You'll receive a confirmation email at <strong>{pendingCompanyInfo?.email}</strong> when everything is ready.
                      </p>
                    </>
                  ) : (
                    <>
                      <p>
                        Your company administrator will review your account request and approve or decline it. The following person will handle your approval:
                      </p>
                      <div style={{ background: "#f5f5f5", padding: "1rem", borderRadius: "6px", margin: "1rem 0" }}>
                        <p><strong>📋 Company Administrator</strong></p>
                        <p>Name: {pendingCompanyInfo?.admin_name || "Company Administrator"}</p>
                        <p>Email: {pendingCompanyInfo?.admin_email || ""}</p>
                      </div>
                      <p className="pending-approval-info">
                        You'll receive a confirmation email at <strong>{pendingCompanyInfo?.email}</strong> once they've reviewed your account.
                      </p>
                    </>
                  )}
                </>
              )}
              <button
                onClick={() => {
                  setShowPendingApprovalDialog(false);
                  setMode("login");
                }}
                className="auth-button"
              >
                Return to Login
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Auth;
