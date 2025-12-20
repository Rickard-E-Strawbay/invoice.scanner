import React, { useState, useEffect } from "react";

function DocumentDetail({ document, onClose, onSave }) {
  const [invoiceData, setInvoiceData] = useState({
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

  // Initialize invoice data from document's training_data
  useEffect(() => {
    if (document && document.training_data) {
      try {
        const data = typeof document.training_data === 'string' 
          ? JSON.parse(document.training_data) 
          : document.training_data;
        
        setInvoiceData({
          invoice_number: data.invoice_number || "",
          invoice_date: data.invoice_date || "",
          vendor_name: data.vendor_name || "",
          amount: data.amount || "",
          vat: data.vat || "",
          total: data.total || "",
          due_date: data.due_date || "",
          reference: data.reference || "",
        });
      } catch (e) {
        console.error("Error parsing training_data:", e);
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
      const response = await fetch(`http://localhost:8000/auth/documents/${document.id}`, {
        method: "PUT",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(invoiceData),
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
        borderRadius: "8px",
        width: "90%",
        maxWidth: "900px",
        maxHeight: "90vh",
        overflow: "auto",
        boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)",
      }}>
        {/* Header */}
        <div style={{
          padding: "1.5rem",
          borderBottom: "1px solid #e8ecf1",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "#f9fafb",
        }}>
          <div>
            <h2 style={{ margin: 0, fontSize: "1.25rem", color: "#1a1a1a" }}>
              {document.raw_filename}
            </h2>
            <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.85rem", color: "#666" }}>
              Uploaded {new Date(document.created_at).toLocaleDateString("sv-SE")}
            </p>
          </div>
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

        {/* Content */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "2rem",
          padding: "2rem",
        }}>
          {/* Preview */}
          <div>
            <h3 style={{ marginTop: 0, color: "#1a1a1a" }}>Document Preview</h3>
            <div style={{
              background: "#f5f7fa",
              borderRadius: "6px",
              padding: "1rem",
              minHeight: "300px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#999",
            }}>
              📄 Preview not available yet
            </div>
          </div>

          {/* Form */}
          <div>
            <h3 style={{ marginTop: 0, color: "#1a1a1a" }}>Invoice Details</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
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
