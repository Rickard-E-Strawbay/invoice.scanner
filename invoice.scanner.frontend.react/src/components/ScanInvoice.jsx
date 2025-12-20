import React, { useState } from "react";
import "./ScanInvoice.css";

function ScanInvoice({ onBack }) {
  const [uploadedImage, setUploadedImage] = useState(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [documentId, setDocumentId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isDragActive, setIsDragActive] = useState(false);
  
  const [invoiceElements, setInvoiceElements] = useState([
    { label: "Invoice Number", value: "" },
    { label: "Date", value: "" },
    { label: "Vendor", value: "" },
    { label: "Amount", value: "" },
    { label: "VAT", value: "" },
    { label: "Total", value: "" },
    { label: "Due Date", value: "" },
    { label: "Reference", value: "" }
  ]);

  const handleImageUpload = async (file) => {
    if (!file) return;

    // Validate file type
    const allowedTypes = ["image/jpeg", "image/png", "application/pdf"];
    if (!allowedTypes.includes(file.type)) {
      setError("Invalid file type. Please upload JPG, PNG, or PDF.");
      return;
    }

    // Preview
    const reader = new FileReader();
    reader.onload = (event) => {
      setUploadedImage(event.target?.result);
    };
    reader.readAsDataURL(file);

    // Upload to backend
    await uploadDocumentToBackend(file);
  };

  const uploadDocumentToBackend = async (file) => {
    setIsLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("http://localhost:8000/auth/documents/upload", {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Upload failed");
      }

      const data = await response.json();
      setUploadedFile(file);
      setDocumentId(data.document?.id);
      console.log("✅ Document uploaded successfully:", data);
    } catch (err) {
      console.error("❌ Upload error:", err);
      setError(err.message || "Failed to upload document");
      setUploadedImage(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true);
    } else if (e.type === "dragleave") {
      setIsDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      handleImageUpload(files[0]);
    }
  };

  const handleFileInputChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      handleImageUpload(file);
    }
  };

  const handleElementChange = (index, value) => {
    const newElements = [...invoiceElements];
    newElements[index].value = value;
    setInvoiceElements(newElements);
  };

  const handleCancel = () => {
    setUploadedImage(null);
    setUploadedFile(null);
    setDocumentId(null);
    setError(null);
    setInvoiceElements(invoiceElements.map(el => ({ ...el, value: "" })));
  };

  return (
    <div className="scan-invoice-content">
      <div className="scan-content-header">
        <h1>Scan/Update</h1>
      </div>

      <div className="upload-section">
        <div 
          className={`upload-area ${isDragActive ? "drag-active" : ""}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            type="file"
            id="file-input"
            onChange={handleFileInputChange}
            accept="image/*,.pdf"
            style={{ display: "none" }}
            disabled={isLoading}
          />
          <label htmlFor="file-input" className="upload-label">
            <div className="upload-icon">
              {isLoading ? (
                <div className="spinner">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/>
                  </svg>
                </div>
              ) : (
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
              )}
            </div>
            <p className="upload-title">{isLoading ? "Uploading..." : "Upload Invoice"}</p>
            <p className="upload-subtitle">Drag and drop or click to select file</p>
            <p className="upload-formats">Accepted formats: JPG, PNG, PDF</p>
          </label>
        </div>

        {error && (
          <div style={{
            marginTop: "1rem",
            padding: "1rem",
            background: "#fee",
            borderRadius: "6px",
            borderLeft: "4px solid #ef4444",
            color: "#991b1b"
          }}>
            {error}
          </div>
        )}

        {documentId && (
          <div style={{
            marginTop: "1rem",
            padding: "1rem",
            background: "#f0fdf4",
            borderRadius: "6px",
            borderLeft: "4px solid #10b981",
            color: "#166534"
          }}>
            ✓ Document uploaded successfully! ID: {documentId}
          </div>
        )}
      </div>

      <div className="scan-content">
        <div className="invoice-preview">
          {uploadedImage ? (
            <img src={uploadedImage} alt="Uploaded invoice" className="preview-image" />
          ) : (
            <div className="preview-placeholder">
              <p>No image uploaded</p>
            </div>
          )}
        </div>

        <div className="invoice-elements">
          <h2>Invoice Elements</h2>
          <div className="elements-list">
            {invoiceElements.map((element, index) => (
              <div key={index} className="element-item">
                <label>{element.label}</label>
                <input
                  type="text"
                  value={element.value}
                  onChange={(e) => handleElementChange(index, e.target.value)}
                  placeholder="Not detected"
                  disabled={!uploadedImage}
                />
              </div>
            ))}
          </div>
          <div className="scan-actions">
            <button 
              className="btn-secondary"
              onClick={handleCancel}
              disabled={isLoading || !uploadedImage}
            >
              Cancel
            </button>
            <button 
              className="btn-primary"
              disabled={isLoading || !uploadedImage || !documentId}
            >
              Save Invoice
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ScanInvoice;
