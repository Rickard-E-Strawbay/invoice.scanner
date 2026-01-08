import React, { useState, useRef, useEffect } from "react";
import "./TermsOfService.css";
import ReactMarkdown from "react-markdown";

function TermsOfService({ onAccept, onClose }) {
  const [hasScrolledToBottom, setHasScrolledToBottom] = useState(false);
  const [isAccepted, setIsAccepted] = useState(false);
  const [tosContent, setTosContent] = useState("");
  const [tosVersion, setTosVersion] = useState("");
  const scrollContainerRef = useRef(null);

  useEffect(() => {
    // Fetch the latest ToS file
    const fetchToS = async () => {
      try {
        const response = await fetch("/terms-of-service/1_0_toc.md");
        const text = await response.text();
        setTosContent(text);
        // Extract version from filename: 1_0_toc.md -> 1.0
        setTosVersion("1.0");
      } catch (error) {
        console.error("Error loading Terms of Service:", error);
        setTosContent("Error loading Terms of Service. Please try again later.");
      }
    };

    fetchToS();
  }, []);

  const handleScroll = () => {
    if (scrollContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
      // Check if scrolled to bottom (with 10px tolerance)
      if (scrollTop + clientHeight >= scrollHeight - 10) {
        setHasScrolledToBottom(true);
      }
    }
  };

  const handleAccept = () => {
    if (hasScrolledToBottom && isAccepted) {
      onAccept(tosVersion);
    }
  };

  return (
    <div className="terms-overlay">
      <div className="terms-modal">
        <div className="terms-header">
          <h2>Strawbay Invoice Scanner - Terms of Service (v{tosVersion})</h2>
          <button className="terms-close" onClick={onClose}>×</button>
        </div>

        <div
          className="terms-content"
          ref={scrollContainerRef}
          onScroll={handleScroll}
        >
          <ReactMarkdown>{tosContent}</ReactMarkdown>
        </div>

        <div className="terms-footer">
          <label className="terms-checkbox">
            <input
              type="checkbox"
              checked={isAccepted}
              onChange={(e) => setIsAccepted(e.target.checked)}
              disabled={!hasScrolledToBottom}
            />
            <span>I have read and agree to the Terms of Service</span>
          </label>
          {!hasScrolledToBottom && (
            <p className="terms-scroll-hint">Please scroll down to read all terms</p>
          )}
          <div className="terms-actions">
            <button className="terms-button cancel" onClick={onClose}>
              Decline
            </button>
            <button
              className="terms-button accept"
              onClick={handleAccept}
              disabled={!hasScrolledToBottom || !isAccepted}
            >
              Accept & Continue
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TermsOfService;
