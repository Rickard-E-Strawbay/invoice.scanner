import React from "react";

function MessageModal({ type, title, message, onClose }) {
  // type: "success" | "error"
  if (!type || !message) return null;

  const isSuccess = type === "success";
  const bgColor = isSuccess ? "#f0f4ff" : "#fff3f0";
  const borderColor = isSuccess ? "#7265cf" : "#d32f2f";
  const buttonColor = isSuccess ? "#7265cf" : "#d32f2f";

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
          maxWidth: "400px",
          width: "100%",
          padding: "1.5rem",
          boxShadow: "0 10px 40px rgba(0, 0, 0, 0.2)"
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", alignItems: "start", gap: "0.75rem", marginBottom: "1rem" }}>
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "50%",
              background: bgColor,
              border: `2px solid ${borderColor}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: borderColor,
              flexShrink: 0,
              fontSize: "1.25rem",
              fontWeight: "bold"
            }}
          >
            {isSuccess ? "✓" : "!"}
          </div>
          <div style={{ flex: 1 }}>
            <h2 style={{ margin: "0 0 0.5rem 0", color: "#333", fontSize: "1.1rem" }}>
              {title || (isSuccess ? "Success" : "Error")}
            </h2>
            <p style={{ margin: "0", color: "#666", fontSize: "0.9rem", lineHeight: "1.4" }}>
              {message}
            </p>
          </div>
        </div>

        <div style={{ marginTop: "1.5rem", paddingTop: "1rem", borderTop: "1px solid #e8ecf1" }}>
          <button
            onClick={onClose}
            style={{
              width: "100%",
              padding: "0.65rem",
              background: buttonColor,
              color: "white",
              border: "none",
              borderRadius: "6px",
              fontSize: "0.9rem",
              fontWeight: "600",
              cursor: "pointer",
              transition: "background-color 0.3s"
            }}
            onMouseEnter={(e) => {
              e.target.style.backgroundColor = isSuccess ? "#5e52a3" : "#b71c1c";
            }}
            onMouseLeave={(e) => {
              e.target.style.backgroundColor = buttonColor;
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default MessageModal;
