import React, { useContext, useState, useEffect } from "react";
import { AuthContext } from "../contexts/AuthContext";
import { getPlanName, clearPlanCache } from "../utils/planMapper";
import ScanInvoice from "./ScanInvoice";
import Settings from "./Settings";
import Admin from "./Admin";
import PlansAndBilling from "./PlansAndBilling";
import DocumentDetail from "./DocumentDetail";
import "./Dashboard.css";

function Dashboard() {
  const { user, logout } = useContext(AuthContext);
  const [planName, setPlanName] = useState("Unknown");
  const [activeTab, setActiveTab] = useState("to-do");
  const [invoices, setInvoices] = useState([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [documentsError, setDocumentsError] = useState(null);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [currentView, setCurrentView] = useState("overview");
  const [selectedDocument, setSelectedDocument] = useState(null);

  const handleLogout = async () => {
    await logout();
  };

  // Fetch documents from backend
  const fetchDocuments = async () => {
    try {
      setDocumentsLoading(true);
      setDocumentsError(null);
      const response = await fetch("http://localhost:8000/auth/documents", {
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
      setInvoices(data.documents || []);
    } catch (err) {
      console.error("Error fetching documents:", err);
      setDocumentsError(err.message);
    } finally {
      setDocumentsLoading(false);
    }
  };

  // Fetch documents when scanned-invoices view is opened
  useEffect(() => {
    if (currentView === "scanned-invoices") {
      fetchDocuments();
    }
  }, [currentView]);

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
            <span>Scanned Invoices</span>
          </button>
          <button 
            onClick={() => setCurrentView("scan-invoice")}
            className={`nav-item ${currentView === "scan-invoice" ? "active" : ""}`}
            style={{ border: "none", background: "none", cursor: "pointer", width: "100%", textAlign: "left" }}
          >
            <span className="nav-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 5v14M5 12h14"></path>
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              </svg>
            </span>
            <span>Scan/Update</span>
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
              <h1>Scanned Invoices</h1>
            </div>

            <div className="tabs">
              <button
                className={`tab ${activeTab === "to-do" ? "active" : ""}`}
                onClick={() => setActiveTab("to-do")}
              >
                To Do
              </button>
              <button
                className={`tab ${activeTab === "approved" ? "active" : ""}`}
                onClick={() => setActiveTab("approved")}
              >
                Approved
              </button>
              <button
                className={`tab ${activeTab === "all" ? "active" : ""}`}
                onClick={() => setActiveTab("all")}
              >
                All Invoices
              </button>
            </div>

            <div className="search-section">
              <div className="search-box">
                <input type="text" placeholder="Search Invoice..." />
                <span className="search-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8"/>
                    <path d="m21 21-4.35-4.35"/>
                  </svg>
                </span>
              </div>
              <input type="date" defaultValue="2024-12-01" className="date-input" />
              <button className="filter-btn">Filter</button>
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
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                      <line x1="12" y1="19" x2="12" y2="5"/>
                      <line x1="9" y1="10" x2="15" y2="10"/>
                    </svg>
                  </div>
                  <p className="empty-title">No invoices scanned yet</p>
                  <p className="empty-subtitle">Here you can view and manage invoices scanned on your company</p>
                </div>
              ) : (
                <div className="invoices-list">
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "2px solid #e8ecf1", background: "#f5f7fa" }}>
                        <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600" }}>File Name</th>
                        <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600" }}>Status</th>
                        <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600" }}>Uploaded</th>
                        <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600" }}>Accuracy</th>
                        <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600" }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {invoices.map((doc) => (
                        <tr key={doc.id} style={{ borderBottom: "1px solid #e8ecf1" }}>
                          <td style={{ padding: "1rem" }}>{doc.raw_filename}</td>
                          <td style={{ padding: "1rem" }}>
                            <span style={{
                              padding: "0.25rem 0.75rem",
                              borderRadius: "4px",
                              background: doc.status === "uploaded" ? "#fef3c7" : "#d1fae5",
                              color: doc.status === "uploaded" ? "#92400e" : "#065f46",
                              fontSize: "0.85rem",
                              fontWeight: "500"
                            }}>
                              {doc.status}
                            </span>
                          </td>
                          <td style={{ padding: "1rem", color: "#666" }}>
                            {doc.created_at ? new Date(doc.created_at).toLocaleDateString("sv-SE") : "-"}
                          </td>
                          <td style={{ padding: "1rem", color: "#666" }}>
                            {doc.predicted_accuracy ? `${doc.predicted_accuracy}%` : "-"}
                          </td>
                          <td style={{ padding: "1rem" }}>
                            <button
                              onClick={() => setSelectedDocument(doc)}
                              style={{
                                padding: "0.5rem 1rem",
                                background: "#7265cf",
                                color: "white",
                                border: "none",
                                borderRadius: "4px",
                                cursor: "pointer",
                                fontSize: "0.9rem",
                                fontWeight: "500",
                                transition: "background 0.2s"
                              }}
                              onMouseEnter={(e) => e.target.style.background = "#5a4db8"}
                              onMouseLeave={(e) => e.target.style.background = "#7265cf"}
                            >
                              Edit
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {selectedDocument && (
                <DocumentDetail 
                  document={selectedDocument} 
                  onClose={() => setSelectedDocument(null)}
                  onSave={fetchDocuments}
                />
              )}
            </div>
          </>
        )}

        {currentView === "scan-invoice" && (
          <ScanInvoice onBack={() => setCurrentView("overview")} />
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
