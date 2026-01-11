import React, { useState, useContext, useEffect } from "react";
import { AuthContext } from "../contexts/AuthContext";
import FeatureModal from "./FeatureModal";
import UpgradeModal from "./UpgradeModal";
import "./Dashboard.css";
import { API_BASE_URL } from "../utils/api";

function PlansAndBilling({ onNavigate }) {
  const { user, isAdmin } = useContext(AuthContext);
  const [plans, setPlans] = useState([]);
  const [currentPlan, setCurrentPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [features, setFeatures] = useState([]);
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [hoveredFeature, setHoveredFeature] = useState(null); // Format: "planId-featureKey"
  const [upgradeModalPlan, setUpgradeModalPlan] = useState(null);
  const [billingData, setBillingData] = useState(null);
  const [billingLoading, setBillingLoading] = useState(true);

  // All available features - built dynamically from backend features
  const allFeatures = features.map(f => ({
    key: f.feature_key,
    name: f.feature_name
  }));

  // DEBUG: Log to verify features data
  useEffect(() => {
    console.log("DEBUG PlansAndBilling - features from API:", features);
    console.log("DEBUG PlansAndBilling - allFeatures array:", allFeatures);
    console.log("DEBUG PlansAndBilling - plans from API:", plans);
    if (plans.length > 0) {
      console.log("DEBUG PlansAndBilling - first plan features object:", plans[0].features);
    }
  }, [features, allFeatures, plans]);

  useEffect(() => {
    fetchPlans();
    fetchFeatures();
    fetchBillingData();
  }, []);

  const fetchFeatures = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/live/features`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        setFeatures(data.features || []);
      }
    } catch (err) {
      console.error("Error fetching features:", err);
    }
  };

  const fetchBillingData = async () => {
    try {
      setBillingLoading(true);
      const response = await fetch(`${API_BASE_URL}/live/billing-details`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        setBillingData(data.billing || null);
      }
    } catch (err) {
      console.error("Error fetching billing data:", err);
    } finally {
      setBillingLoading(false);
    }
  };

  const getFeatureDetails = (featureKey) => {
    return features.find(f => f.feature_key === featureKey);
  };

  const fetchPlans = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/live/plans`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Failed to fetch plans");
      }

      const data = await response.json();
      setPlans(data.plans || []);
      setCurrentPlan(data.current_plan_key || null);
    } catch (err) {
      console.error("Error fetching plans:", err);
      setError("Failed to load plans");
    } finally {
      setLoading(false);
    }
  };

  const isFeatureIncluded = (plan, featureKey) => {
    if (!plan.features) return false;
    return plan.features[featureKey] === true;
  };

  if (loading) {
    return <div className="admin-section"><p>Loading plans...</p></div>;
  }

  return (
    <div className="admin-section">
      <div style={{ padding: "2rem", background: "#ffffff", borderRadius: "8px", border: "1px solid #e8ecf1" }}>
        <div style={{ marginBottom: "2rem" }}>
          <h2>Plans and Billing</h2>
          <p style={{ color: "#666", marginBottom: "1rem" }}>
            {user?.company_name} - Current Plan
          </p>
          {error && (
            <div style={{
              background: "#fee",
              color: "#c33",
              padding: "1rem",
              borderRadius: "4px",
              marginBottom: "1rem",
            }}>
              {error}
            </div>
          )}
        </div>

        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "1.5rem",
          marginTop: "2rem"
        }}>
          {plans.filter(plan => plan.price_plan_key !== 1000).map((plan) => {
            const isCurrentPlan = plan.price_plan_key === currentPlan;
            return (
              <div
                key={plan.id}
                style={{
                  border: isCurrentPlan ? "2px solid #7265cf" : "1px solid #e8ecf1",
                  borderRadius: "8px",
                  padding: "1.5rem",
                  background: isCurrentPlan ? "#f0f4ff" : "#ffffff",
                  position: "relative",
                  transition: "all 0.3s ease",
                  boxShadow: isCurrentPlan ? "0 4px 12px rgba(124, 58, 237, 0.15)" : "none",
                }}
              >
                {isCurrentPlan && (
                  <div style={{
                    position: "absolute",
                    top: "-12px",
                    left: "50%",
                    transform: "translateX(-50%)",
                    background: "#7265cf",
                    color: "white",
                    padding: "0.25rem 1rem",
                    borderRadius: "20px",
                    fontSize: "0.75rem",
                    fontWeight: "600",
                    textTransform: "uppercase",
                  }}>
                    Current Plan
                  </div>
                )}

                <h3 style={{
                  margin: "0 0 0.5rem 0",
                  color: isCurrentPlan ? "#7265cf" : "#333",
                  fontSize: "1.25rem",
                  fontWeight: "600"
                }}>
                  {plan.plan_name}
                </h3>

                <p style={{
                  color: "#666",
                  fontSize: "0.9rem",
                  margin: "0 0 1rem 0",
                  minHeight: "2rem"
                }}>
                  {plan.plan_description}
                </p>

                <div style={{
                  margin: "1rem 0",
                  paddingTop: "1rem",
                  borderTop: "1px solid #e8ecf1"
                }}>
                  <h4 style={{ margin: "0 0 0.75rem 0", fontSize: "0.85rem", fontWeight: "600", color: "#333", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                    Features
                  </h4>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    {allFeatures.map((feature) => {
                      const isIncluded = isFeatureIncluded(plan, feature.key);
                      const featureDetails = getFeatureDetails(feature.key);
                      const hoverKey = `${plan.id}-${feature.key}`;
                      const isHovered = hoveredFeature === hoverKey;

                      return (
                        <div key={feature.key} style={{ position: "relative" }}>
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "0.5rem",
                              fontSize: "0.85rem",
                              cursor: featureDetails ? "pointer" : "default",
                              padding: "0.25rem",
                              borderRadius: "4px",
                              transition: "background-color 0.2s",
                              background: isHovered && featureDetails ? "#f5f5f5" : "transparent"
                            }}
                            onMouseEnter={() => featureDetails && setHoveredFeature(hoverKey)}
                            onMouseLeave={() => setHoveredFeature(null)}
                            onClick={() => featureDetails && setSelectedFeature(featureDetails)}
                          >
                            <span style={{
                              display: "inline-flex",
                              alignItems: "center",
                              justifyContent: "center",
                              width: "18px",
                              height: "18px",
                              borderRadius: "3px",
                              background: isIncluded ? "#7265cf" : "#e8ecf1",
                              color: isIncluded ? "white" : "#999",
                              fontSize: "0.7rem",
                              fontWeight: "700",
                              flexShrink: 0
                            }}>
                              {isIncluded ? "✓" : "—"}
                            </span>
                            <span style={{ color: isIncluded ? "#333" : "#999", textDecoration: featureDetails ? "underline dotted #7265cf" : "none" }}>
                              {feature.name}
                            </span>
                          </div>

                          {isHovered && featureDetails && (
                            <div
                              style={{
                                position: "absolute",
                                bottom: "100%",
                                left: "0",
                                background: "#333",
                                color: "white",
                                padding: "0.5rem 0.75rem",
                                borderRadius: "4px",
                                fontSize: "0.75rem",
                                marginBottom: "0.5rem",
                                maxWidth: "200px",
                                zIndex: 100,
                                boxShadow: "0 2px 8px rgba(0, 0, 0, 0.15)",
                                whiteSpace: "normal",
                                lineHeight: "1.4"
                              }}
                            >
                              {featureDetails.feature_short_description}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div style={{
                  margin: "1.5rem 0",
                  paddingTop: "1.5rem",
                  borderTop: "1px solid #e8ecf1"
                }}>
                  <div style={{
                    fontSize: "2rem",
                    fontWeight: "700",
                    color: isCurrentPlan ? "#7265cf" : "#333",
                    marginBottom: "0.25rem"
                  }}>
                    {plan.price_per_month === 0 ? (
                      "Free"
                    ) : (
                      <>
                        €{(plan.price_per_month / 100).toFixed(0)}
                        <span style={{ fontSize: "0.8rem", color: "#999", fontWeight: "400" }}>/month</span>
                      </>
                    )}
                  </div>
                </div>

                {isCurrentPlan ? (
                  <button
                    disabled
                    style={{
                      width: "100%",
                      padding: "0.75rem",
                      background: "#e8ecf1",
                      color: "#666",
                      border: "none",
                      borderRadius: "6px",
                      fontSize: "0.9rem",
                      fontWeight: "600",
                      cursor: "not-allowed",
                      marginTop: "1rem"
                    }}
                  >
                    Current Plan
                  </button>
                ) : (
                  <button
                    disabled={!isAdmin()}
                    style={{
                      width: "100%",
                      padding: "0.75rem",
                      background: isAdmin() ? "#7265cf" : "#e8ecf1",
                      color: isAdmin() ? "white" : "#999",
                      border: "none",
                      borderRadius: "6px",
                      fontSize: "0.9rem",
                      fontWeight: "600",
                      cursor: isAdmin() ? "pointer" : "not-allowed",
                      marginTop: "1rem",
                      transition: "background-color 0.3s"
                    }}
                    onMouseEnter={(e) => {
                      if (isAdmin()) {
                        e.target.style.backgroundColor = "#5e52a3";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (isAdmin()) {
                        e.target.style.backgroundColor = "#7265cf";
                      }
                    }}
                    onClick={() => {
                      if (isAdmin()) {
                        setUpgradeModalPlan(plan);
                      }
                    }}
                    title={!isAdmin() ? "Only Admins can upgrade plans" : ""}
                  >
                    {isAdmin() ? `Switch to ${plan.plan_name}` : "Admin Only"}
                  </button>
                )}
              </div>
            );
          })}
        </div>

        <div style={{
          marginTop: "2rem",
          padding: "1.5rem",
          background: "#f9f9f9",
          borderRadius: "8px",
          border: "1px solid #e8ecf1"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
            <div>
              <h3 style={{ margin: "0 0 1rem 0" }}>Billing Information</h3>
            </div>
            <button
              disabled={!isAdmin()}
              onClick={() => onNavigate && onNavigate("settings", "company")}
              style={{
                padding: "0.5rem 1rem",
                background: isAdmin() ? "#7265cf" : "#e8ecf1",
                color: isAdmin() ? "white" : "#999",
                border: "none",
                borderRadius: "6px",
                fontSize: "0.85rem",
                fontWeight: "600",
                cursor: isAdmin() ? "pointer" : "not-allowed",
                transition: "background-color 0.3s"
              }}
              onMouseEnter={(e) => {
                if (isAdmin()) e.target.style.backgroundColor = "#5e52a3";
              }}
              onMouseLeave={(e) => {
                if (isAdmin()) e.target.style.backgroundColor = "#7265cf";
              }}
              title={!isAdmin() ? "Only Company Admins can edit billing information" : "Edit billing information"}
            >
              Edit Billing
            </button>
          </div>

          {billingLoading ? (
            <p style={{ color: "#999" }}>Loading billing information...</p>
          ) : billingData ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
              <div>
                <p style={{ color: "#999", fontSize: "0.85rem", marginBottom: "0.25rem" }}>Contact Name</p>
                <p style={{ color: "#333", fontWeight: "500" }}>{billingData.billing_contact_name || "-"}</p>
              </div>
              <div>
                <p style={{ color: "#999", fontSize: "0.85rem", marginBottom: "0.25rem" }}>Contact Email</p>
                <p style={{ color: "#333", fontWeight: "500" }}>{billingData.billing_contact_email || "-"}</p>
              </div>
              <div>
                <p style={{ color: "#999", fontSize: "0.85rem", marginBottom: "0.25rem" }}>Address</p>
                <p style={{ color: "#333", fontWeight: "500" }}>{billingData.street_address || "-"}</p>
              </div>
              <div>
                <p style={{ color: "#999", fontSize: "0.85rem", marginBottom: "0.25rem" }}>City</p>
                <p style={{ color: "#333", fontWeight: "500" }}>{billingData.city || "-"}</p>
              </div>
              <div>
                <p style={{ color: "#999", fontSize: "0.85rem", marginBottom: "0.25rem" }}>Postal Code</p>
                <p style={{ color: "#333", fontWeight: "500" }}>{billingData.postal_code || "-"}</p>
              </div>
              <div>
                <p style={{ color: "#999", fontSize: "0.85rem", marginBottom: "0.25rem" }}>Country</p>
                <p style={{ color: "#333", fontWeight: "500" }}>{billingData.country || "-"}</p>
              </div>
              <div>
                <p style={{ color: "#999", fontSize: "0.85rem", marginBottom: "0.25rem" }}>VAT Number</p>
                <p style={{ color: "#333", fontWeight: "500" }}>{billingData.vat_number || "-"}</p>
              </div>
              <div>
                <p style={{ color: "#999", fontSize: "0.85rem", marginBottom: "0.25rem" }}>Payment Method</p>
                <p style={{ color: "#333", fontWeight: "500" }}>{billingData.payment_method || "-"}</p>
              </div>
            </div>
          ) : (
            <p style={{ color: "#666" }}>
              No billing information on file.{isAdmin() && " Click \"Edit Billing\" to add it."}
            </p>
          )}

          <p style={{ color: "#666", marginTop: "1.5rem", fontSize: "0.9rem" }}>
            <strong>Company:</strong> {user?.company_name}
          </p>
          <p style={{ color: "#666", fontSize: "0.9rem" }}>
            <strong>Organization ID:</strong> {user?.organization_id}
          </p>
        </div>
      </div>

      <FeatureModal feature={selectedFeature} onClose={() => setSelectedFeature(null)} />
      <UpgradeModal 
        plan={upgradeModalPlan}
        currentPlan={plans.find(p => p.price_plan_key === currentPlan)}
        onClose={() => setUpgradeModalPlan(null)}
      />
    </div>
  );
}

export default PlansAndBilling;
