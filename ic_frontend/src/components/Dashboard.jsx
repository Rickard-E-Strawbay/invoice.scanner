import React, { useContext, useState, useEffect } from "react";
import { AuthContext } from "../contexts/AuthContext";
import { getPlanName, clearPlanCache } from "../utils/planMapper";
import Settings from "./Settings";
import Admin from "./Admin";
import PlansAndBilling from "./PlansAndBilling";
import DocumentDetail from "./DocumentDetail";
import "./Dashboard.css";
import "./ScanInvoice.css";
import { API_BASE_URL } from "../utils/api";

function Dashboard() {
  const { user, logout } = useContext(AuthContext);
  const [planName, setPlanName] = useState("Unknown");
  const [activeTab, setActiveTab] = useState("to-do");
  const [searchQuery, setSearchQuery] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [invoices, setInvoices] = useState([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [documentsError, setDocumentsError] = useState(null);
  const [peppolSections, setPeppolSections] = useState({});
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [currentView, setCurrentView] = useState("overview");
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [restartingDocumentId, setRestartingDocumentId] = useState(null);
  const [restartError, setRestartError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(50);
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState("desc");
  
  // Upload state
  const [uploadedImage, setUploadedImage] = useState(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploadDocumentId, setUploadDocumentId] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [isDragActive, setIsDragActive] = useState(false);
  const [uploadDocumentName, setUploadDocumentName] = useState("");
  const [uploadSectionExpanded, setUploadSectionExpanded] = useState(() => {
    // Initialize from sessionStorage, default to true (expanded)
    const cached = sessionStorage.getItem("uploadSectionExpanded");
    return cached ? JSON.parse(cached) : true;
  });

  const handleLogout = async () => {
    await logout();
  };

  // Load PEPPOL structure once on mount and cache it
  useEffect(() => {
    const loadPeppolStructure = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/documents/peppolv2`, {
          method: "GET",
          credentials: "include",
        });
        
        if (response.ok) {
          const xmlText = await response.text();
          
          // Cache XML string directly in sessionStorage
          sessionStorage.setItem("peppol_xml_schema", xmlText);
          setPeppolSections(xmlText);
        }
      } catch (err) {
        console.error("Error loading PEPPOL structure V2:", err);
      }
    };
    
    // Try to load from cache first
    const cachedXml = sessionStorage.getItem("peppol_xml_schema");
    if (cachedXml) {
      setPeppolSections(cachedXml);
    }
    
    // Always fetch to ensure fresh data
    loadPeppolStructure();
  }, []);

  // Upload handlers
  const handleImageUpload = async (file) => {
    if (!file) return;

    // Validate file type
    const allowedTypes = ["image/jpeg", "image/png", "application/pdf"];
    if (!allowedTypes.includes(file.type)) {
      setUploadError("Invalid file type. Please upload JPG, PNG, or PDF.");
      return;
    }

    // Set document name from filename without extension
    const fileName = file.name.split('.').slice(0, -1).join('.');
    setUploadDocumentName(fileName);

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
    setIsUploading(true);
    setUploadError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
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
      setUploadDocumentId(data.document?.id);
      console.log("✅ Document uploaded successfully:", data);
      
      // Switch to "To Do" tab to show the newly uploaded document
      setActiveTab("to-do");
      
      // Immediately refresh documents list
      await fetchDocuments();
      
      // Clear upload form after 1.5 seconds
      setTimeout(() => {
        handleUploadCancel();
      }, 1500);
    } catch (err) {
      console.error("❌ Upload error:", err);
      setUploadError(err.message || "Failed to upload document");
      setUploadedImage(null);
    } finally {
      setIsUploading(false);
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

  const handleUploadCancel = () => {
    setUploadedImage(null);
    setUploadedFile(null);
    setUploadDocumentId(null);
    setUploadDocumentName("");
    setUploadError(null);
  };

  // Cache upload section expanded state in sessionStorage
  useEffect(() => {
    sessionStorage.setItem("uploadSectionExpanded", JSON.stringify(uploadSectionExpanded));
  }, [uploadSectionExpanded]);

  // Fetch documents from backend
  const fetchDocuments = async (isPolling = false) => {
    try {
      // Only show loading spinner on initial fetch, not during polling
      if (!isPolling) {
        setDocumentsLoading(true);
      }
      setDocumentsError(null);
      const response = await fetch(`${API_BASE_URL}/documents/`, {
        method: "GET",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch documents");
      }

      const data = await response.json();
      const newDocuments = data.documents || [];
      
      // Smart update: only update documents that have changed
      setInvoices(prevInvoices => {
        return newDocuments.map(newDoc => {
          const oldDoc = prevInvoices.find(d => d.id === newDoc.id);
          
          // If status changed, mark as "just updated" for visual feedback
          if (oldDoc && oldDoc.status !== newDoc.status) {
            return { ...newDoc, _justUpdated: true };
          }
          
          // Return unchanged documents as-is to avoid re-renders
          return oldDoc && JSON.stringify(oldDoc) === JSON.stringify(newDoc) ? oldDoc : newDoc;
        });
      });
    } catch (err) {
      console.error("Error fetching documents:", err);
      setDocumentsError(err.message);
    } finally {
      if (!isPolling) {
        setDocumentsLoading(false);
      }
    }
  };

  // Restart document processing
  const handleRestart = async (docId) => {
    try {
      setRestartingDocumentId(docId);
      setRestartError(null);
      
      const response = await fetch(`${API_BASE_URL}/documents/${docId}/restart`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to restart document");
      }

      const data = await response.json();
      console.log("Document restart initiated:", data);
      
      // Fetch fresh documents to show updated status
      await fetchDocuments();
    } catch (err) {
      console.error("Error restarting document:", err);
      setRestartError(err.message);
    } finally {
      setRestartingDocumentId(null);
    }
  };

  // Fetch documents when scanned-invoices view is opened
  useEffect(() => {
    if (currentView === "scanned-invoices") {
      fetchDocuments();

      // Set up polling to update status every 4 seconds while in the scanned-invoices view
      // Only fetches changes, not re-renders everything
      const pollInterval = setInterval(() => {
        fetchDocuments(true); // Pass true to indicate this is a polling update
      }, 4000);

      return () => clearInterval(pollInterval);
    }
  }, [currentView]);

  // Filter invoices based on active tab and search query
  const getFilteredInvoices = () => {
    let filtered = invoices;
    
    // First filter by tab
    if (activeTab === "to-do") {
      // Show all documents that are being processed or need action
      filtered = filtered.filter(doc => 
        [
          "uploaded", 
          "preprocessing", 
          "preprocessed",
          "ocr_extracting",
          "predicting",
          "extraction", 
          "automated_evaluation",
          "predicted",
          "manual_review",
          "preprocess_error",
          "ocr_error",
          "predict_error",
          "extraction_error",
          "automated_evaluation_error"
        ].includes(doc.status)
      );
    } else if (activeTab === "approved") {
      filtered = filtered.filter(doc => doc.status === "approved" || doc.status === "completed");
    }
    
    // Then filter by search query on Document Name
    if (searchQuery.trim()) {
      const lowerQuery = searchQuery.toLowerCase();
      filtered = filtered.filter(doc => 
        (doc.document_name || doc.raw_filename || "").toLowerCase().includes(lowerQuery)
      );
    }
    
    // Finally filter by date range
    if (startDate || endDate) {
      filtered = filtered.filter(doc => {
        if (!doc.created_at) return false;
        
        const docDate = new Date(doc.created_at).toISOString().split('T')[0]; // Get date part only
        
        if (startDate && docDate < startDate) return false;
        if (endDate && docDate > endDate) return false;
        
        return true;
      });
    }
    
    return filtered;
  };

  // Get paginated and sorted invoices
  const getPaginatedInvoices = () => {
    let filtered = getFilteredInvoices();
    
    // Sort
    filtered.sort((a, b) => {
      let aVal = a[sortBy];
      let bVal = b[sortBy];
      
      // Handle null/undefined values
      if (aVal == null) aVal = "";
      if (bVal == null) bVal = "";
      
      // Handle date sorting
      if (sortBy === "created_at") {
        aVal = new Date(aVal).getTime();
        bVal = new Date(bVal).getTime();
      }
      
      // Case-insensitive string comparison
      if (typeof aVal === "string") {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }
      
      if (aVal < bVal) return sortOrder === "asc" ? -1 : 1;
      if (aVal > bVal) return sortOrder === "asc" ? 1 : -1;
      return 0;
    });
    
    // Paginate
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return filtered.slice(startIndex, endIndex);
  };

  // Count documents by category
  const getTabCounts = () => {
    const todoCount = invoices.filter(doc => 
      [
        "uploaded", 
        "preprocessing", 
        "preprocessed",
        "ocr_extracting",
        "predicting",
        "extraction", 
        "automated_evaluation",
        "predicted",
        "manual_review",
        "preprocess_error",
        "ocr_error",
        "predict_error",
        "extraction_error",
        "automated_evaluation_error"
      ].includes(doc.status)
    ).length;
    
    const approvedCount = invoices.filter(doc => 
      doc.status === "approved" || doc.status === "completed"
    ).length;
    
    const allCount = invoices.length;
    
    return { todoCount, approvedCount, allCount };
  };

  // Get total pages
  const getTotalPages = () => {
    const filtered = getFilteredInvoices();
    return Math.ceil(filtered.length / itemsPerPage);
  };

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [activeTab, searchQuery, startDate, endDate, itemsPerPage]);

  // Fetch plan name from backend
  useEffect(() => {
    const fetchPlanName = async () => {
      if (user?.price_plan_key) {
        const name = await getPlanName(user.price_plan_key);
        setPlanName(name);
      }
    };
    fetchPlanName();
  }, [user?.price_plan_key]);

  // Helper to handle column sorting
  const handleSort = (column) => {
    if (sortBy === column) {
      // Toggle sort order if same column
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      // Sort ascending on new column
      setSortBy(column);
      setSortOrder("asc");
    }
    setCurrentPage(1);
  };

  // Helper to render sort indicator
  const getSortIndicator = (column) => {
    if (sortBy !== column) return " ↕";
    return sortOrder === "asc" ? " ↑" : " ↓";
  };

  // Get initials from user name
  const getInitials = () => {
    const name = user?.name || user?.email || "User";
    const parts = name.includes("@") ? name.split("@")[0].split(".") : name.split(" ");
    return parts.map(p => p[0].toUpperCase()).join("").slice(0, 2);
  };

  const getUserName = () => {
    return user?.name || user?.email?.split("@")[0] || "User";
  };

  const getCompanyName = () => {
    return user?.company_name || "Company";
  };

  // Get plan name from state (fetched from backend)
  const getPlanNameFromState = () => {
    return planName;
  };

  // Helper function to get status colors
  const getStatusColor = (status) => {
    const statusColors = {
      // Processing stages
      "uploaded": { background: "#fef3c7", color: "#92400e" },
      "preprocessing": { background: "#dbeafe", color: "#1e40af" },
      "preprocessed": { background: "#dbeafe", color: "#1e40af" },
      "ocr_extracting": { background: "#dbeafe", color: "#1e40af" },
      "predicting": { background: "#dbeafe", color: "#1e40af" },
      "extraction": { background: "#dbeafe", color: "#1e40af" },
      "automated_evaluation": { background: "#dbeafe", color: "#1e40af" },
      "predicted": { background: "#dbeafe", color: "#1e40af" },
      
      // Error states
      "failed_preprocessing": { background: "#fee2e2", color: "#991b1b" },
      "preprocess_error": { background: "#fee2e2", color: "#991b1b" },
      "ocr_error": { background: "#fee2e2", color: "#991b1b" },
      "predict_error": { background: "#fee2e2", color: "#991b1b" },
      "extraction_error": { background: "#fee2e2", color: "#991b1b" },
      "automated_evaluation_error": { background: "#fee2e2", color: "#991b1b" },
      "error": { background: "#fee2e2", color: "#991b1b" },
      
      // Manual review
      "manual_review": { background: "#fef08a", color: "#854d0e" },
      
      // Complete states
      "completed": { background: "#d1fae5", color: "#065f46" },
      "approved": { background: "#d1fae5", color: "#065f46" }
    };

    return statusColors[status] || { background: "#f3f4f6", color: "#374151" };
  };

  // Helper function to get status icons
  const getStatusIcon = (status) => {
    // All processing/automated states should show spinner
    const processingStates = [
      "preprocessing", 
      "preprocessed",
      "ocr_extracting", 
      "predicting",
      "extraction", 
      "automated_evaluation"
    ];
    
    // Error states should show error icon
    const errorStates = [
      "failed_preprocessing",
      "preprocess_error",
      "ocr_error",
      "predict_error",
      "extraction_error",
      "automated_evaluation_error",
      "error"
    ];
    
    if (errorStates.includes(status)) {
      return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{
          display: "inline-block"
        }}>
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
      );
    }

    if (processingStates.includes(status)) {
      return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{
          animation: "spin 1s linear infinite",
          display: "inline-block"
        }}>
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 6v6"/>
        </svg>
      );
    }

    const iconMap = {
      "uploaded": "📤",
      "predicted": "✓",
      "approved": "✓",
      "manual_review": "⚠",
      "error": "✗",
      "preprocess_error": "✗",
      "ocr_error": "✗",
      "predict_error": "✗",
      "extraction_error": "✗",
      "automated_evaluation_error": "✗"
    };

    return iconMap[status] || "";
  };

  return (
    <div className="dashboard-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <img src="/images/logos/Strawbay-purple-Logotype.png" alt="Strawbay" style={{ height: "40px", width: "auto" }} />
        </div>
        <nav className="sidebar-nav">
          <button 
            onClick={() => setCurrentView("overview")}
            className={`nav-item ${currentView === "overview" ? "active" : ""}`}
            style={{ border: "none", background: "none", cursor: "pointer", width: "100%", textAlign: "left" }}
          >
            <span className="nav-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                <polyline points="9 22 9 12 15 12 15 22"></polyline>
              </svg>
            </span>
            <span>Overview</span>
          </button>
          <button 
            onClick={() => setCurrentView("scanned-invoices")}
            className={`nav-item ${currentView === "scanned-invoices" ? "active" : ""}`}
            style={{ border: "none", background: "none", cursor: "pointer", width: "100%", textAlign: "left" }}
          >
            <span className="nav-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="12" y1="11" x2="12" y2="17"></line>
                <line x1="9" y1="14" x2="15" y2="14"></line>
              </svg>
            </span>
            <span>Manage Invoices</span>
          </button>
        </nav>
        <div className="sidebar-footer">
          <div 
            className="user-card"
            onMouseEnter={() => setShowUserMenu(true)}
            onMouseLeave={() => setShowUserMenu(false)}
          >
            <div className="user-avatar">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19.43 12.98c.04-.32.07-.64.07-.98s-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65C14.46 2.18 14.25 2 14 2h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.22-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98l-2.11 1.65c-.19.15-.24.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.25 1.17-.59 1.69-.98l2.49 1c.23.09.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zM12 15.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"/>
              </svg>
            </div>
            <div className="user-details">
              <div className="user-name">{getUserName()}</div>
              <div className="user-role">{user?.email || "User"}</div>
              <div className="user-company">{getCompanyName()}</div>
            </div>
            
            {showUserMenu && (
              <div className="user-menu">
                <div className="user-menu-header">
                  <div className="user-menu-avatar">{getInitials()}</div>
                  <div className="user-menu-info">
                    <div className="user-menu-name">{getUserName()}</div>
                    <div className="user-menu-role">{user?.role_name || "User"}</div>
                    <div className="user-menu-company">{getCompanyName()}</div>
                  </div>
                </div>
                
                <a href="#" onClick={(e) => { e.preventDefault(); setCurrentView("settings"); }} className="user-menu-item">
                  <span className="menu-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M19.43 12.98c.04-.32.07-.64.07-.98s-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65C14.46 2.18 14.25 2 14 2h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.22-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98l-2.11 1.65c-.19.15-.24.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.25 1.17-.59 1.69-.98l2.49 1c.23.09.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zM12 15.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"/>
                    </svg>
                  </span>
                  <span>Settings</span>
                </a>
                
                {user?.role_key === 1000 && (
                  <a href="#" onClick={(e) => { e.preventDefault(); setCurrentView("admin"); }} className="user-menu-item">
                    <span className="menu-icon">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 10h4v4h-4z"/>
                      </svg>
                    </span>
                    <span>Admin</span>
                  </a>
                )}
                
                <a href="#" onClick={(e) => { e.preventDefault(); setCurrentView("plans-and-billing"); }} className="user-menu-item">
                  <span className="menu-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M9 2h6a2 2 0 0 1 2 2v2h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h2V4a2 2 0 0 1 2-2z"></path>
                      <path d="M9 2v4h6V2"></path>
                      <path d="M9 13l2 2 4-4"></path>
                      <line x1="9" y1="17" x2="15" y2="17"></line>
                    </svg>
                  </span>
                  <span>Plans and Billing</span>
                  <span className="menu-badge">{getPlanNameFromState()}</span>
                </a>
                
                <a href="#" className="user-menu-item">
                  <span className="menu-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10"></circle>
                      <path d="M12 16v-4"></path>
                      <path d="M12 8h.01"></path>
                    </svg>
                  </span>
                  <span>Help Center</span>
                </a>
                
                <a href="#" className="user-menu-item">
                  <span className="menu-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10"></circle>
                      <polygon points="10 8 16 12 10 16 10 8"></polygon>
                    </svg>
                  </span>
                  <span>Show Startup Guide</span>
                </a>
                
                <div className="user-menu-divider"></div>
                
                <button onClick={handleLogout} className="user-menu-item logout">
                  <span className="menu-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                      <polyline points="16 17 21 12 16 7"></polyline>
                      <line x1="21" y1="12" x2="9" y2="12"></line>
                    </svg>
                  </span>
                  <span>Logout</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      <main className="main-content">
        {currentView === "overview" && (
          <div className="empty-overview">
            <div className="empty-overview-content">
              <h1>Welcome to Strawbay</h1>
              <p>Select an option from the sidebar to get started</p>
            </div>
          </div>
        )}

        {currentView === "scanned-invoices" && (
          <>
            <div className="content-header">
              <h1>Manage Invoices</h1>
            </div>

            {/* Upload Section - Collapsible Accordion */}
            <div style={{ marginBottom: "0" }}>
              <button
                onClick={() => setUploadSectionExpanded(!uploadSectionExpanded)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  padding: "0.375rem 1rem",
                  background: "#f5f7fa",
                  border: "1px solid #e8ecf1",
                  borderRadius: uploadSectionExpanded ? "6px 6px 0 0" : "6px",
                  cursor: "pointer",
                  fontWeight: "600",
                  color: "#333",
                  width: "100%",
                  textAlign: "left",
                  transition: "all 0.2s"
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "#eff0f5";
                  e.currentTarget.style.borderColor = "#d0d5e0";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "#f5f7fa";
                  e.currentTarget.style.borderColor = "#e8ecf1";
                }}
              >
                <svg 
                  width="20" 
                  height="20" 
                  viewBox="0 0 24 24" 
                  fill="none" 
                  stroke="currentColor" 
                  strokeWidth="2"
                  style={{
                    transform: uploadSectionExpanded ? "rotate(180deg)" : "rotate(0deg)",
                    transition: "transform 0.2s",
                    flexShrink: 0
                  }}
                >
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
                <span>Upload Invoices</span>
              </button>

              {uploadSectionExpanded && (
                <div className="upload-section" style={{ 
                  marginTop: "0",
                  borderTop: "none",
                  borderRadius: "0 0 6px 6px",
                  border: "1px solid #e8ecf1",
                  borderTop: "none",
                  padding: "1rem"
                }}>
                  <div 
                    className={`upload-area ${isDragActive ? "drag-active" : ""}`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                  >
                    <input
                      type="file"
                      id="file-input-dashboard"
                      onChange={handleFileInputChange}
                      accept="image/*,.pdf"
                      style={{ display: "none" }}
                      disabled={isUploading}
                    />
                    <label htmlFor="file-input-dashboard" className="upload-label">
                      <div className="upload-icon">
                        {isUploading ? (
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
                      <p className="upload-title">{isUploading ? "Uploading..." : "Upload Invoice"}</p>
                      <p className="upload-subtitle">Drag and drop or click to select file</p>
                      <p className="upload-formats">Accepted formats: JPG, PNG, PDF</p>
                    </label>
                  </div>

                  {uploadError && (
                    <div style={{
                      marginTop: "1rem",
                      padding: "1rem",
                      background: "#fee",
                      borderRadius: "6px",
                      borderLeft: "4px solid #ef4444",
                      color: "#991b1b"
                    }}>
                      {uploadError}
                    </div>
                  )}

                  {uploadDocumentId && (
                    <div style={{
                      marginTop: "1rem",
                      padding: "1rem",
                      background: "#f0fdf4",
                      borderRadius: "6px",
                      borderLeft: "4px solid #10b981",
                      color: "#166534"
                    }}>
                      ✓ Document uploaded successfully! ID: {uploadDocumentId}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="tabs">
              <button
                className={`tab ${activeTab === "to-do" ? "active" : ""}`}
                onClick={() => setActiveTab("to-do")}
              >
                To Do ({getTabCounts().todoCount})
              </button>
              <button
                className={`tab ${activeTab === "approved" ? "active" : ""}`}
                onClick={() => setActiveTab("approved")}
              >
                Approved ({getTabCounts().approvedCount})
              </button>
              <button
                className={`tab ${activeTab === "all" ? "active" : ""}`}
                onClick={() => setActiveTab("all")}
              >
                All Invoices ({getTabCounts().allCount})
              </button>
            </div>

            <div className="search-section">
              <div className="search-box">
                <input 
                  type="text" 
                  placeholder="Search by Document Name..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <span className="search-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8"/>
                    <path d="m21 21-4.35-4.35"/>
                  </svg>
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <input 
                  type="date" 
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  title="Start date"
                  className="date-input" 
                />
                <span style={{ color: "#999", fontSize: "0.9rem" }}>—</span>
                <input 
                  type="date" 
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  title="End date"
                  className="date-input" 
                />
                {(startDate || endDate) && (
                  <button 
                    className="filter-btn"
                    onClick={() => {
                      setStartDate("");
                      setEndDate("");
                    }}
                    title="Clear date filters"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>

            <div className="invoices-section">
              {documentsLoading ? (
                <div className="empty-state">
                  <p>Loading documents...</p>
                </div>
              ) : documentsError ? (
                <div className="empty-state">
                  <p style={{ color: "#ef4444" }}>Error: {documentsError}</p>
                </div>
              ) : invoices.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">
                    <svg width="50" height="50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                      <line x1="12" y1="11" x2="12" y2="17"/>
                      <line x1="9" y1="14" x2="15" y2="14"/>
                    </svg>
                  </div>
                  <p className="empty-title">No invoices scanned yet</p>
                  <p className="empty-subtitle">Here you can view and manage invoices scanned on your company</p>
                </div>
              ) : getFilteredInvoices().length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">
                    <svg width="50" height="50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                      <line x1="12" y1="11" x2="12" y2="17"/>
                      <line x1="9" y1="14" x2="15" y2="14"/>
                    </svg>
                  </div>
                  <p className="empty-title">No invoices found</p>
                  <p className="empty-subtitle">No invoices match the current filter</p>
                </div>
              ) : (
                <div className="invoices-list">
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "2px solid #e8ecf1", background: "#f5f7fa" }}>
                        <th 
                          onClick={() => handleSort("document_name")}
                          style={{ 
                            padding: "1rem", 
                            textAlign: "left", 
                            fontWeight: "600", 
                            width: "160px",
                            cursor: "pointer",
                            userSelect: "none",
                            transition: "background 0.2s"
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = "#eff0f5"}
                          onMouseLeave={(e) => e.currentTarget.style.background = "#f5f7fa"}
                          title="Click to sort by document name"
                        >
                          Document Name{getSortIndicator("document_name")}
                        </th>
                        <th 
                          onClick={() => handleSort("status")}
                          style={{ 
                            padding: "1rem", 
                            textAlign: "left", 
                            fontWeight: "600", 
                            width: "180px",
                            cursor: "pointer",
                            userSelect: "none",
                            transition: "background 0.2s"
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = "#eff0f5"}
                          onMouseLeave={(e) => e.currentTarget.style.background = "#f5f7fa"}
                          title="Click to sort by status"
                        >
                          Status{getSortIndicator("status")}
                        </th>
                        <th 
                          onClick={() => handleSort("created_at")}
                          style={{ 
                            padding: "1rem", 
                            textAlign: "left", 
                            fontWeight: "600",
                            cursor: "pointer",
                            userSelect: "none",
                            transition: "background 0.2s"
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = "#eff0f5"}
                          onMouseLeave={(e) => e.currentTarget.style.background = "#f5f7fa"}
                          title="Click to sort by upload date"
                        >
                          Uploaded{getSortIndicator("created_at")}
                        </th>
                        <th 
                          onClick={() => handleSort("predicted_accuracy")}
                          style={{ 
                            padding: "1rem", 
                            textAlign: "left", 
                            fontWeight: "600",
                            cursor: "pointer",
                            userSelect: "none",
                            transition: "background 0.2s"
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = "#eff0f5"}
                          onMouseLeave={(e) => e.currentTarget.style.background = "#f5f7fa"}
                          title="Click to sort by accuracy"
                        >
                          Accuracy{getSortIndicator("predicted_accuracy")}
                        </th>
                        <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600" }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {getPaginatedInvoices().map((doc) => (
                        <tr key={doc.id} style={{ 
                          borderBottom: "1px solid #e8ecf1"
                        }}>
                          <td style={{ 
                            padding: "1rem", 
                            width: "160px",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap"
                          }}>
                            <a 
                              onClick={() => setSelectedDocument(doc)}
                              style={{
                                color: "#7265cf",
                                cursor: "pointer",
                                textDecoration: "none",
                                borderBottom: "1px solid transparent",
                                transition: "all 0.2s"
                              }}
                              onMouseEnter={(e) => {
                                e.target.style.textDecoration = "underline";
                                e.target.style.color = "#5a4db8";
                              }}
                              onMouseLeave={(e) => {
                                e.target.style.textDecoration = "none";
                                e.target.style.color = "#7265cf";
                              }}
                              title={doc.document_name || doc.raw_filename}
                            >
                              {doc.document_name || doc.raw_filename}
                            </a>
                          </td>
                          <td style={{ padding: "1rem", width: "180px" }}>
                            <span style={{
                              padding: "0.25rem 0.75rem",
                              borderRadius: "4px",
                              background: getStatusColor(doc.status).background,
                              color: getStatusColor(doc.status).color,
                              fontSize: "0.85rem",
                              fontWeight: "500",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "0.5rem"
                            }}>
                              {getStatusIcon(doc.status)}
                              {doc.status_name || doc.status}
                            </span>
                          </td>
                          <td style={{ padding: "1rem", color: "#666" }}>
                            {doc.created_at ? new Date(doc.created_at).toLocaleDateString("sv-SE") : "-"}
                          </td>
                          <td style={{ padding: "1rem", color: "#666" }}>
                            {doc.predicted_accuracy ? `${doc.predicted_accuracy}%` : "-"}
                          </td>
                          <td style={{ padding: "1rem" }}>
                            <div style={{ display: "flex", gap: "0.5rem" }}>
                              <button
                                onClick={() => handleRestart(doc.id)}
                                disabled={restartingDocumentId === doc.id || ["preprocessing", "preprocessed", "ocr_extracting", "predicting", "extraction", "automated_evaluation"].includes(doc.status)}
                                title={restartingDocumentId === doc.id ? "Restarting..." : ["preprocessing", "preprocessed", "ocr_extracting", "predicting", "extraction", "automated_evaluation"].includes(doc.status) ? "Cannot restart while processing" : "Restart document"}
                                style={{
                                  padding: "0.4rem",
                                  background: "transparent",
                                  border: "none",
                                  cursor: (restartingDocumentId === doc.id || ["preprocessing", "preprocessed", "ocr_extracting", "predicting", "extraction", "automated_evaluation"].includes(doc.status)) ? "not-allowed" : "pointer",
                                  opacity: (restartingDocumentId === doc.id || ["preprocessing", "preprocessed", "ocr_extracting", "predicting", "extraction", "automated_evaluation"].includes(doc.status)) ? 0.5 : 1,
                                  transition: "opacity 0.2s, transform 0.1s",
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "center"
                                }}
                                onMouseEnter={(e) => {
                                  if (restartingDocumentId !== doc.id && !["preprocessing", "preprocessed", "ocr_extracting", "predicting", "extraction", "automated_evaluation"].includes(doc.status)) {
                                    e.currentTarget.style.opacity = "0.7";
                                    const svg = e.currentTarget.querySelector("svg");
                                    if (svg) {
                                      svg.style.animation = "spin 1s linear infinite";
                                    }
                                  }
                                }}
                                onMouseLeave={(e) => {
                                  if (restartingDocumentId !== doc.id && !["preprocessing", "preprocessed", "ocr_extracting", "predicting", "extraction", "automated_evaluation"].includes(doc.status)) {
                                    e.currentTarget.style.opacity = "1";
                                    const svg = e.currentTarget.querySelector("svg");
                                    if (svg) {
                                      svg.style.animation = "none";
                                    }
                                  }
                                }}
                                onMouseDown={(e) => {
                                  if (restartingDocumentId !== doc.id && !["preprocessing", "preprocessed", "ocr_extracting", "predicting", "extraction", "automated_evaluation"].includes(doc.status)) {
                                    e.currentTarget.style.transform = "scale(0.95)";
                                  }
                                }}
                                onMouseUp={(e) => {
                                  if (restartingDocumentId !== doc.id && !["preprocessing", "preprocessed", "ocr_extracting", "predicting", "extraction", "automated_evaluation"].includes(doc.status)) {
                                    e.currentTarget.style.transform = "scale(1)";
                                  }
                                }}
                              >
                                <svg 
                                  width="18" 
                                  height="18" 
                                  viewBox="0 0 24 24" 
                                  fill="none" 
                                  stroke="#666" 
                                  strokeWidth="2"
                                  style={{
                                    animation: restartingDocumentId === doc.id ? "spin 1s linear infinite" : "none",
                                    display: "inline-block"
                                  }}
                                >
                                  <path d="M21.5 2v6h-6M2.5 22v-6h6"/>
                                  <path d="M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
                                </svg>
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <div style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "1.5rem",
                    borderTop: "1px solid #e8ecf1",
                    backgroundColor: "#fafbfc"
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <label style={{ fontSize: "0.9rem", color: "#666" }}>Items per page:</label>
                      <select 
                        value={itemsPerPage}
                        onChange={(e) => setItemsPerPage(parseInt(e.target.value))}
                        style={{
                          padding: "0.5rem 0.75rem",
                          border: "1px solid #ddd",
                          borderRadius: "4px",
                          fontSize: "0.9rem",
                          cursor: "pointer",
                          backgroundColor: "white"
                        }}
                      >
                        <option value={50}>50</option>
                        <option value={100}>100</option>
                        <option value={250}>250</option>
                      </select>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <button 
                        onClick={() => setCurrentPage(1)}
                        disabled={currentPage === 1}
                        title="First page"
                        style={{
                          padding: "0.4rem",
                          background: "transparent",
                          border: "1px solid #ddd",
                          borderRadius: "4px",
                          cursor: currentPage === 1 ? "not-allowed" : "pointer",
                          opacity: currentPage === 1 ? 0.5 : 1,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          transition: "all 0.2s"
                        }}
                        onMouseEnter={(e) => {
                          if (currentPage !== 1) {
                            e.currentTarget.style.background = "#f0f0f0";
                            e.currentTarget.style.borderColor = "#bbb";
                          }
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = "transparent";
                          e.currentTarget.style.borderColor = "#ddd";
                        }}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="19 12 12 19 5 12 12 5 19 12"></polyline>
                          <line x1="12" y1="19" x2="12" y2="5"></line>
                        </svg>
                      </button>
                      
                      <button 
                        onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                        disabled={currentPage === 1}
                        title="Previous page"
                        style={{
                          padding: "0.4rem",
                          background: "transparent",
                          border: "1px solid #ddd",
                          borderRadius: "4px",
                          cursor: currentPage === 1 ? "not-allowed" : "pointer",
                          opacity: currentPage === 1 ? 0.5 : 1,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          transition: "all 0.2s"
                        }}
                        onMouseEnter={(e) => {
                          if (currentPage !== 1) {
                            e.currentTarget.style.background = "#f0f0f0";
                            e.currentTarget.style.borderColor = "#bbb";
                          }
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = "transparent";
                          e.currentTarget.style.borderColor = "#ddd";
                        }}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="15 18 9 12 15 6"></polyline>
                        </svg>
                      </button>

                      <span style={{ fontSize: "0.9rem", color: "#666", whiteSpace: "nowrap", minWidth: "120px", textAlign: "center" }}>
                        Page {currentPage} of {getTotalPages() || 1}
                      </span>

                      <button 
                        onClick={() => setCurrentPage(prev => Math.min(getTotalPages(), prev + 1))}
                        disabled={currentPage === getTotalPages()}
                        title="Next page"
                        style={{
                          padding: "0.4rem",
                          background: "transparent",
                          border: "1px solid #ddd",
                          borderRadius: "4px",
                          cursor: currentPage === getTotalPages() ? "not-allowed" : "pointer",
                          opacity: currentPage === getTotalPages() ? 0.5 : 1,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          transition: "all 0.2s"
                        }}
                        onMouseEnter={(e) => {
                          if (currentPage !== getTotalPages()) {
                            e.currentTarget.style.background = "#f0f0f0";
                            e.currentTarget.style.borderColor = "#bbb";
                          }
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = "transparent";
                          e.currentTarget.style.borderColor = "#ddd";
                        }}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="9 18 15 12 9 6"></polyline>
                        </svg>
                      </button>

                      <button 
                        onClick={() => setCurrentPage(getTotalPages())}
                        disabled={currentPage === getTotalPages()}
                        title="Last page"
                        style={{
                          padding: "0.4rem",
                          background: "transparent",
                          border: "1px solid #ddd",
                          borderRadius: "4px",
                          cursor: currentPage === getTotalPages() ? "not-allowed" : "pointer",
                          opacity: currentPage === getTotalPages() ? 0.5 : 1,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          transition: "all 0.2s"
                        }}
                        onMouseEnter={(e) => {
                          if (currentPage !== getTotalPages()) {
                            e.currentTarget.style.background = "#f0f0f0";
                            e.currentTarget.style.borderColor = "#bbb";
                          }
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = "transparent";
                          e.currentTarget.style.borderColor = "#ddd";
                        }}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="5 12 12 5 19 12 12 19 5 12"></polyline>
                          <line x1="12" y1="5" x2="12" y2="19"></line>
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              )}
              {selectedDocument && (
                <DocumentDetail 
                  document={selectedDocument} 
                  peppolSections={peppolSections}
                  onClose={() => setSelectedDocument(null)}
                  onSave={fetchDocuments}
                />
              )}
            </div>
          </>
        )}

        {currentView === "settings" && (
          <Settings />
        )}

        {currentView === "admin" && (
          <Admin />
        )}

        {currentView === "plans-and-billing" && (
          <PlansAndBilling onNavigate={(view, tab) => {
            setCurrentView(view);
            if (view === "settings" && tab) {
              // Store the tab to be selected in Settings
              localStorage.setItem("settings-active-tab", tab);
            }
          }} />
        )}


      </main>
    </div>
  );
}

export default Dashboard;
