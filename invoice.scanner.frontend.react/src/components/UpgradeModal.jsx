import React, { useState, useEffect, useContext } from "react";
import { AuthContext } from "../contexts/AuthContext";
import { API_BASE_URL } from "../utils/api";

function UpgradeModal({ plan, currentPlan, onClose }) {
  const { user, checkAuth } = useContext(AuthContext);
  if (!plan || !currentPlan) return null;

  const [step, setStep] = useState("loading"); // "loading", "billing", "confirm", "processing", "success"
  const [billingDetails, setBillingDetails] = useState(null);
  const [paymentMethods, setPaymentMethods] = useState([]);
  const [formData, setFormData] = useState({
    billing_contact_name: "",
    billing_contact_email: "",
    country: "",
    city: "",
    postal_code: "",
    street_address: "",
    vat_number: "",
    payment_method: "strawbay_invoice"
  });
  const [formErrors, setFormErrors] = useState({});
  const [formLoading, setFormLoading] = useState(false);

  useEffect(() => {
    fetchPaymentMethods();
    fetchBillingDetails();
  }, [plan?.id]);

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

  const fetchBillingDetails = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/billing-details?_t=${Date.now()}`, {
        method: "GET",
        headers: { 
          "Content-Type": "application/json",
          "Cache-Control": "no-cache, no-store, must-revalidate",
          "Pragma": "no-cache",
          "Expires": "0"
        },
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        if (data.billing) {
          setBillingDetails(data.billing);
          setFormData(data.billing);
          setStep("confirm");
        } else {
          setStep("billing");
        }
      } else {
        setStep("billing");
      }
    } catch (err) {
      console.error("Error fetching billing details:", err);
      setStep("billing");
    }
  };

  const validateForm = () => {
    const errors = {};
    const requiredFields = ["billing_contact_name", "billing_contact_email", "country", "city", "postal_code", "street_address"];
    
    requiredFields.forEach(field => {
      if (!formData[field] || !formData[field].trim()) {
        errors[field] = "This field is required";
      }
    });

    if (formData.billing_contact_email && !formData.billing_contact_email.includes("@")) {
      errors.billing_contact_email = "Please enter a valid email";
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSaveBilling = async () => {
    if (!validateForm()) return;

    setFormLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/billing-details`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        const data = await response.json();
        setBillingDetails(data.billing);
        setStep("confirm");
      } else {
        const error = await response.json();
        alert("Error saving billing details: " + (error.error || "Unknown error"));
      }
    } catch (err) {
      console.error("Error saving billing details:", err);
      alert("Error saving billing details");
    } finally {
      setFormLoading(false);
    }
  };

  const handleUpgrade = async () => {
    setStep("processing");
    try {
      const response = await fetch(`${API_BASE_URL}/auth/change-plan`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          price_plan_key: plan.price_plan_key
        })
      });

      if (response.ok) {
        const data = await response.json();
        setStep("success");
        // Refresh user data in AuthContext and wait for it
        await checkAuth();
      } else {
        const error = await response.json();
        alert("Error: " + (error.error || "Failed to change plan"));
        onClose();
      }
    } catch (err) {
      console.error("Error changing plan:", err);
      alert("Error changing plan: " + err.message);
      onClose();
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0, 0, 0, 0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "1rem"
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "white",
          borderRadius: "8px",
          maxWidth: "500px",
          width: "100%",
          maxHeight: "85vh",
          overflow: "auto",
          padding: "2rem",
          boxShadow: "0 10px 40px rgba(0, 0, 0, 0.2)"
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {step === "loading" && (
          <div style={{ textAlign: "center", padding: "2rem 0" }}>
            <div style={{
              width: "40px",
              height: "40px",
              border: "4px solid #e8ecf1",
              borderTop: "4px solid #7265cf",
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
              margin: "0 auto 1rem",
            }}></div>
            <p style={{ color: "#666", margin: "0" }}>Loading billing details...</p>
            <style>{`
              @keyframes spin {
                to { transform: rotate(360deg); }
              }
            `}</style>
          </div>
        )}

        {step === "billing" && (
          <>
            <h2 style={{ margin: "0 0 1rem 0", color: "#333", fontSize: "1.5rem" }}>
              Billing Information Required
            </h2>
            <p style={{ color: "#666", marginBottom: "1.5rem", lineHeight: "1.6" }}>
              Before upgrading your plan, please provide your billing information.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div>
                <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "600", color: "#333", fontSize: "0.9rem" }}>
                  Contact Name *
                </label>
                <input
                  type="text"
                  value={formData.billing_contact_name}
                  onChange={(e) => setFormData({ ...formData, billing_contact_name: e.target.value })}
                  style={{
                    width: "100%",
                    padding: "0.75rem",
                    border: formErrors.billing_contact_name ? "1px solid #dc3545" : "1px solid #e8ecf1",
                    borderRadius: "6px",
                    fontSize: "0.9rem",
                    boxSizing: "border-box"
                  }}
                  placeholder="Full name"
                />
                {formErrors.billing_contact_name && <p style={{ color: "#dc3545", fontSize: "0.8rem", margin: "0.25rem 0 0" }}>{formErrors.billing_contact_name}</p>}
              </div>

              <div>
                <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "600", color: "#333", fontSize: "0.9rem" }}>
                  Email *
                </label>
                <input
                  type="email"
                  value={formData.billing_contact_email}
                  onChange={(e) => setFormData({ ...formData, billing_contact_email: e.target.value })}
                  style={{
                    width: "100%",
                    padding: "0.75rem",
                    border: formErrors.billing_contact_email ? "1px solid #dc3545" : "1px solid #e8ecf1",
                    borderRadius: "6px",
                    fontSize: "0.9rem",
                    boxSizing: "border-box"
                  }}
                  placeholder="Email address"
                />
                {formErrors.billing_contact_email && <p style={{ color: "#dc3545", fontSize: "0.8rem", margin: "0.25rem 0 0" }}>{formErrors.billing_contact_email}</p>}
              </div>

              <div>
                <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "600", color: "#333", fontSize: "0.9rem" }}>
                  Country *
                </label>
                <input
                  type="text"
                  value={formData.country}
                  onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                  style={{
                    width: "100%",
                    padding: "0.75rem",
                    border: formErrors.country ? "1px solid #dc3545" : "1px solid #e8ecf1",
                    borderRadius: "6px",
                    fontSize: "0.9rem",
                    boxSizing: "border-box"
                  }}
                  placeholder="Country"
                />
                {formErrors.country && <p style={{ color: "#dc3545", fontSize: "0.8rem", margin: "0.25rem 0 0" }}>{formErrors.country}</p>}
              </div>

              <div>
                <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "600", color: "#333", fontSize: "0.9rem" }}>
                  City *
                </label>
                <input
                  type="text"
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  style={{
                    width: "100%",
                    padding: "0.75rem",
                    border: formErrors.city ? "1px solid #dc3545" : "1px solid #e8ecf1",
                    borderRadius: "6px",
                    fontSize: "0.9rem",
                    boxSizing: "border-box"
                  }}
                  placeholder="City"
                />
                {formErrors.city && <p style={{ color: "#dc3545", fontSize: "0.8rem", margin: "0.25rem 0 0" }}>{formErrors.city}</p>}
              </div>

              <div>
                <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "600", color: "#333", fontSize: "0.9rem" }}>
                  Postal Code *
                </label>
                <input
                  type="text"
                  value={formData.postal_code}
                  onChange={(e) => setFormData({ ...formData, postal_code: e.target.value })}
                  style={{
                    width: "100%",
                    padding: "0.75rem",
                    border: formErrors.postal_code ? "1px solid #dc3545" : "1px solid #e8ecf1",
                    borderRadius: "6px",
                    fontSize: "0.9rem",
                    boxSizing: "border-box"
                  }}
                  placeholder="Postal code"
                />
                {formErrors.postal_code && <p style={{ color: "#dc3545", fontSize: "0.8rem", margin: "0.25rem 0 0" }}>{formErrors.postal_code}</p>}
              </div>

              <div>
                <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "600", color: "#333", fontSize: "0.9rem" }}>
                  Street Address *
                </label>
                <input
                  type="text"
                  value={formData.street_address}
                  onChange={(e) => setFormData({ ...formData, street_address: e.target.value })}
                  style={{
                    width: "100%",
                    padding: "0.75rem",
                    border: formErrors.street_address ? "1px solid #dc3545" : "1px solid #e8ecf1",
                    borderRadius: "6px",
                    fontSize: "0.9rem",
                    boxSizing: "border-box"
                  }}
                  placeholder="Street address"
                />
                {formErrors.street_address && <p style={{ color: "#dc3545", fontSize: "0.8rem", margin: "0.25rem 0 0" }}>{formErrors.street_address}</p>}
              </div>

              <div>
                <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "600", color: "#333", fontSize: "0.9rem" }}>
                  VAT Number
                </label>
                <input
                  type="text"
                  value={formData.vat_number || ""}
                  onChange={(e) => setFormData({ ...formData, vat_number: e.target.value })}
                  style={{
                    width: "100%",
                    padding: "0.75rem",
                    border: "1px solid #e8ecf1",
                    borderRadius: "6px",
                    fontSize: "0.9rem",
                    boxSizing: "border-box"
                  }}
                  placeholder="VAT number (optional)"
                />
              </div>

              <div>
                <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "600", color: "#333", fontSize: "0.9rem" }}>
                  Payment Method
                </label>
                <select
                  value={formData.payment_method}
                  onChange={(e) => setFormData({ ...formData, payment_method: e.target.value })}
                  style={{
                    width: "100%",
                    padding: "0.75rem",
                    border: "1px solid #e8ecf1",
                    borderRadius: "6px",
                    fontSize: "0.9rem",
                    boxSizing: "border-box",
                    backgroundColor: "#ffffff",
                    cursor: "pointer",
                    appearance: "none",
                    backgroundImage: "url(\"data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e\")",
                    backgroundRepeat: "no-repeat",
                    backgroundPosition: "right 0.75rem center",
                    backgroundSize: "20px",
                    paddingRight: "2.5rem"
                  }}
                >
                  {paymentMethods.map((method) => (
                    <option key={method.key} value={method.key} disabled={!method.enabled}>
                      {method.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div style={{ display: "flex", gap: "1rem", marginTop: "1.5rem" }}>
              <button
                onClick={onClose}
                style={{
                  flex: 1,
                  padding: "0.75rem",
                  background: "#f0f0f0",
                  color: "#333",
                  border: "none",
                  borderRadius: "6px",
                  fontSize: "0.9rem",
                  fontWeight: "600",
                  cursor: "pointer",
                  transition: "background-color 0.3s"
                }}
                onMouseEnter={(e) => (e.target.style.backgroundColor = "#e0e0e0")}
                onMouseLeave={(e) => (e.target.style.backgroundColor = "#f0f0f0")}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveBilling}
                disabled={formLoading}
                style={{
                  flex: 1,
                  padding: "0.75rem",
                  background: formLoading ? "#cccccc" : "#7265cf",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  fontSize: "0.9rem",
                  fontWeight: "600",
                  cursor: formLoading ? "not-allowed" : "pointer",
                  transition: "background-color 0.3s"
                }}
                onMouseEnter={(e) => {
                  if (!formLoading) e.target.style.backgroundColor = "#5e52a3";
                }}
                onMouseLeave={(e) => {
                  if (!formLoading) e.target.style.backgroundColor = "#7265cf";
                }}
              >
                {formLoading ? "Saving..." : "Save & Continue"}
              </button>
            </div>
          </>
        )}

        {step === "confirm" && (
          <>
            <h2 style={{ margin: "0 0 1rem 0", color: "#333", fontSize: "1.5rem" }}>
              Change Plan
            </h2>

            <div style={{
              background: "#f0f4ff",
              padding: "1rem",
              borderRadius: "6px",
              marginBottom: "1.5rem",
              border: "1px solid #e0e8ff"
            }}>
              <p style={{ margin: "0 0 0.5rem 0", color: "#999", fontSize: "0.85rem", textTransform: "uppercase" }}>
                Current Plan
              </p>
              <h3 style={{ margin: "0 0 0.5rem 0", color: "#333", fontSize: "1.1rem" }}>
                {currentPlan.plan_name}
              </h3>
              <p style={{ margin: "0", color: "#666", fontSize: "0.9rem" }}>
                €{(currentPlan.price_per_month / 100).toFixed(0)}/month
              </p>
            </div>

            <div style={{ textAlign: "center", margin: "1rem 0" }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#7265cf" strokeWidth="2" style={{ margin: "0 auto", display: "block" }}>
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </div>

            <div style={{
              background: "#f9fafb",
              padding: "1rem",
              borderRadius: "6px",
              marginBottom: "1.5rem",
              border: "1px solid #e8ecf1"
            }}>
              <p style={{ margin: "0 0 0.5rem 0", color: "#999", fontSize: "0.85rem", textTransform: "uppercase" }}>
                New Plan
              </p>
              <h3 style={{ margin: "0 0 0.5rem 0", color: "#333", fontSize: "1.1rem" }}>
                {plan.plan_name}
              </h3>
              <p style={{ margin: "0", color: "#666", fontSize: "0.9rem" }}>
                €{(plan.price_per_month / 100).toFixed(0)}/month
              </p>
            </div>

            <p style={{
              color: "#666",
              fontSize: "0.9rem",
              marginBottom: "1.5rem",
              lineHeight: "1.6"
            }}>
              Your plan will be upgraded immediately. The billing will be adjusted based on your current subscription period.
            </p>

            <div style={{ display: "flex", gap: "1rem" }}>
              <button
                onClick={() => setStep("billing")}
                style={{
                  flex: 1,
                  padding: "0.75rem",
                  background: "#f0f0f0",
                  color: "#333",
                  border: "none",
                  borderRadius: "6px",
                  fontSize: "0.9rem",
                  fontWeight: "600",
                  cursor: "pointer",
                  transition: "background-color 0.3s"
                }}
                onMouseEnter={(e) => (e.target.style.backgroundColor = "#e0e0e0")}
                onMouseLeave={(e) => (e.target.style.backgroundColor = "#f0f0f0")}
              >
                Edit Billing
              </button>
              <button
                onClick={handleUpgrade}
                style={{
                  flex: 1,
                  padding: "0.75rem",
                  background: "#7265cf",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  fontSize: "0.9rem",
                  fontWeight: "600",
                  cursor: "pointer",
                  transition: "background-color 0.3s"
                }}
                onMouseEnter={(e) => (e.target.style.backgroundColor = "#5e52a3")}
                onMouseLeave={(e) => (e.target.style.backgroundColor = "#7265cf")}
              >
                Confirm Plan
              </button>
            </div>
          </>
        )}

        {step === "processing" && (
          <div style={{ textAlign: "center", padding: "2rem 0" }}>
            <div style={{
              width: "40px",
              height: "40px",
              border: "4px solid #e8ecf1",
              borderTop: "4px solid #7265cf",
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
              margin: "0 auto 1rem",
            }}></div>
            <h3 style={{ margin: "0 0 0.5rem 0", color: "#333" }}>Processing Upgrade</h3>
            <p style={{ color: "#666", margin: "0", fontSize: "0.9rem" }}>
              Please wait while we process your upgrade...
            </p>
            <style>{`
              @keyframes spin {
                to { transform: rotate(360deg); }
              }
            `}</style>
          </div>
        )}

        {step === "success" && (
          <div style={{ textAlign: "center", padding: "2rem 0" }}>
            <div style={{
              width: "60px",
              height: "60px",
              background: "#4caf50",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 1.5rem",
            }}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </div>
            <h2 style={{ margin: "0 0 0.5rem 0", color: "#333", fontSize: "1.3rem" }}>
              Plan Updated Successfully
            </h2>
            <p style={{ color: "#666", margin: "0 0 1.5rem 0", fontSize: "0.95rem" }}>
              Your plan has been changed to <strong>{plan.plan_name}</strong>.<br/>
              A confirmation email has been sent to your billing contact.
            </p>
            <button
              onClick={onClose}
              style={{
                padding: "0.75rem 2rem",
                background: "#7265cf",
                color: "white",
                border: "none",
                borderRadius: "6px",
                fontSize: "0.9rem",
                fontWeight: "600",
                cursor: "pointer",
                transition: "background-color 0.3s"
              }}
              onMouseEnter={(e) => (e.target.style.backgroundColor = "#5e52a3")}
              onMouseLeave={(e) => (e.target.style.backgroundColor = "#7265cf")}
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default UpgradeModal;
