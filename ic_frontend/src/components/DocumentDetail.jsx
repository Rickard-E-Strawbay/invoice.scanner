import React, { useState, useEffect } from "react";
import { API_BASE_URL } from "../utils/api";

function DocumentDetail({ document, peppolSections = {}, onClose, onSave }) {
  // Get sections order from sessionStorage (set by Dashboard)
  const sectionsOrder = JSON.parse(sessionStorage.getItem("peppol_sections_order") || "[]");
  
  const [invoiceData, setInvoiceData] = useState({
    document_name: "",
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [showPreview, setShowPreview] = useState(true);
  const [showForm, setShowForm] = useState(true);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [expandedSections, setExpandedSections] = useState({});
  const [showNonMandatory, setShowNonMandatory] = useState(false);

  const toggleSection = (sectionName) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionName]: !prev[sectionName]
    }));
  };

  const togglePreview = () => {
    if (showPreview) {
      // Trying to collapse preview
      if (!showForm) {
        // Form is already collapsed, so expand it
        setShowForm(true);
      }
      setShowPreview(false);
    } else {
      setShowPreview(true);
    }
  };

  const toggleForm = () => {
    if (showForm) {
      // Trying to collapse form
      if (!showPreview) {
        // Preview is already collapsed, so expand it
        setShowPreview(true);
      }
      setShowForm(false);
    } else {
      setShowForm(true);
    }
  };

  // Initialize invoice data and preview from document
  useEffect(() => {
    if (document) {
      const newInvoiceData = {
        document_name: document.document_name || "",
      };
      
      // If invoice_data_peppol_final exists, populate fields from it
      if (document.invoice_data_peppol_final) {
        let peppol_final = document.invoice_data_peppol_final;
        
        // Parse if it's a JSON string
        if (typeof peppol_final === 'string') {
          try {
            peppol_final = JSON.parse(peppol_final);
          } catch (e) {
            console.warn('Failed to parse invoice_data_peppol_final:', e);
            peppol_final = {};
          }
        }
        
        // Flatten the PEPPOL structure and populate fields
        Object.entries(peppol_final).forEach(([sectionName, sectionFields]) => {
          if (typeof sectionFields === 'object' && sectionFields !== null) {
            Object.entries(sectionFields).forEach(([fieldName, fieldValue]) => {
              newInvoiceData[fieldName] = fieldValue;
            });
          }
        });
      }
      
      setInvoiceData(newInvoiceData);

      // Set preview URL directly - no need to fetch and convert
      // Browser will fetch it automatically with credentials
      setPreviewUrl(`${API_BASE_URL}/documents/${document.id}/preview`);
      setPreviewLoading(false);
    }
  }, [document]);
  
  // Initialize PEPPOL fields in state when they're available
  useEffect(() => {
    if (Object.keys(peppolSections).length > 0) {
      setInvoiceData(prev => {
        const updated = { ...prev };
        // Iterate through sections and fields
        Object.entries(peppolSections).forEach(([sectionName, fieldsInSection]) => {
          Object.keys(fieldsInSection).forEach(fieldName => {
            if (!(fieldName in updated)) {
              updated[fieldName] = "";
            }
          });
        });
        return updated;
      });
    }
  }, [peppolSections]);

  const handleFieldChange = (field, value) => {
    setInvoiceData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSave = async () => {
    setIsLoading(true);
    setError(null);
    setSuccess(false);

    try {
      // Build PEPPOL structure organized by sections
      const peppol_final = {};
      
      Object.entries(peppolSections).forEach(([sectionName, fieldsInSection]) => {
        const sectionData = {};
        let hasData = false;
        
        Object.keys(fieldsInSection).forEach(fieldName => {
          if (invoiceData[fieldName]) {
            sectionData[fieldName] = invoiceData[fieldName];
            hasData = true;
          }
        });
        
        // Only add section if it has data
        if (hasData) {
          peppol_final[sectionName] = sectionData;
        }
      });
      
      // Also save document_name
      const body = {
        document_name: invoiceData.document_name,
        invoice_data_peppol_final: peppol_final
      };
      
      const response = await fetch(`${API_BASE_URL}/documents/${document.id}`, {
        method: "PUT",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to save document");
      }

      setSuccess(true);
      if (onSave) {
        onSave();
      }
      
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (err) {
      console.error("Error saving document:", err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <style>{`
        .info-icon {
          position: relative;
          cursor: help;
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
          pointer-events: auto;
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
    <div style={{
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
    }}>
      <div style={{
        background: "white",
        borderRadius: isMaximized ? "0" : "8px",
        width: isMaximized ? "100%" : "90%",
        maxWidth: isMaximized ? "100%" : "900px",
        maxHeight: isMaximized ? "100%" : "90vh",
        display: "flex",
        flexDirection: "column",
        boxShadow: isMaximized ? "none" : "0 20px 25px -5px rgba(0, 0, 0, 0.1)",
        position: "relative",
      }}>
        {/* Header */}
        <div style={{
          padding: "1.5rem",
          borderBottom: "1px solid #e8ecf1",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "#f9fafb",
          flexShrink: 0,
        }}>
          <div>
            <h2 style={{ margin: 0, fontSize: "1.25rem", color: "#1a1a1a" }}>
              {invoiceData.document_name || document.raw_filename}
            </h2>
            <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.85rem", color: "#666" }}>
              Uploaded {new Date(document.created_at).toLocaleDateString("sv-SE")}
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              onClick={() => setIsMaximized(!isMaximized)}
              style={{
                background: "none",
                border: "none",
                borderRadius: "4px",
                fontSize: "1rem",
                cursor: "pointer",
                color: "#666",
                padding: "0.5rem 0.75rem",
                transition: "all 0.2s ease",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              onMouseEnter={(e) => {
                e.target.style.opacity = "0.7";
              }}
              onMouseLeave={(e) => {
                e.target.style.opacity = "1";
              }}
              title={isMaximized ? "Exit fullscreen" : "Maximize"}
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                {isMaximized ? (
                  <>
                    <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
                  </>
                ) : (
                  <>
                    <path d="M14 3h7a1 1 0 0 1 1 1v7" />
                    <path d="M3 14v7a1 1 0 0 0 1 1h7" />
                    <path d="M6 9h12v8H6z" />
                    <path d="M9 14v4h6v-6" />
                  </>
                )}
              </svg>
            </button>
            <button
              onClick={onClose}
              style={{
                background: "none",
                border: "none",
                fontSize: "1.5rem",
                cursor: "pointer",
                color: "#666",
              }}
            >
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <div style={{
          display: "grid",
          gridTemplateColumns: isMaximized 
            ? `${showPreview ? "3fr" : "0px"} ${showForm ? "1fr" : "0px"}` 
            : `${showPreview ? "1fr" : "0px"} ${showForm ? "1fr" : "0px"}`,
          gap: "2rem",
          padding: "2rem",
          overflow: "hidden",
          flex: 1,
        }}>
          {/* Preview Panel */}
          <div style={{
            display: "flex",
            flexDirection: "column",
            overflow: "auto",
            transition: "all 0.3s ease",
            minWidth: 0,
          }}>
            <div style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1rem",
              position: "sticky",
              top: 0,
              background: "inherit",
              paddingBottom: "1rem",
              borderBottom: "1px solid #e8ecf1",
              zIndex: 10,
            }}>
              <h3 style={{ margin: 0, color: "#1a1a1a" }}>Document Preview</h3>
              <button
                onClick={togglePreview}
                style={{
                  padding: "0.4rem 0.5rem",
                  background: "none",
                  border: "1px solid #d0d0d0",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "1.2rem",
                  color: "#7265cf",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "32px",
                  height: "32px",
                  transition: "all 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.target.style.background = "#f5f5f5";
                  e.target.style.borderColor = "#999";
                }}
                onMouseLeave={(e) => {
                  e.target.style.background = "none";
                  e.target.style.borderColor = "#d0d0d0";
                }}
                title="Hide preview"
              >
                ◀
              </button>
            </div>
            <div style={{
              background: "#f5f7fa",
              borderRadius: "6px",
              padding: "1rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#999",
              overflow: "auto",
              flex: 1,
            }}>
              {document.raw_filename?.toLowerCase().endsWith('.pdf') ? (
                <iframe 
                  src={`${API_BASE_URL}/documents/${document.id}/preview`}
                  title="Document preview" 
                  style={{
                    width: "100%",
                    height: "100%",
                    border: "none",
                    borderRadius: "4px",
                  }}
                />
              ) : (
                <img 
                  src={`${API_BASE_URL}/documents/${document.id}/preview`}
                  alt="Document preview" 
                  style={{
                    maxWidth: "100%",
                    maxHeight: "100%",
                    objectFit: "contain",
                  }}
                />
              )}
            </div>
          </div>

          {/* Form */}
          <div style={{
            display: "flex",
            flexDirection: "column",
            overflow: "auto",
            minWidth: 0,
          }}>
            <div style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1rem",
              position: "sticky",
              top: 0,
              background: "white",
              paddingBottom: "1rem",
              borderBottom: "1px solid #e8ecf1",
              zIndex: 10,
            }}>
              <h3 style={{ margin: 0, color: "#1a1a1a" }}>Invoice Details</h3>
              <button
                onClick={toggleForm}
                style={{
                  padding: "0.4rem 0.5rem",
                  background: "none",
                  border: "1px solid #d0d0d0",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "1.2rem",
                  color: "#7265cf",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "32px",
                  height: "32px",
                  transition: "all 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.target.style.background = "#f5f5f5";
                  e.target.style.borderColor = "#999";
                }}
                onMouseLeave={(e) => {
                  e.target.style.background = "none";
                  e.target.style.borderColor = "#d0d0d0";
                }}
                title="Hide details"
              >
                ▶
              </button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem", height: "100%", minHeight: 0 }}>
              <div style={{ flexShrink: 0 }}>
                <label style={{ display: "block", fontWeight: "500", marginBottom: "0.5rem" }}>
                  Document Name
                </label>
                <input
                  type="text"
                  value={invoiceData.document_name}
                  onChange={(e) => handleFieldChange("document_name", e.target.value)}
                  onBlur={(e) => {
                    // If field is empty on blur, fill with raw_filename without extension
                    if (!e.target.value.trim()) {
                      const nameWithoutExt = document.raw_filename.split('.').slice(0, -1).join('.');
                      handleFieldChange("document_name", nameWithoutExt);
                    }
                  }}
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    border: "1px solid #ddd",
                    borderRadius: "4px",
                    fontSize: "0.9rem",
                    boxSizing: "border-box"
                  }}
                />
              </div>
              
              {/* PEPPOL Sections - Scrollable Container */}
              {Object.keys(peppolSections).length > 0 && (
                <div style={{ 
                  marginTop: "0.5rem",
                  display: "flex",
                  flexDirection: "column",
                  minHeight: 0,
                  flex: 1
                }}>
                  <div style={{ marginBottom: "1rem", flexShrink: 0 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                      <p style={{ margin: 0, fontSize: "0.85rem", color: "#666", fontWeight: "500" }}>
                        Invoice Sections ({
                          sectionsOrder.filter(sectionName => {
                            const fieldsInSection = peppolSections[sectionName] || {};
                            const filteredFields = Object.entries(fieldsInSection)
                              .filter(([fieldName, fieldInfo]) => {
                                if (fieldInfo.Obligation === "required") return true;
                                if (showNonMandatory) return true;
                                return invoiceData[fieldName]; // Show if has value
                              })
                              .reduce((acc, [fieldName, fieldInfo]) => {
                                acc[fieldName] = fieldInfo;
                                return acc;
                              }, {});
                            return Object.keys(filteredFields).length > 0;
                          }).length
                        })
                      </p>
                      <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem", cursor: "pointer" }}>
                        <input
                          type="checkbox"
                          checked={showNonMandatory}
                          onChange={(e) => {
                            console.log("Checkbox clicked! New value:", e.target.checked);
                            setShowNonMandatory(e.target.checked);
                          }}
                          style={{ cursor: "pointer" }}
                        />
                        <span style={{ color: "#666" }}>Show Non-Mandatory</span>
                      </label>
                    </div>
                  </div>

                  <div style={{ 
                    overflowY: "auto",
                    paddingRight: "0.5rem",
                    flex: 1,
                    minHeight: 0
                  }}>
                    {sectionsOrder.map((sectionName) => {
                      const fieldsInSection = peppolSections[sectionName] || {};
                      
                      // Filter fields: mandatory + filled + (all if showNonMandatory)
                      const filteredFields = Object.entries(fieldsInSection)
                        .filter(([fieldName, fieldInfo]) => {
                          if (fieldInfo.Obligation === "required") return true;
                          if (showNonMandatory) return true;
                          return invoiceData[fieldName]; // Show if has value
                        })
                        .reduce((acc, [fieldName, fieldInfo]) => {
                          acc[fieldName] = fieldInfo;
                          return acc;
                        }, {});
                      
                      // Hide section if no fields after filtering
                      if (Object.keys(filteredFields).length === 0) return null;
                      
                      const hasFields = Object.keys(filteredFields).length > 0;
                      return (
                      <div key={sectionName}>
                        <button
                          onClick={() => toggleSection(sectionName)}
                          style={{
                            width: "100%",
                            padding: "0.75rem 1rem",
                            background: expandedSections[sectionName] ? "#f3f4f6" : "#ffffff",
                            border: "1px solid #e5e7eb",
                            borderRadius: "4px",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "0.75rem",
                            fontSize: "0.9rem",
                            fontWeight: "500",
                            color: "#1f2937",
                            marginBottom: "0.5rem",
                            transition: "all 0.2s ease",
                          }}
                          onMouseEnter={(e) => {
                            e.target.style.background = expandedSections[sectionName] ? "#f3f4f6" : "#f9fafb";
                            e.target.style.borderColor = "#9ca3af";
                          }}
                          onMouseLeave={(e) => {
                            e.target.style.background = expandedSections[sectionName] ? "#f3f4f6" : "#ffffff";
                            e.target.style.borderColor = "#e5e7eb";
                          }}
                        >
                          <span style={{ display: "inline-block", transform: expandedSections[sectionName] ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.2s", width: "14px" }}>
                            ▶
                          </span>
                          <span>{sectionName}</span>
                          <span style={{ marginLeft: "auto", fontSize: "0.8rem", color: "#9ca3af" }}>
                            ({Object.keys(filteredFields).length})
                          </span>
                        </button>
                        
                        {expandedSections[sectionName] && (
                          <div style={{ 
                            padding: "1rem", 
                            background: "#f9fafb",
                            borderRadius: "0 0 6px 6px",
                            border: "1px solid #e5e7eb",
                            borderTop: "none",
                            marginBottom: "0.5rem"
                          }}>
                            {hasFields ? (
                              <div style={{ 
                                display: "grid", 
                                gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", 
                                gap: "1rem"
                              }}>
                              {Object.entries(filteredFields)
                                .map(([fieldName, fieldInfo]) => (
                                <div key={fieldName}>
                                  <label 
                                    style={{ 
                                      display: "flex",
                                      alignItems: "center",
                                      gap: "0.5rem",
                                      fontWeight: "500", 
                                      marginBottom: "0.5rem",
                                      color: "#374151",
                                      cursor: "help",
                              }}
                            >
                              <div
                                className="info-icon"
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  justifyContent: "center",
                                  width: "18px",
                                  height: "18px",
                                  borderRadius: "50%",
                                  border: "1px solid #9ca3af",
                                  fontSize: "0.75rem",
                                  color: "#9ca3af",
                                  fontWeight: "600",
                                  cursor: "pointer",
                                }}
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
                                  <a 
                                    href={`https://docs.peppol.eu/poacc/billing/3.0/#${fieldInfo["BT-ID"]}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{
                                      color: "#60a5fa",
                                      textDecoration: "none",
                                      fontWeight: "600",
                                      cursor: "pointer",
                                    }}
                                    onMouseEnter={(e) => e.target.style.textDecoration = "underline"}
                                    onMouseLeave={(e) => e.target.style.textDecoration = "none"}
                                  >
                                    {fieldInfo["BT-ID"]} ↗
                                  </a>
                                  <div style={{ marginTop: "0.5rem", fontSize: "0.8rem", color: "#e5e7eb" }}>
                                    {fieldInfo["Description"]}
                                  </div>
                                </div>
                              </div>
                              <span style={{ borderBottom: "1px dotted #9ca3af" }}>
                                {fieldName}
                              </span>
                            </label>
                            <input
                              type="text"
                              value={invoiceData[fieldName] || ""}
                              onChange={(e) => handleFieldChange(fieldName, e.target.value)}
                              placeholder={fieldInfo["Example"] || `Enter ${fieldName}`}
                              title={fieldInfo["Description"]}
                              style={{
                                width: "100%",
                                padding: "0.75rem",
                                border: fieldInfo.Obligation === "required" ? "2px solid #6b7280" : "1px solid #d0d0d0",
                                borderRadius: "6px",
                                fontSize: "0.95rem",
                                boxSizing: "border-box",
                              }}
                            />
                          </div>
                        ))}
                              </div>
                            ) : (
                              <p style={{ margin: 0, color: "#9ca3af", fontSize: "0.9rem" }}>
                                No mandatory fields in this section.
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                      );
                    })}
                    </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Collapsed Preview Tab */}
        {!showPreview && (
        <div style={{
          position: "absolute",
          left: 0,
          top: "110px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "white",
          border: "1px solid #d0d0d0",
          borderRadius: "0 6px 6px 0",
          cursor: "pointer",
          transition: "all 0.2s ease",
          paddingBottom: "1rem",
          paddingTop: "1rem",
          paddingLeft: "0.5rem",
          paddingRight: "0.5rem",
          height: "auto",
          zIndex: 20,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "#f5f5f5";
          e.currentTarget.style.borderColor = "#999";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "white";
          e.currentTarget.style.borderColor = "#d0d0d0";
        }}
        onClick={togglePreview}
        title="Show preview"
        >
          <div style={{
            writingMode: "vertical-lr",
            textOrientation: "mixed",
            color: "#7265cf",
            fontSize: "0.8rem",
            fontWeight: "700",
            marginBottom: "0.8rem",
            letterSpacing: "0.5px",
          }}>
            PREVIEW
          </div>
          <div style={{
            fontSize: "1.8rem",
            color: "#7265cf",
            fontWeight: "bold",
            transition: "transform 0.2s ease",
          }}>
            ▶
          </div>
        </div>
        )}

        {/* Collapsed Form Tab */}
        {!showForm && (
        <div style={{
          position: "absolute",
          right: 0,
          top: "110px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "white",
          border: "1px solid #d0d0d0",
          borderRadius: "6px 0 0 6px",
          cursor: "pointer",
          transition: "all 0.2s ease",
          paddingBottom: "1rem",
          paddingTop: "1rem",
          paddingLeft: "0.5rem",
          paddingRight: "0.5rem",
          height: "auto",
          zIndex: 20,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "#f5f5f5";
          e.currentTarget.style.borderColor = "#999";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "white";
          e.currentTarget.style.borderColor = "#d0d0d0";
        }}
        onClick={toggleForm}
        title="Show form"
        >
          <div style={{
            writingMode: "vertical-rl",
            textOrientation: "mixed",
            color: "#7265cf",
            fontSize: "0.8rem",
            fontWeight: "700",
            marginBottom: "0.8rem",
            letterSpacing: "0.5px",
          }}>
            DETAILS
          </div>
          <div style={{
            fontSize: "1.8rem",
            color: "#7265cf",
            fontWeight: "bold",
            transition: "transform 0.2s ease",
          }}>
            ◀
          </div>
        </div>
        )}

        {/* Error/Success Messages */}
        {error && (
          <div style={{
            margin: "0 2rem",
            padding: "1rem",
            background: "#fee",
            borderRadius: "6px",
            borderLeft: "4px solid #ef4444",
            color: "#991b1b",
          }}>
            Error: {error}
          </div>
        )}

        {success && (
          <div style={{
            margin: "0 2rem",
            padding: "1rem",
            background: "#f0fdf4",
            borderRadius: "6px",
            borderLeft: "4px solid #10b981",
            color: "#166534",
          }}>
            ✓ Document saved successfully!
          </div>
        )}

        {/* Footer Actions */}
        <div style={{
          padding: "1.5rem 2rem",
          borderTop: "1px solid #e8ecf1",
          display: "flex",
          gap: "1rem",
          justifyContent: "flex-end",
          background: "#f9fafb",
          flexShrink: 0,
        }}>
          <button
            onClick={onClose}
            disabled={isLoading}
            style={{
              padding: "0.75rem 1.5rem",
              background: "white",
              color: "#1a1a1a",
              border: "1px solid #d0d0d0",
              borderRadius: "6px",
              cursor: "pointer",
              fontWeight: "600",
              opacity: isLoading ? 0.6 : 1,
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isLoading}
            style={{
              padding: "0.75rem 1.5rem",
              background: "#7265cf",
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: isLoading ? "not-allowed" : "pointer",
              fontWeight: "600",
              opacity: isLoading ? 0.7 : 1,
            }}
          >
            {isLoading ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
    </>
  );
}

export default DocumentDetail;
