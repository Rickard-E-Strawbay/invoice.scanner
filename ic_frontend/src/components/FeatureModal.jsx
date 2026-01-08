import React from "react";

function FeatureModal({ feature, onClose }) {
  if (!feature) return null;

  // Simple markdown to HTML converter for basic formatting
  const renderMarkdown = (text) => {
    if (!text) return "";
    
    return text
      .split("\n")
      .map((line, idx) => {
        if (line.startsWith("## ")) {
          return <h3 key={idx} style={{ margin: "0.5rem 0 0.25rem 0", fontSize: "0.95rem", fontWeight: "600", color: "#333" }}>{line.replace("## ", "")}</h3>;
        }
        if (line.startsWith("### ")) {
          return <h4 key={idx} style={{ margin: "0.4rem 0 0.2rem 0", fontSize: "0.85rem", fontWeight: "600", color: "#555" }}>{line.replace("### ", "")}</h4>;
        }
        if (line.startsWith("- ")) {
          return <li key={idx} style={{ marginLeft: "1rem", marginBottom: "0.1rem", color: "#666", fontSize: "0.8rem" }}>{line.replace("- ", "")}</li>;
        }
        if (line.trim() === "") {
          return <div key={idx} style={{ height: "0.25rem" }}></div>;
        }
        return <p key={idx} style={{ margin: "0.25rem 0", color: "#666", lineHeight: "1.4", fontSize: "0.8rem" }}>{line}</p>;
      });
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
          maxWidth: "550px",
          width: "100%",
          maxHeight: "70vh",
          overflow: "auto",
          padding: "1.25rem",
          boxShadow: "0 10px 40px rgba(0, 0, 0, 0.2)"
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: "0.75rem" }}>
          <div>
            <h2 style={{ margin: "0 0 0.25rem 0", color: "#333", fontSize: "1.25rem" }}>
              {feature.feature_name}
            </h2>
            <p style={{ margin: "0", color: "#999", fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              {feature.feature_category}
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              fontSize: "1.25rem",
              color: "#999",
              cursor: "pointer",
              padding: "0",
              width: "28px",
              height: "28px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0
            }}
          >
            ✕
          </button>
        </div>

        <div style={{ marginBottom: "0.75rem", padding: "0.75rem", background: "#f9f9f9", borderRadius: "6px", borderLeft: "3px solid #7265cf" }}>
          <p style={{ margin: "0", color: "#333", fontStyle: "italic", fontSize: "0.8rem" }}>
            {feature.feature_short_description}
          </p>
        </div>

        <div style={{ color: "#333", lineHeight: "1.4" }}>
          {renderMarkdown(feature.feature_description)}
        </div>

        <div style={{ marginTop: "1rem", paddingTop: "0.75rem", borderTop: "1px solid #e8ecf1" }}>
          <button
            onClick={onClose}
            style={{
              width: "100%",
              padding: "0.6rem",
              background: "#7265cf",
              color: "white",
              border: "none",
              borderRadius: "6px",
              fontSize: "0.85rem",
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
      </div>
    </div>
  );
}

export default FeatureModal;
