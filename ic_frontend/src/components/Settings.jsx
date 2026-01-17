import React, { useContext, useEffect } from "react";
import { AuthContext } from "../contexts/AuthContext";
import MessageModal from "./MessageModal";
import "./Settings.css";
import { API_BASE_URL } from "../utils/api";

function Settings() {
  const { user, isAdmin, checkAuth } = useContext(AuthContext);
  const [activeTab, setActiveTab] = React.useState("profile");

  // Helper function to check if user is Company User (read-only access to company info)
  const isCompanyUser = () => {
    return user?.role_key === 10;
  };

  // Helper function to check if user is Company Admin (can edit company info)
  const isCompanyAdmin = () => {
    return user?.role_key === 50;
  };

  // Helper function to check if user has access to company settings
  const hasCompanyAccess = () => {
    return isCompanyAdmin() || isCompanyUser();
  };

  // Check for stored tab preference (from PlansAndBilling navigation)
  useEffect(() => {
    const storedTab = localStorage.getItem("settings-active-tab");
    if (storedTab) {
      setActiveTab(storedTab);
      localStorage.removeItem("settings-active-tab");
    }
  }, []);

  // Update form data when user context changes
  React.useEffect(() => {
    if (user) {
      setFormData((prev) => ({
        ...prev,
        name: user.name || "",
        email: user.email || "",
        receive_notifications: user.receive_notifications !== undefined ? user.receive_notifications : true,
        weekly_summary: user.weekly_summary !== undefined ? user.weekly_summary : true,
        marketing_opt_in: user.marketing_opt_in !== undefined ? user.marketing_opt_in : true,
      }));
    }
  }, [user]);

  const [formData, setFormData] = React.useState({
    name: user?.name || "",
    email: user?.email || "",
    company_name: user?.company_name || "",
    company_email: user?.company_email || "",
    organization_id: user?.organization_id || "",
    receive_notifications: user?.receive_notifications ?? true,
    weekly_summary: user?.weekly_summary ?? true,
    marketing_opt_in: user?.marketing_opt_in ?? true,
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
  const [currentPassword, setCurrentPassword] = React.useState("");
  const [newPassword, setNewPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [billingLoading, setBillingLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const [billingError, setBillingError] = React.useState(null);
  const [billingSuccess, setBillingSuccess] = React.useState(null);
  const [messageModal, setMessageModal] = React.useState({
    show: false,
    type: "success",
    title: "",
    message: ""
  });

  const [companySettings, setCompanySettings] = React.useState(null);
  const [companySettingsLoading, setCompanySettingsLoading] = React.useState(true);
  const [companySettingsError, setCompanySettingsError] = React.useState(null);
  const [editableSettings, setEditableSettings] = React.useState({});
  const [settingsSaving, setSettingsSaving] = React.useState(false);
  const [settingsSaved, setSettingsSaved] = React.useState(false);

  // Fetch company settings
  React.useEffect(() => {
    const fetchCompanySettings = async () => {
      try {
        setCompanySettingsLoading(true);
        setCompanySettingsError(null);
        const response = await fetch(`${API_BASE_URL}/live/company-settings`, {
          method: "GET",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (!response.ok) {
          throw new Error("Failed to fetch company settings");
        }

        const data = await response.json();
        const settings = data.company_settings || {};
        setCompanySettings(settings);
        
        // Populate editable settings with parameter values
        if (settings.scanner_settings?.parameters) {
          const paramValues = {};
          settings.scanner_settings.parameters.forEach(param => {
            paramValues[param.key] = param.value;
          });
          setEditableSettings(paramValues);
        }
      } catch (err) {
        console.error("Error fetching company settings:", err);
        setCompanySettingsError(err.message);
      } finally {
        setCompanySettingsLoading(false);
      }
    };

    fetchCompanySettings();
  }, []);

  // Fetch company information from backend
  React.useEffect(() => {
    const fetchCompanyInfo = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(`${API_BASE_URL}/live/company-info`, {
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
          company_email: data.company_email || "",
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
        const response = await fetch(`${API_BASE_URL}/live/payment-methods`, {
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
        const response = await fetch(`${API_BASE_URL}/live/billing-details`, {
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
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
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
    const requiredFields = ["billing_contact_name", "billing_contact_email", "country", "city", "postal_code", "street_address", "vat_number"];
    
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

  const handleSaveCompany = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/live/company-info`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          company_name: formData.company_name,
          company_email: formData.company_email
        })
      });

      if (response.ok) {
        const data = await response.json();
        setFormData((prev) => ({
          ...prev,
          company_name: data.company.company_name || "",
          company_email: data.company.company_email || ""
        }));
        setMessageModal({
          show: true,
          type: "success",
          title: "Company Updated",
          message: data.message || "Company information updated successfully"
        });
      } else {
        const error = await response.json();
        setMessageModal({
          show: true,
          type: "error",
          title: "Update Failed",
          message: error.error || "Failed to update company information"
        });
      }
    } catch (err) {
      console.error("Error saving company info:", err);
      setMessageModal({
        show: true,
        type: "error",
        title: "Error",
        message: "Error saving company information"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveBilling = async () => {
    if (!validateBillingForm()) return;

    try {
      setBillingLoading(true);
      setBillingError(null);
      setBillingSuccess(null);

      const response = await fetch(`${API_BASE_URL}/live/billing-details`, {
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
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`${API_BASE_URL}/live/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ 
          name: formData.name,
          receive_notifications: formData.receive_notifications,
          weekly_summary: formData.weekly_summary,
          marketing_opt_in: formData.marketing_opt_in
        })
      });

      if (response.ok) {
        const data = await response.json();
        // Update local form data and AuthContext
        setFormData((prev) => ({
          ...prev,
          name: data.user.name,
          receive_notifications: data.user.receive_notifications,
          weekly_summary: data.user.weekly_summary,
          marketing_opt_in: data.user.marketing_opt_in
        }));
        // Refresh user data in AuthContext
        await checkAuth();
        setMessageModal({
          show: true,
          type: "success",
          title: "Profile Updated",
          message: "Your profile has been updated successfully."
        });
      } else {
        const error = await response.json();
        setMessageModal({
          show: true,
          type: "error",
          title: "Update Failed",
          message: error.error || "Failed to update profile"
        });
      }
    } catch (err) {
      console.error("Error updating profile:", err);
      setMessageModal({
        show: true,
        type: "error",
        title: "Error",
        message: "An error occurred while updating your profile"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSettingChange = (paramKey, newValue) => {
    setEditableSettings(prev => ({
      ...prev,
      [paramKey]: newValue
    }));
    setSettingsSaved(false);
  };

  const handleSaveSettings = async () => {
    try {
      setSettingsSaving(true);
      setCompanySettingsError(null);

      // Build the settings object to send
      const settingsToSave = {
        scanner_settings: {
          name: companySettings.scanner_settings.name,
          parameters: companySettings.scanner_settings.parameters.map(param => ({
            ...param,
            value: editableSettings[param.key] ?? param.value
          }))
        }
      };

      const response = await fetch(`${API_BASE_URL}/live/company-settings`, {
        method: "PUT",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(settingsToSave)
      });

      if (!response.ok) {
        throw new Error("Failed to save company settings");
      }

      const data = await response.json();
      setCompanySettings(data.company_settings || {});
      setSettingsSaved(true);

      setMessageModal({
        show: true,
        type: "success",
        title: "Settings Saved",
        message: "Scanner settings have been updated successfully."
      });

      // Clear success message after 3 seconds
      setTimeout(() => setSettingsSaved(false), 3000);
    } catch (err) {
      console.error("Error saving company settings:", err);
      setCompanySettingsError(err.message);
      setMessageModal({
        show: true,
        type: "error",
        title: "Save Failed",
        message: err.message || "Failed to save company settings"
      });
    } finally {
      setSettingsSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (!currentPassword) {
      setMessageModal({
        show: true,
        type: "error",
        title: "Validation Error",
        message: "Nuvarande lösenord krävs!"
      });
      return;
    }
    if (newPassword !== confirmPassword) {
      setMessageModal({
        show: true,
        type: "error",
        title: "Validation Error",
        message: "Lösenorden matchar inte!"
      });
      return;
    }
    if (newPassword.length < 6) {
      setMessageModal({
        show: true,
        type: "error",
        title: "Validation Error",
        message: "Lösenordet måste vara minst 6 tecken långt!"
      });
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/live/change-password`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          old_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword
        })
      });

      if (response.ok) {
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
        setMessageModal({
          show: true,
          type: "success",
          title: "Password Changed",
          message: "Lösenord uppdaterat!"
        });
      } else {
        const error = await response.json();
        setMessageModal({
          show: true,
          type: "error",
          title: "Update Failed",
          message: error.error || "Failed to change password"
        });
      }
    } catch (err) {
      console.error("Error changing password:", err);
      setMessageModal({
        show: true,
        type: "error",
        title: "Error",
        message: "An error occurred while changing your password"
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <style>{`
        .info-icon {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 18px;
          height: 18px;
          border-radius: 50%;
          border: 1px solid #9ca3af;
          font-size: 0.75rem;
          color: #9ca3af;
          font-weight: 600;
          cursor: help;
          margin-left: 0.5rem;
          position: relative;
        }
        
        .tooltip-content {
          position: fixed;
          background: #1f2937;
          color: white;
          padding: 0.75rem;
          border-radius: 6px;
          font-size: 0.85rem;
          width: 220px;
          text-align: left;
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
          white-space: normal;
          z-index: 99999;
          opacity: 0;
          visibility: hidden;
          transition: opacity 0.2s ease, visibility 0.2s ease;
        }
        
        .tooltip-content::before {
          content: '';
          position: absolute;
          bottom: -5px;
          left: 50%;
          transform: translateX(-50%);
          width: 0;
          height: 0;
          border-left: 5px solid transparent;
          border-right: 5px solid transparent;
          border-top: 5px solid #1f2937;
        }
        
        .info-icon:hover .tooltip-content {
          opacity: 1;
          visibility: visible;
        }
      `}</style>
      
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
        {(isAdmin || hasCompanyAccess()) && (
          <button 
            className={`settings-tab ${activeTab === "company" ? "active" : ""}`}
            onClick={() => setActiveTab("company")}
          >
            Company Settings
          </button>
        )}
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
                  <input 
                    type="checkbox" 
                    id="notifications" 
                    name="receive_notifications"
                    checked={formData.receive_notifications}
                    onChange={handleInputChange}
                  />
                  <label htmlFor="notifications">Notifications</label>
                </div>

                <div className="form-group checkbox">
                  <input 
                    type="checkbox" 
                    id="weekly" 
                    name="weekly_summary"
                    checked={formData.weekly_summary}
                    onChange={handleInputChange}
                  />
                  <label htmlFor="weekly">Weekly Report</label>
                </div>

                <div className="form-group checkbox">
                  <input 
                    type="checkbox" 
                    id="productInfo" 
                    name="marketing_opt_in"
                    checked={formData.marketing_opt_in}
                    onChange={handleInputChange}
                  />
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
                  <label>Current Password</label>
                  <input
                    type={showPassword ? "text" : "password"}
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="Enter current password"
                  />
                </div>

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
              <h2>Company Information {isCompanyUser() && <span style={{fontSize: '0.8em', color: '#999'}}>(Read-only)</span>}</h2>
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
                      disabled={isCompanyUser()}
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

                  <div className="form-group">
                    <label>Company Email</label>
                    <input
                      type="email"
                      name="company_email"
                      value={formData.company_email}
                      onChange={handleInputChange}
                      placeholder="Company email address"
                      disabled={isCompanyUser()}
                    />
                  </div>

                  {(isAdmin || isCompanyAdmin()) && (
                    <button className="btn btn-primary" onClick={handleSaveCompany}>
                      Save Changes
                    </button>
                  )}
                </div>
              )}
            </section>

            {/* Company Settings Section */}
            <section className="settings-section">
              <h2>Scanner Settings</h2>
              {companySettingsError ? (
                <div style={{ color: '#d32f2f', marginBottom: '1rem' }}>Error: {companySettingsError}</div>
              ) : companySettingsLoading ? (
                <div style={{ color: '#666', padding: '1rem' }}>Loading scanner settings...</div>
              ) : (
                <div className="settings-form">
                  {companySettings?.scanner_settings?.parameters && companySettings.scanner_settings.parameters.length > 0 ? (
                    <div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        {companySettings.scanner_settings.parameters.map((param, index) => {
                          const isReadOnly = !(isAdmin || isCompanyAdmin());
                          const paramValue = editableSettings[param.key] ?? param.value;
                          
                          return (
                            <div key={index} className="form-group">
                              <label>
                                {param.name}
                                <div 
                                  className="info-icon"
                                  onMouseEnter={(e) => {
                                    const rect = e.currentTarget.getBoundingClientRect();
                                    const tooltip = e.currentTarget.querySelector('.tooltip-content');
                                    if (tooltip) {
                                      tooltip.style.top = (rect.top - tooltip.offsetHeight - 10) + "px";
                                      tooltip.style.left = (rect.left + rect.width / 2 - 110) + "px";
                                    }
                                  }}
                                >
                                  i
                                  <div className="tooltip-content">
                                    {param.description}
                                  </div>
                                </div>
                              </label>
                              
                              {param.type === 'boolean' && (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                  <input
                                    type="checkbox"
                                    id={`param_${param.key}`}
                                    checked={Boolean(paramValue)}
                                    onChange={(e) => handleSettingChange(param.key, e.target.checked)}
                                    disabled={isReadOnly}
                                  />
                                  <label htmlFor={`param_${param.key}`} style={{ margin: 0, fontWeight: 'normal', fontSize: '0.95rem' }}>
                                    {paramValue ? 'Enabled' : 'Disabled'}
                                  </label>
                                  {isReadOnly && (
                                    <span style={{ fontSize: '0.8em', color: '#999', marginLeft: '0.5rem' }}>
                                      (Read-only)
                                    </span>
                                  )}
                                </div>
                              )}
                              
                              {(param.type === 'float' || param.type === 'number') && (
                                <>
                                  <input
                                    type="number"
                                    step="0.01"
                                    value={paramValue}
                                    onChange={(e) => handleSettingChange(param.key, parseFloat(e.target.value))}
                                    disabled={isReadOnly}
                                  />
                                  {isReadOnly && (
                                    <div style={{ fontSize: '0.8em', color: '#999', marginTop: '0.3rem' }}>
                                      (Read-only)
                                    </div>
                                  )}
                                </>
                              )}
                              
                              {param.type === 'integer' && (
                                <>
                                  <input
                                    type="number"
                                    step="1"
                                    value={paramValue}
                                    onChange={(e) => handleSettingChange(param.key, parseInt(e.target.value))}
                                    disabled={isReadOnly}
                                  />
                                  {isReadOnly && (
                                    <div style={{ fontSize: '0.8em', color: '#999', marginTop: '0.3rem' }}>
                                      (Read-only)
                                    </div>
                                  )}
                                </>
                              )}
                              
                              {param.type === 'text' && (
                                <>
                                  <input
                                    type="text"
                                    value={paramValue}
                                    onChange={(e) => handleSettingChange(param.key, e.target.value)}
                                    disabled={isReadOnly}
                                  />
                                  {isReadOnly && (
                                    <div style={{ fontSize: '0.8em', color: '#999', marginTop: '0.3rem' }}>
                                      (Read-only)
                                    </div>
                                  )}
                                </>
                              )}
                            </div>
                          );
                        })}
                      </div>
                      
                      {(isAdmin || isCompanyAdmin()) && (
                        <div style={{ marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid #eee' }}>
                          {settingsSaved && (
                            <div style={{ color: '#2e7d32', marginBottom: '1rem', fontSize: '0.9em' }}>
                              ✅ Settings saved successfully
                            </div>
                          )}
                          <button
                            className="btn btn-primary"
                            onClick={handleSaveSettings}
                            disabled={settingsSaving}
                            style={{ minWidth: '150px' }}
                          >
                            {settingsSaving ? 'Saving...' : 'Save Changes'}
                          </button>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div style={{ backgroundColor: '#f5f5f5', padding: '1rem', borderRadius: '4px', fontFamily: 'monospace', fontSize: '0.9em' }}>
                      <pre style={{ margin: 0, color: '#333' }}>
                        {JSON.stringify(companySettings, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </section>

            {/* Billing Section - For Company Admins (editable) and Company Users (read-only) */}
            {(isAdmin || hasCompanyAccess()) && (
              <section className="settings-section">
                <h2>Billing Information {isCompanyUser() && <span style={{fontSize: '0.8em', color: '#999'}}>(Read-only)</span>}</h2>
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
                        disabled={isCompanyUser()}
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
                        disabled={isCompanyUser()}
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
                        disabled={isCompanyUser()}
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
                        disabled={isCompanyUser()}
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
                        disabled={isCompanyUser()}
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
                        disabled={isCompanyUser()}
                      />
                      {billingErrors.country && (
                        <p className="error-message">{billingErrors.country}</p>
                      )}
                    </div>

                    <div className="form-group">
                      <label>VAT Number *</label>
                      <input
                        type="text"
                        name="vat_number"
                        value={billingData.vat_number || ""}
                        onChange={handleBillingInputChange}
                        placeholder="VAT number"
                        className={billingErrors.vat_number ? "error" : ""}
                        disabled={isCompanyUser()}
                      />
                      {billingErrors.vat_number && (
                        <p className="error-message">{billingErrors.vat_number}</p>
                      )}
                    </div>

                    <div className="form-group">
                      <label>Payment Method</label>
                      <select
                        name="payment_method"
                        value={billingData.payment_method}
                        onChange={handleBillingInputChange}
                        className="form-select"
                        disabled={isCompanyUser()}
                      >
                        {paymentMethods.map((method) => (
                          <option key={method.key} value={method.key} disabled={!method.enabled}>
                            {method.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <button className="btn btn-primary" onClick={handleSaveBilling} disabled={billingLoading || isCompanyUser()}>
                      {billingLoading ? "Saving..." : "Save Changes"}
                    </button>
                  </div>
                )}
              </section>
            )}
          </>
        )}

      </div>

      {messageModal.show && (
        <MessageModal
          type={messageModal.type}
          title={messageModal.title}
          message={messageModal.message}
          onClose={() => setMessageModal({ ...messageModal, show: false })}
        />
      )}
    </>
  );
}

export default Settings;
