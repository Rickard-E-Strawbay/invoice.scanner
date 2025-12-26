import React, { useState, useEffect } from "react";
import { API_BASE_URL } from "../utils/api";

function DocumentDetail({ document, onClose, onSave }) {
  const [invoiceData, setInvoiceData] = useState({
    document_name: "",
    invoice_number: "",
    invoice_date: "",
    vendor_name: "",
    amount: "",
    vat: "",
    total: "",
    due_date: "",
    reference: "",
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [showPreview, setShowPreview] = useState(true);
  const [showForm, setShowForm] = useState(true);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);

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
      setInvoiceData(prev => ({
        ...prev,
        document_name: document.document_name || "",
      }));

      // Load preview if status allows it
      const allowedStatuses = ["uploaded", "preprocessing", "preprocess_error"];
      if (allowedStatuses.includes(document.status)) {
        setPreviewLoading(true);
        fetch(`${API_BASE_URL}/auth/documents/${document.id}/preview`, {
          credentials: "include",
        })
          .then(res => {
            if (res.ok) {
              return res.blob().then(blob => {
                const url = URL.createObjectURL(blob);
                setPreviewUrl(url);
              });
            }
          })
          .catch(err => {
            console.error("Failed to load preview:", err);
            setPreviewUrl(null);
          })
          .finally(() => setPreviewLoading(false));
      } else {
        setPreviewUrl(null);
      }

      if (document.training_data) {
        try {
          const data = typeof document.training_data === 'string' 
            ? JSON.parse(document.training_data) 
            : document.training_data;
          
          setInvoiceData(prev => ({
            ...prev,
            invoice_number: data.invoice_number || "",
            invoice_date: data.invoice_date || "",
            vendor_name: data.vendor_name || "",
            amount: data.amount || "",
            vat: data.vat || "",
            total: data.total || "",
            due_date: data.due_date || "",
            reference: data.reference || "",
          }));
        } catch (e) {
          console.error("Error parsing training_data:", e);
        }
      }
    }
  }, [document]);

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
      // Only send document_name for now (invoice data will be stored separately)
      const response = await fetch(`${API_BASE_URL}/auth/documents/${document.id}`, {
        method: "PUT",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ document_name: invoiceData.document_name }),
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
                background: isMaximized ? "#7265cf" : "white",
                border: "none",
                borderRadius: "4px",
                fontSize: "1rem",
                cursor: "pointer",
                color: isMaximized ? "white" : "#7265cf",
                padding: "0.5rem 0.75rem",
                transition: "all 0.2s ease",
                fontWeight: "600",
              }}
              onMouseEnter={(e) => {
                e.target.style.background = isMaximized ? "#6055b8" : "#f5f5f5";
              }}
              onMouseLeave={(e) => {
                e.target.style.background = isMaximized ? "#7265cf" : "white";
              }}
              title={isMaximized ? "Exit fullscreen" : "Maximize"}
            >
              {isMaximized ? "⛶" : "⬜"}
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
              {previewLoading ? (
                <div>Loading preview...</div>
              ) : previewUrl ? (
                document.raw_filename?.toLowerCase().endsWith('.pdf') ? (
                  <iframe 
                    src={previewUrl} 
                    title="Document preview"
                    allow="fullscreen"
                    style={{
                      width: "100%",
                      height: "100%",
                      border: "none",
                      borderRadius: "4px",
                    }}
                  />
                ) : (
                  <img 
                    src={previewUrl} 
                    alt="Document preview" 
                    style={{
                      maxWidth: "100%",
                      maxHeight: "100%",
                      objectFit: "contain",
                    }}
                  />
                )
              ) : (
                <div>📄 Preview not available</div>
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
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div>
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
              <div>
                <label style={{ display: "block", fontWeight: "500", marginBottom: "0.5rem" }}>
                  Invoice Number
                </label>
                <input
                  type="text"
                  value={invoiceData.invoice_number}
                  onChange={(e) => handleFieldChange("invoice_number", e.target.value)}
                  placeholder="e.g., INV-2024-001"
                  style={{
                    width: "100%",
                    padding: "0.75rem",
                    border: "1px solid #d0d0d0",
                    borderRadius: "6px",
                    fontSize: "0.95rem",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontWeight: "500", marginBottom: "0.5rem" }}>
                  Invoice Date
                </label>
                <input
                  type="date"
                  value={invoiceData.invoice_date}
                  onChange={(e) => handleFieldChange("invoice_date", e.target.value)}
                  style={{
                    width: "100%",
                    padding: "0.75rem",
                    border: "1px solid #d0d0d0",
                    borderRadius: "6px",
                    fontSize: "0.95rem",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontWeight: "500", marginBottom: "0.5rem" }}>
                  Vendor Name
                </label>
                <input
                  type="text"
                  value={invoiceData.vendor_name}
                  onChange={(e) => handleFieldChange("vendor_name", e.target.value)}
                  placeholder="e.g., Acme Corp"
                  style={{
                    width: "100%",
                    padding: "0.75rem",
                    border: "1px solid #d0d0d0",
                    borderRadius: "6px",
                    fontSize: "0.95rem",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontWeight: "500", marginBottom: "0.5rem" }}>
                  Amount
                </label>
                <input
                  type="number"
                  value={invoiceData.amount}
                  onChange={(e) => handleFieldChange("amount", e.target.value)}
                  placeholder="e.g., 1000.00"
                  step="0.01"
                  style={{
                    width: "100%",
                    padding: "0.75rem",
                    border: "1px solid #d0d0d0",
                    borderRadius: "6px",
                    fontSize: "0.95rem",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontWeight: "500", marginBottom: "0.5rem" }}>
                  VAT
                </label>
                <input
                  type="number"
                  value={invoiceData.vat}
                  onChange={(e) => handleFieldChange("vat", e.target.value)}
                  placeholder="e.g., 250.00"
                  step="0.01"
                  style={{
                    width: "100%",
                    padding: "0.75rem",
                    border: "1px solid #d0d0d0",
                    borderRadius: "6px",
                    fontSize: "0.95rem",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontWeight: "500", marginBottom: "0.5rem" }}>
                  Total
                </label>
                <input
                  type="number"
                  value={invoiceData.total}
                  onChange={(e) => handleFieldChange("total", e.target.value)}
                  placeholder="e.g., 1250.00"
                  step="0.01"
                  style={{
                    width: "100%",
                    padding: "0.75rem",
                    border: "1px solid #d0d0d0",
                    borderRadius: "6px",
                    fontSize: "0.95rem",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontWeight: "500", marginBottom: "0.5rem" }}>
                  Due Date
                </label>
                <input
                  type="date"
                  value={invoiceData.due_date}
                  onChange={(e) => handleFieldChange("due_date", e.target.value)}
                  style={{
                    width: "100%",
                    padding: "0.75rem",
                    border: "1px solid #d0d0d0",
                    borderRadius: "6px",
                    fontSize: "0.95rem",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontWeight: "500", marginBottom: "0.5rem" }}>
                  Reference
                </label>
                <input
                  type="text"
                  value={invoiceData.reference}
                  onChange={(e) => handleFieldChange("reference", e.target.value)}
                  placeholder="e.g., PO-2024-123"
                  style={{
                    width: "100%",
                    padding: "0.75rem",
                    border: "1px solid #d0d0d0",
                    borderRadius: "6px",
                    fontSize: "0.95rem",
                    boxSizing: "border-box",
                  }}
                />
              </div>
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
  );
}

export default DocumentDetail;
