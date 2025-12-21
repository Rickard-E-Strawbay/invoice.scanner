import React, { useContext, useEffect } from "react";
import { AuthContext } from "../contexts/AuthContext";
import "./Settings.css";
import { API_BASE_URL } from "../utils/api";

function Settings() {
  const { user, isAdmin } = useContext(AuthContext);
  const [activeTab, setActiveTab] = React.useState("profile");

  // Check for stored tab preference (from PlansAndBilling navigation)
  useEffect(() => {
    const storedTab = localStorage.getItem("settings-active-tab");
    if (storedTab) {
      setActiveTab(storedTab);
      localStorage.removeItem("settings-active-tab");
    }
  }, []);

  const [formData, setFormData] = React.useState({
    name: user?.name || "",
    email: user?.email || "",
    company_name: user?.company_name || "",
    organization_id: user?.organization_id || "",
  });

  const [billingData, setBillingData] = React.useState({
    billing_contact_name: "",
    billing_contact_email: "",
    country: "",
    city: "",
    postal_code: "",
    street_address: "",
    vat_number: "",
    payment_method: "strawbay_invoice"
  });

  const [paymentMethods, setPaymentMethods] = React.useState([]);
  const [billingErrors, setBillingErrors] = React.useState({});
  const [showPassword, setShowPassword] = React.useState(false);
  const [newPassword, setNewPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [billingLoading, setBillingLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const [billingError, setBillingError] = React.useState(null);
  const [billingSuccess, setBillingSuccess] = React.useState(null);

  // Fetch company information from backend
  React.useEffect(() => {
    const fetchCompanyInfo = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(`${API_BASE_URL}/auth/company-info`, {
          method: "GET",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (!response.ok) {
          throw new Error("Failed to fetch company information");
        }

        const data = await response.json();
        setFormData((prev) => ({
          ...prev,
          company_name: data.company_name || "",
          organization_id: data.organization_id || "",
        }));
      } catch (err) {
        console.error("Error fetching company info:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchCompanyInfo();
  }, []);

  // Fetch payment methods
  React.useEffect(() => {
    const fetchPaymentMethods = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/payment-methods`, {
          method: "GET",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (response.ok) {
          const data = await response.json();
          setPaymentMethods(data.payment_methods || []);
        }
      } catch (err) {
        console.error("Error fetching payment methods:", err);
      }
    };

    fetchPaymentMethods();
  }, []);

  // Fetch billing details
  React.useEffect(() => {
    const fetchBillingDetails = async () => {
      try {
        setBillingLoading(true);
        setBillingError(null);
        const response = await fetch(`${API_BASE_URL}/auth/billing-details`, {
          method: "GET",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (response.ok) {
          const data = await response.json();
          if (data.billing) {
            setBillingData(data.billing);
          }
        }
      } catch (err) {
        console.error("Error fetching billing details:", err);
        setBillingError("Failed to load billing details");
      } finally {
        setBillingLoading(false);
      }
    };

    fetchBillingDetails();
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleBillingInputChange = (e) => {
    const { name, value } = e.target;
    setBillingData((prev) => ({
      ...prev,
      [name]: value,
    }));
    // Clear error for this field if it exists
    if (billingErrors[name]) {
      setBillingErrors((prev) => ({
        ...prev,
        [name]: null,
      }));
    }
  };

  const validateBillingForm = () => {
    const errors = {};
    const requiredFields = ["billing_contact_name", "billing_contact_email", "country", "city", "postal_code", "street_address"];
    
    requiredFields.forEach(field => {
      if (!billingData[field] || !billingData[field].trim()) {
        errors[field] = "This field is required";
      }
    });

    if (billingData.billing_contact_email && !billingData.billing_contact_email.includes("@")) {
      errors.billing_contact_email = "Please enter a valid email";
    }

    setBillingErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSaveBilling = async () => {
    if (!validateBillingForm()) return;

    try {
      setBillingLoading(true);
      setBillingError(null);
      setBillingSuccess(null);

      const response = await fetch(`${API_BASE_URL}/auth/billing-details`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(billingData)
      });

      if (response.ok) {
        const data = await response.json();
        setBillingData(data.billing);
        setBillingSuccess("Billing details saved successfully!");
        setTimeout(() => setBillingSuccess(null), 3000);
      } else {
        const error = await response.json();
        setBillingError(error.error || "Failed to save billing details");
      }
    } catch (err) {
      console.error("Error saving billing details:", err);
      setBillingError("Error saving billing details");
    } finally {
      setBillingLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    // TODO: Implement API call to save profile
    console.log("Saving profile:", formData);
    alert("Profil uppdaterad!");
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      alert("Lösenorden matchar inte!");
      return;
    }
    if (newPassword.length < 6) {
      alert("Lösenordet måste vara minst 6 tecken långt!");
      return;
    }
    // TODO: Implement API call to change password
    console.log("Changing password");
    setNewPassword("");
    setConfirmPassword("");
    alert("Lösenord uppdaterat!");
  };

  return (
    <>
      <div className="content-header">
        <h1>Settings</h1>
      </div>

      <div className="settings-tabs">
        <button 
          className={`settings-tab ${activeTab === "profile" ? "active" : ""}`}
          onClick={() => setActiveTab("profile")}
        >
          Profile Settings
        </button>
        <button 
          className={`settings-tab ${activeTab === "company" ? "active" : ""}`}
          onClick={() => setActiveTab("company")}
        >
          Company Settings
        </button>
      </div>

      <div className="settings-content">
        {/* Profile Settings Tab */}
        {activeTab === "profile" && (
          <>
            {/* Profile Section */}
            <section className="settings-section">
              <h2>Profile Settings</h2>
              <div className="settings-form">
                <div className="form-group">
                  <label>Name</label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder="Your name"
                  />
                </div>

                <div className="form-group">
                  <label>Email</label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    disabled
                    placeholder="Your email address"
                  />
                </div>

                <div className="form-group checkbox">
                  <input type="checkbox" id="notifications" defaultChecked />
                  <label htmlFor="notifications">Notifications</label>
                </div>

                <div className="form-group checkbox">
                  <input type="checkbox" id="weekly" defaultChecked />
                  <label htmlFor="weekly">Weekly Report</label>
                </div>

                <div className="form-group checkbox">
                  <input type="checkbox" id="productInfo" defaultChecked />
                  <label htmlFor="productInfo">Product Information</label>
                </div>

                <div className="account-info">
                  <div className="info-item">
                    <span className="info-label">Account Created:</span>
                    <span className="info-value">
                      {new Date().toLocaleDateString("sv-SE")}
                    </span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">Last Login:</span>
                    <span className="info-value">
                      {new Date().toLocaleDateString("sv-SE")}
                    </span>
                  </div>
                </div>

                <button className="btn btn-primary" onClick={handleSaveProfile}>
                  Save Changes
                </button>
              </div>
            </section>

            {/* Password Section */}
            <section className="settings-section">
              <h2>Change Password</h2>
              <div className="settings-form">
                <div className="form-group">
                  <label>New Password</label>
                  <div className="password-input-group">
                    <input
                      type={showPassword ? "text" : "password"}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Enter new password"
                    />
                    <button
                      type="button"
                      className="toggle-password"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                          <circle cx="12" cy="12" r="3"/>
                          <line x1="1" y1="1" x2="23" y2="23" stroke="currentColor" strokeWidth="2"/>
                        </svg>
                      ) : (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                          <circle cx="12" cy="12" r="3"/>
                        </svg>
                      )}
                    </button>
                  </div>
                </div>

                <div className="form-group">
                  <label>Confirm Password</label>
                  <input
                    type={showPassword ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm password"
                  />
                </div>

                <button className="btn btn-primary" onClick={handleChangePassword}>
                  Update Password
                </button>
              </div>
            </section>
          </>
        )}

        {/* Company Settings Tab */}
        {activeTab === "company" && (
          <>
            {/* Company Section */}
            <section className="settings-section">
              <h2>Company Information</h2>
              {error && <div style={{ color: '#d32f2f', marginBottom: '1rem' }}>Error: {error}</div>}
              {loading ? (
                <div style={{ color: '#666', padding: '1rem' }}>Loading company information...</div>
              ) : (
                <div className="settings-form">
                  <div className="form-group">
                    <label>Company Name</label>
                    <input
                      type="text"
                      name="company_name"
                      value={formData.company_name}
                      onChange={handleInputChange}
                      placeholder="Your company name"
                    />
                  </div>

                  <div className="form-group">
                    <label>Organization ID</label>
                    <input
                      type="text"
                      name="organization_id"
                      value={formData.organization_id}
                      disabled
                      placeholder="Organization ID"
                    />
                  </div>

                  <button className="btn btn-primary" onClick={handleSaveProfile}>
                    Save Changes
                  </button>
                </div>
              )}
            </section>

            {/* Billing Section - Only for Company Admins */}
            {isAdmin() && (
              <section className="settings-section">
                <h2>Billing Information</h2>
                {billingError && (
                  <div className="billing-message error">
                    {billingError}
                  </div>
                )}
                {billingSuccess && (
                  <div className="billing-message success">
                    {billingSuccess}
                  </div>
                )}
                {billingLoading ? (
                  <div className="loading-message">Loading billing information...</div>
                ) : (
                  <div className="settings-form">
                    <div className="form-group">
                      <label>Contact Name *</label>
                      <input
                        type="text"
                        name="billing_contact_name"
                        value={billingData.billing_contact_name}
                        onChange={handleBillingInputChange}
                        placeholder="Full name"
                        className={billingErrors.billing_contact_name ? "error" : ""}
                      />
                      {billingErrors.billing_contact_name && (
                        <p className="error-message">{billingErrors.billing_contact_name}</p>
                      )}
                    </div>

                    <div className="form-group">
                      <label>Email *</label>
                      <input
                        type="email"
                        name="billing_contact_email"
                        value={billingData.billing_contact_email}
                        onChange={handleBillingInputChange}
                        placeholder="Email address"
                        className={billingErrors.billing_contact_email ? "error" : ""}
                      />
                      {billingErrors.billing_contact_email && (
                        <p className="error-message">{billingErrors.billing_contact_email}</p>
                      )}
                    </div>

                    <div className="form-group">
                      <label>Street Address *</label>
                      <input
                        type="text"
                        name="street_address"
                        value={billingData.street_address}
                        onChange={handleBillingInputChange}
                        placeholder="Street address"
                        className={billingErrors.street_address ? "error" : ""}
                      />
                      {billingErrors.street_address && (
                        <p className="error-message">{billingErrors.street_address}</p>
                      )}
                    </div>

                    <div className="form-group">
                      <label>Postal Code *</label>
                      <input
                        type="text"
                        name="postal_code"
                        value={billingData.postal_code}
                        onChange={handleBillingInputChange}
                        placeholder="Postal code"
                        className={billingErrors.postal_code ? "error" : ""}
                      />
                      {billingErrors.postal_code && (
                        <p className="error-message">{billingErrors.postal_code}</p>
                      )}
                    </div>

                    <div className="form-group">
                      <label>City *</label>
                      <input
                        type="text"
                        name="city"
                        value={billingData.city}
                        onChange={handleBillingInputChange}
                        placeholder="City"
                        className={billingErrors.city ? "error" : ""}
                      />
                      {billingErrors.city && (
                        <p className="error-message">{billingErrors.city}</p>
                      )}
                    </div>

                    <div className="form-group">
                      <label>Country *</label>
                      <input
                        type="text"
                        name="country"
                        value={billingData.country}
                        onChange={handleBillingInputChange}
                        placeholder="Country"
                        className={billingErrors.country ? "error" : ""}
                      />
                      {billingErrors.country && (
                        <p className="error-message">{billingErrors.country}</p>
                      )}
                    </div>

                    <div className="form-group">
                      <label>VAT Number</label>
                      <input
                        type="text"
                        name="vat_number"
                        value={billingData.vat_number || ""}
                        onChange={handleBillingInputChange}
                        placeholder="VAT number (optional)"
                      />
                    </div>

                    <div className="form-group">
                      <label>Payment Method</label>
                      <select
                        name="payment_method"
                        value={billingData.payment_method}
                        onChange={handleBillingInputChange}
                        className="form-select"
                      >
                        {paymentMethods.map((method) => (
                          <option key={method.key} value={method.key} disabled={!method.enabled}>
                            {method.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <button className="btn btn-primary" onClick={handleSaveBilling} disabled={billingLoading}>
                      {billingLoading ? "Saving..." : "Save Changes"}
                    </button>
                  </div>
                )}
              </section>
            )}
          </>
        )}

      </div>
    </>
  );
}

export default Settings;
