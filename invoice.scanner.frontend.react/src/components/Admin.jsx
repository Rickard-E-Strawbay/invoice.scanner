import React, { useContext, useState, useEffect } from "react";
import { AuthContext } from "../contexts/AuthContext";
import { getPlanName, clearPlanCache } from "../utils/planMapper";
import "./Dashboard.css";
import { API_BASE_URL } from "../utils/api";

function Admin() {
  const { user, isAdmin } = useContext(AuthContext);
  const [activeTab, setActiveTab] = useState("user-admin");
  // Company Admin state (for managing all companies)
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  // Company Admin form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingCompanyId, setEditingCompanyId] = useState(null);
  const [formData, setFormData] = useState({
    company_name: "",
    company_email: "",
    organization_id: "",
    company_enabled: true,
    price_plan_key: "10",
  });
  const [formError, setFormError] = useState(null);
  const [formLoading, setFormLoading] = useState(false);

  // User Admin state
  const [users, setUsers] = useState([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [usersError, setUsersError] = useState(null);
  const [showAddUserForm, setShowAddUserForm] = useState(false);
  const [editingUserId, setEditingUserId] = useState(null);
  const [userFormData, setUserFormData] = useState({
    email: "",
    name: "",
    role_key: 10,
    user_enabled: false,
    company_id: "",
  });
  const [userFormError, setUserFormError] = useState(null);
  const [userFormLoading, setUserFormLoading] = useState(false);
  const [companySearchInput, setCompanySearchInput] = useState("");
  const [showCompanyDropdown, setShowCompanyDropdown] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState(null);
  const [companyToDelete, setCompanyToDelete] = useState(null);
  const [passwordResetDialog, setPasswordResetDialog] = useState({
    open: false,
    message: "",
    type: "", // "success" or "error"
    email: "",
  });
  const [allRoles, setAllRoles] = useState([]);
  const [rolesLoading, setRolesLoading] = useState(false);

  const canAccessCompanyAdmin = user?.role_key === 1000;
  const canAccessUserAdmin = isAdmin();

  useEffect(() => {
    // Fetch roles on component mount
    fetchRoles();
    // Fetch data based on active tab
    if (activeTab === "user-admin" && (canAccessUserAdmin || canAccessCompanyAdmin)) {
      setUsers([]);
      setUsersLoading(true);
      fetchUsers();
    }
    // Fetch companies for company admin tab
    if (activeTab === "company-admin" && canAccessCompanyAdmin) {
      setCompanies([]);
      setLoading(true);
      fetchCompanies();
    }
    // PlansAndBilling handles its own data fetching
  }, [activeTab, canAccessCompanyAdmin, canAccessUserAdmin]);

  const fetchCompanies = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${API_BASE_URL}/auth/admin/companies`, {
        method: "GET",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch companies: ${response.status}`);
      }

      const data = await response.json();
      setCompanies(data.companies || []);
      
      // Also fetch and cache plan names to avoid async rendering
      try {
        const plansResponse = await fetch(`${API_BASE_URL}/auth/plans`, {
          credentials: "include",
        });
        if (plansResponse.ok) {
          const plansData = await plansResponse.json();
          const cache = {};
          plansData.plans.forEach(plan => {
            cache[plan.price_plan_key] = plan.plan_name;
          });
          setPlanNameCache(cache);
        }
      } catch (planErr) {
        console.error("Error fetching plans:", planErr);
      }
    } catch (err) {
      console.error("Error fetching companies:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchRoles = async () => {
    try {
      setRolesLoading(true);
      const response = await fetch(`${API_BASE_URL}/auth/roles`, {
        method: "GET",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch roles");
      }

      const data = await response.json();
      setAllRoles(data.roles || []);
    } catch (err) {
      console.error("Error fetching roles:", err);
    } finally {
      setRolesLoading(false);
    }
  };

  const fetchUsers = async () => {
    try {
      setUsersLoading(true);
      setUsersError(null);
      const response = await fetch(`${API_BASE_URL}/auth/admin/users`, {
        method: "GET",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch users");
      }

      const data = await response.json();
      setUsers(data.users || []);
    } catch (err) {
      console.error("Error fetching users:", err);
      setUsersError(err.message);
    } finally {
      setUsersLoading(false);
    }
  };

  const handleFormChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : name === "price_plan_key" ? parseInt(value) : value,
    }));
  };

  const handleUserFormChange = (e) => {
    const { name, value, type, checked } = e.target;
    setUserFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : name === "role_key" ? parseInt(value) : value,
    }));
  };

  const handleCompanySearch = (e) => {
    const value = e.target.value;
    setCompanySearchInput(value);
    setShowCompanyDropdown(true);
  };

  const handleSelectCompany = (company) => {
    setUserFormData((prev) => ({
      ...prev,
      company_id: company.id,
    }));
    setCompanySearchInput(company.company_name);
    setShowCompanyDropdown(false);
  };

  const filteredCompanies = companies.filter((company) =>
    company.company_name.toLowerCase().includes(companySearchInput.toLowerCase())
  );

  const getSelectedCompany = () => {
    return companies.find((c) => c.id === userFormData.company_id);
  };

  const getAvailableRoles = () => {
    if (!allRoles || allRoles.length === 0) {
      // Fallback while loading
      return [{ key: 10, name: "Company User" }];
    }

    // Filter roles based on user permissions and company selection
    let availableRoles = allRoles.filter(role => role.key === 10); // Always include Company User
    
    // Add Company Admin only if current user is Strawbay Admin
    if (user?.role_key === 1000) {
      const companyAdmin = allRoles.find(r => r.key === 50);
      if (companyAdmin) {
        availableRoles.push(companyAdmin);
      }
    }
    
    // Add Strawbay Admin only if selected company is Strawbay AB
    if (getSelectedCompany()?.company_name === "Strawbay AB") {
      const strawbayAdmin = allRoles.find(r => r.key === 1000);
      if (strawbayAdmin) {
        availableRoles.push(strawbayAdmin);
      }
    }
    
    return availableRoles;
  };

  const handleAddCompany = async (e) => {
    e.preventDefault();
    setFormError(null);

    if (!formData.company_name.trim()) {
      setFormError("Company name is required");
      return;
    }
    if (!formData.company_email.trim()) {
      setFormError("Company email is required");
      return;
    }
    if (!formData.organization_id.trim()) {
      setFormError("Organization ID is required");
      return;
    }

    try {
      setFormLoading(true);
      const method = editingCompanyId ? "PUT" : "POST";
      const url = editingCompanyId 
        ? `${API_BASE_URL}/auth/admin/companies/${editingCompanyId}`
        : `${API_BASE_URL}/auth/admin/companies`;

      const response = await fetch(url, {
        method: method,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `Failed to ${editingCompanyId ? "update" : "add"} company`);
      }

      // Ensure price_plan_key is present in the returned data
      const companyData = {
        ...data.company,
        price_plan_key: data.company.price_plan_key || parseInt(formData.price_plan_key)
      };

      if (editingCompanyId) {
        // Update existing company in list
        setCompanies(companies.map((c) => (c.id === editingCompanyId ? companyData : c)));
      } else {
        // Add new company to list
        setCompanies([...companies, companyData]);
      }

      setFormData({
        company_name: "",
        company_email: "",
        organization_id: "",
        company_enabled: true,
        price_plan_key: "10",
      });
      setShowAddForm(false);
      setEditingCompanyId(null);
      setFormError(null);
    } catch (err) {
      console.error("Error saving company:", err);
      setFormError(err.message);
    } finally {
      setFormLoading(false);
    }
  };

  const handleEditCompany = (company) => {
    setEditingCompanyId(company.id);
    setFormData({
      company_name: company.company_name,
      company_email: company.company_email,
      organization_id: company.organization_id,
      company_enabled: company.company_enabled,
      price_plan_key: String(company.price_plan_key || 10),
    });
    setShowAddForm(true);
    setFormError(null);
  };

  const handleCancelEdit = () => {
    setShowAddForm(false);
    setEditingCompanyId(null);
    setFormData({
      company_name: "",
      company_email: "",
      organization_id: "",
      company_enabled: true,
      price_plan_key: "10",
    });
    setFormError(null);
  };

  const handleCancelUserEdit = () => {
    setShowAddUserForm(false);
    setEditingUserId(null);
    setUserFormData({
      email: "",
      name: "",
      role_key: 10,
      user_enabled: false,
      company_id: "",
    });
    setUserFormError(null);
    setCompanySearchInput("");
    setShowCompanyDropdown(false);
  };

  const handleToggleCompanyStatus = async (companyId, currentStatus) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/admin/companies/${companyId}`, {
        method: "PUT",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          company_enabled: !currentStatus,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to update company status");
      }

      // Update the company in the list
      setCompanies(companies.map((c) => (c.id === companyId ? data.company : c)));
    } catch (err) {
      console.error("Error updating company status:", err);
      alert(`Error: ${err.message}`);
    }
  };

  const handleToggleUserStatus = async (userId, currentStatus) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/admin/users/${userId}`, {
        method: "PUT",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_enabled: !currentStatus,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to update user status");
      }

      // Update the user in the list
      setUsers(users.map((u) => (u.id === userId ? data.user : u)));
    } catch (err) {
      console.error("Error updating user status:", err);
      alert(`Error: ${err.message}`);
    }
  };

  const handleAddUser = async (e) => {
    e.preventDefault();
    setUserFormError(null);

    if (!userFormData.email.trim()) {
      setUserFormError("Email is required");
      return;
    }
    if (!userFormData.name.trim()) {
      setUserFormError("Name is required");
      return;
    }
    if (!userFormData.company_id) {
      setUserFormError("Company is required");
      return;
    }

    try {
      setUserFormLoading(true);
      const method = editingUserId ? "PUT" : "POST";
      const url = editingUserId 
        ? `${API_BASE_URL}/auth/admin/users/${editingUserId}`
        : `${API_BASE_URL}/auth/admin/users`;

      const response = await fetch(url, {
        method: method,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: userFormData.email,
          name: userFormData.name,
          role_key: userFormData.role_key,
          user_enabled: userFormData.user_enabled,
          company_id: userFormData.company_id,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `Failed to ${editingUserId ? "update" : "add"} user`);
      }

      if (editingUserId) {
        // Update existing user in list
        setUsers(users.map((u) => (u.id === editingUserId ? data.user : u)));
      } else {
        // Add new user to list - include company_name from companies list
        const selectedCompany = companies.find((c) => c.id === userFormData.company_id);
        const userWithCompany = {
          ...data.user,
          company_name: selectedCompany?.company_name || "",
        };
        setUsers([...users, userWithCompany]);
      }

      setUserFormData({
        email: "",
        name: "",
        role_key: 10,
        user_enabled: false,
        company_id: "",
      });
      setShowAddUserForm(false);
      setEditingUserId(null);
      setUserFormError(null);
    } catch (err) {
      console.error("Error saving user:", err);
      setUserFormError(err.message);
    } finally {
      setUserFormLoading(false);
    }
  };

  const handleEditUser = (user) => {
    setEditingUserId(user.id);
    setUserFormData({
      email: user.email,
      name: user.name,
      role_key: user.role_key,
      user_enabled: user.user_enabled,
      company_id: "",
    });
    setCompanySearchInput(user.company_name || "");
    setShowAddUserForm(true);
    setUserFormError(null);
  };

  const handleDeleteUser = (userId, email) => {
    setUserToDelete({ id: userId, email: email });
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!userToDelete) return;

    try {
      const response = await fetch(`${API_BASE_URL}/auth/admin/users/${userToDelete.id}`, {
        method: "DELETE",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to delete user");
      }

      setUsers(users.filter((u) => u.id !== userToDelete.id));
      setDeleteDialogOpen(false);
      setUserToDelete(null);
    } catch (err) {
      console.error("Error deleting user:", err);
      alert(`Error: ${err.message}`);
    }
  };

  const handleCancelDelete = () => {
    setDeleteDialogOpen(false);
    setUserToDelete(null);
    setCompanyToDelete(null);
  };

  const handleSendPasswordReset = async (userId, userEmail) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/admin/users/${userId}/send-password-reset`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to send password reset email");
      }

      setPasswordResetDialog({
        open: true,
        message: `Password reset email sent to ${userEmail}`,
        type: "success",
        email: userEmail,
      });
    } catch (err) {
      console.error("Error sending password reset email:", err);
      setPasswordResetDialog({
        open: true,
        message: err.message,
        type: "error",
        email: userEmail,
      });
    }
  };

  const handleDeleteCompany = (companyId, companyName) => {
    setCompanyToDelete({ id: companyId, name: companyName });
    setDeleteDialogOpen(true);
  };

  const handleConfirmCompanyDelete = async () => {
    if (!companyToDelete) return;

    try {
      const response = await fetch(`${API_BASE_URL}/auth/admin/companies/${companyToDelete.id}`, {
        method: "DELETE",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to delete company");
      }

      setCompanies(companies.filter((c) => c.id !== companyToDelete.id));
      setDeleteDialogOpen(false);
      setCompanyToDelete(null);
    } catch (err) {
      console.error("Error deleting company:", err);
      alert(`Error: ${err.message}`);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleDateString("sv-SE");
  };

  const getEnabledBadge = (enabled) => {
    return enabled ? (
      <span style={{ color: "#10b981", fontWeight: "600" }}>✓ Enabled</span>
    ) : (
      <span style={{ color: "#ef4444", fontWeight: "600" }}>✗ Pending</span>
    );
  };

  // Cache for plan names fetched from backend
  const [planNameCache, setPlanNameCache] = useState({});

  const getPlanNameFromBackend = async (priceplankey) => {
    // Check if already in cache
    if (planNameCache[priceplankey]) {
      return planNameCache[priceplankey];
    }

    // Fetch from backend
    const name = await getPlanName(priceplankey);
    setPlanNameCache(prev => ({
      ...prev,
      [priceplankey]: name
    }));
    return name;
  };

  return (
    <>
      {deleteDialogOpen && (
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
            zIndex: 999,
          }}
          onClick={handleCancelDelete}
        />
      )}

      <dialog
        open={deleteDialogOpen}
        style={{
          padding: "0",
          border: "none",
          borderRadius: "8px",
          boxShadow: "0 10px 40px rgba(0,0,0,0.15)",
          maxWidth: "400px",
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          zIndex: 1000,
        }}
      >
        <div style={{ padding: "1.5rem" }}>
          {userToDelete ? (
            <>
              <h2 style={{ marginTop: 0, color: "#ef4444" }}>Delete User</h2>
              <p style={{ marginBottom: "1.5rem", color: "#666" }}>
                Are you sure you want to delete <strong>{userToDelete?.email}</strong>? This action cannot be undone.
              </p>
              <div style={{ display: "flex", gap: "1rem", justifyContent: "flex-end" }}>
                <button
                  onClick={handleCancelDelete}
                  style={{
                    padding: "0.75rem 1.5rem",
                    background: "#e5e7eb",
                    color: "#1a1a1a",
                    border: "none",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontWeight: "600",
                    fontSize: "0.95rem",
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmDelete}
                  style={{
                    padding: "0.75rem 1.5rem",
                    background: "#ef4444",
                    color: "white",
                    border: "none",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontWeight: "600",
                    fontSize: "0.95rem",
                  }}
                >
                  Delete
                </button>
              </div>
            </>
          ) : companyToDelete ? (
            <>
              <h2 style={{ marginTop: 0, color: "#ef4444" }}>Delete Company</h2>
              <p style={{ marginBottom: "1.5rem", color: "#666" }}>
                Are you sure you want to delete <strong>{companyToDelete?.name}</strong>? This action cannot be undone.
              </p>
              <div style={{ display: "flex", gap: "1rem", justifyContent: "flex-end" }}>
                <button
                  onClick={handleCancelDelete}
                  style={{
                    padding: "0.75rem 1.5rem",
                    background: "#e5e7eb",
                    color: "#1a1a1a",
                    border: "none",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontWeight: "600",
                    fontSize: "0.95rem",
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmCompanyDelete}
                  style={{
                    padding: "0.75rem 1.5rem",
                    background: "#ef4444",
                    color: "white",
                    border: "none",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontWeight: "600",
                    fontSize: "0.95rem",
                  }}
                >
                  Delete
                </button>
              </div>
            </>
          ) : null}
        </div>
      </dialog>

      <div className="content-header">
        <h1>Admin</h1>
      </div>

      <div className="tabs">
        <button
          className={`tab ${activeTab === "user-admin" ? "active" : ""}`}
          onClick={() => setActiveTab("user-admin")}
        >
          User Admin
        </button>
        {canAccessCompanyAdmin && (
          <button
            className={`tab ${activeTab === "company-admin" ? "active" : ""}`}
            onClick={() => setActiveTab("company-admin")}
          >
            Company Admin
          </button>
        )}
      </div>

      {activeTab === "user-admin" && (
        <div className="admin-section">
          <div style={{ padding: "2rem", background: "#ffffff", borderRadius: "8px", border: "1px solid #e8ecf1" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
              <div>
                <h2>User Admin</h2>
                <p>Manage all users in the system.</p>
              </div>
              <button
                onClick={() => {
                  if (showAddUserForm) {
                    handleCancelUserEdit();
                  } else {
                    setShowAddUserForm(true);
                  }
                }}
                style={{
                  padding: "0.75rem 1.5rem",
                  background: "#7265cf",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontWeight: "600",
                  fontSize: "0.95rem",
                }}
              >
                {showAddUserForm ? "Cancel" : "+ Add User"}
              </button>
            </div>

            {showAddUserForm && (
              <div style={{ marginBottom: "2rem", padding: "1.5rem", background: "#f5f7fa", borderRadius: "8px", border: "1px solid #e8ecf1" }}>
                <h3 style={{ marginTop: 0 }}>{editingUserId ? "Edit User" : "Add New User"}</h3>
                <form onSubmit={handleAddUser}>
                  <div style={{ marginBottom: "1rem" }}>
                    <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "500" }}>
                      Email
                    </label>
                    <input
                      type="email"
                      name="email"
                      value={userFormData.email}
                      onChange={handleUserFormChange}
                      placeholder="user@example.com"
                      disabled={editingUserId}
                      style={{
                        width: "100%",
                        padding: "0.75rem 1rem",
                        border: "1px solid #d0d0d0",
                        borderRadius: "6px",
                        fontSize: "0.95rem",
                        boxSizing: "border-box",
                        backgroundColor: editingUserId ? "#f0f0f0" : "white",
                      }}
                    />
                  </div>

                  <div style={{ marginBottom: "1rem" }}>
                    <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "500" }}>
                      Name
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={userFormData.name}
                      onChange={handleUserFormChange}
                      placeholder="e.g., John Doe"
                      style={{
                        width: "100%",
                        padding: "0.75rem 1rem",
                        border: "1px solid #d0d0d0",
                        borderRadius: "6px",
                        fontSize: "0.95rem",
                        boxSizing: "border-box",
                      }}
                    />
                  </div>

                  <div style={{ marginBottom: "1rem", display: "block", position: "relative" }}>
                    <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "500" }}>
                      Company
                    </label>
                    <input
                      type="text"
                      value={companySearchInput}
                      onChange={handleCompanySearch}
                      onFocus={() => setShowCompanyDropdown(true)}
                      placeholder="Search company..."
                      style={{
                        width: "100%",
                        padding: "0.75rem 1rem",
                        border: "1px solid #d0d0d0",
                        borderRadius: "6px",
                        fontSize: "0.95rem",
                        boxSizing: "border-box",
                        backgroundColor: "white",
                      }}
                    />
                    {showCompanyDropdown && companySearchInput && (
                      <div
                        style={{
                          position: "absolute",
                          top: "100%",
                          left: 0,
                          right: 0,
                          background: "white",
                          border: "1px solid #d0d0d0",
                          borderTop: "none",
                          borderRadius: "0 0 6px 6px",
                          maxHeight: "200px",
                          overflowY: "auto",
                          zIndex: 10,
                        }}
                      >
                        {filteredCompanies.length > 0 ? (
                          filteredCompanies.map((company) => (
                            <div
                              key={company.id}
                              onClick={() => handleSelectCompany(company)}
                              style={{
                                padding: "0.75rem 1rem",
                                cursor: "pointer",
                                borderBottom: "1px solid #f0f0f0",
                                backgroundColor: userFormData.company_id === company.id ? "#f5f7fa" : "white",
                                transition: "background-color 0.2s",
                              }}
                              onMouseEnter={(e) => {
                                e.target.style.backgroundColor = "#f5f7fa";
                              }}
                              onMouseLeave={(e) => {
                                e.target.style.backgroundColor = userFormData.company_id === company.id ? "#f5f7fa" : "white";
                              }}
                            >
                              {company.company_name}
                            </div>
                          ))
                        ) : (
                          <div style={{ padding: "0.75rem 1rem", color: "#999" }}>
                            No companies found
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div style={{ marginBottom: "1rem" }}>
                    <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "500" }}>
                      Role
                    </label>
                    <select
                      name="role_key"
                      value={userFormData.role_key}
                      onChange={handleUserFormChange}
                      disabled={!userFormData.company_id && !editingUserId}
                      style={{
                        width: "100%",
                        padding: "0.75rem 1rem",
                        border: "1px solid #d0d0d0",
                        borderRadius: "6px",
                        fontSize: "0.95rem",
                        boxSizing: "border-box",
                        backgroundColor: (!userFormData.company_id && !editingUserId) ? "#f0f0f0" : "white",
                        color: (!userFormData.company_id && !editingUserId) ? "#999" : "#1a1a1a",
                      }}
                    >
                      {getAvailableRoles().map((role) => (
                        <option key={role.key} value={role.key}>
                          {role.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div style={{ marginBottom: "1.5rem", display: "flex", alignItems: "center" }}>
                    <input
                      type="checkbox"
                      id="user_enabled"
                      name="user_enabled"
                      checked={userFormData.user_enabled}
                      onChange={handleUserFormChange}
                      style={{
                        width: "18px",
                        height: "18px",
                        cursor: "pointer",
                        marginRight: "0.5rem",
                      }}
                    />
                    <label htmlFor="user_enabled" style={{ cursor: "pointer", fontWeight: "500", marginBottom: 0 }}>
                      Enable user
                    </label>
                  </div>

                  {userFormError && (
                    <div style={{ marginBottom: "1rem", padding: "1rem", background: "#fee", borderRadius: "6px", borderLeft: "4px solid #ef4444", color: "#991b1b" }}>
                      {userFormError}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={userFormLoading}
                    style={{
                      padding: "0.75rem 1.5rem",
                      background: "#10b981",
                      color: "white",
                      border: "none",
                      borderRadius: "6px",
                      cursor: userFormLoading ? "not-allowed" : "pointer",
                      fontWeight: "600",
                      fontSize: "0.95rem",
                      opacity: userFormLoading ? 0.7 : 1,
                    }}
                  >
                    {userFormLoading ? (editingUserId ? "Updating..." : "Adding...") : (editingUserId ? "Update User" : "Add User")}
                  </button>
                </form>
              </div>
            )}

            {usersError && (
              <div style={{ marginTop: "1rem", padding: "1rem", background: "#fee", borderRadius: "6px", borderLeft: "4px solid #ef4444", color: "#991b1b" }}>
                Error: {usersError}
              </div>
            )}

            {usersLoading && (
              <div style={{ marginTop: "1rem", padding: "1rem", background: "#f5f7fa", borderRadius: "6px", color: "#666" }}>
                Loading users...
              </div>
            )}

            {!usersLoading && users.length === 0 && (
              <div style={{ marginTop: "1rem", padding: "1rem", background: "#f5f7fa", borderRadius: "6px", color: "#666" }}>
                No users found.
              </div>
            )}

            {!usersLoading && users.length > 0 && (
              <div style={{ marginTop: "1.5rem", overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.95rem" }}>
                  <thead>
                    <tr style={{ borderBottom: "2px solid #e8ecf1", background: "#f5f7fa" }}>
                      <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600", color: "#1a1a1a" }}>Email</th>
                      <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600", color: "#1a1a1a" }}>Name</th>
                      <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600", color: "#1a1a1a" }}>Company</th>
                      <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600", color: "#1a1a1a" }}>Role</th>
                      <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600", color: "#1a1a1a" }}>Status</th>
                      <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600", color: "#1a1a1a" }}>Actions</th>
                      <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600", color: "#1a1a1a" }}>Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((user) => (
                      <tr key={user.id} style={{ borderBottom: "1px solid #e8ecf1" }}>
                        <td 
                          onClick={() => handleEditUser(user)}
                          style={{ padding: "1rem", color: "#1a1a1a", fontWeight: "500", cursor: "pointer", textDecoration: "underline", textDecorationColor: "#7265cf" }}
                        >
                          {user.email}
                        </td>
                        <td style={{ padding: "1rem", color: "#666" }}>{user.name || "-"}</td>
                        <td style={{ padding: "1rem", color: "#666" }}>{user.company_name || "-"}</td>
                        <td style={{ padding: "1rem", color: "#666" }}>
                          {allRoles.find(r => r.key === user.role_key)?.name || "Unknown"}
                        </td>
                        <td style={{ padding: "1rem" }}>
                          {user.company_enabled === false ? (
                            <span style={{ color: "#999", fontWeight: "600" }}>✗ Company Pending</span>
                          ) : user.user_enabled ? (
                            <span style={{ color: "#10b981", fontWeight: "600" }}>✓ Enabled</span>
                          ) : (
                            <span style={{ color: "#ef4444", fontWeight: "600" }}>✗ Pending</span>
                          )}
                        </td>
                        <td style={{ padding: "1rem", display: "flex", gap: "0.5rem" }}>
                          <button
                            onClick={() => handleToggleUserStatus(user.id, user.user_enabled)}
                            disabled={user.company_enabled === false}
                            style={{
                              padding: "0.35rem 0.75rem",
                              background: user.company_enabled === false ? "#ccc" : "#7265cf",
                              color: "white",
                              border: "none",
                              borderRadius: "4px",
                              cursor: user.company_enabled === false ? "not-allowed" : "pointer",
                              fontWeight: "500",
                              fontSize: "0.8rem",
                              transition: "all 0.2s ease",
                              opacity: user.company_enabled === false ? 0.6 : 1,
                            }}
                            onMouseEnter={(e) => {
                              if (user.company_enabled !== false) {
                                e.target.style.opacity = "0.8";
                              }
                            }}
                            onMouseLeave={(e) => {
                              if (user.company_enabled !== false) {
                                e.target.style.opacity = "1";
                              }
                            }}
                          >
                            {user.user_enabled ? "Disable" : "Enable"}
                          </button>
                          <button
                            onClick={() => handleSendPasswordReset(user.id, user.email)}
                            disabled={!user.user_enabled}
                            style={{
                              padding: "0.35rem 0.5rem",
                              background: "transparent",
                              border: "none",
                              borderRadius: "4px",
                              cursor: user.user_enabled ? "pointer" : "not-allowed",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              transition: "background-color 0.2s, opacity 0.2s",
                              opacity: user.user_enabled ? 1 : 0.4,
                            }}
                            onMouseEnter={(e) => {
                              if (user.user_enabled) {
                                e.target.style.backgroundColor = "#fef3c7";
                              }
                            }}
                            onMouseLeave={(e) => {
                              if (user.user_enabled) {
                                e.target.style.backgroundColor = "transparent";
                              }
                            }}
                            title={user.user_enabled ? "Send password reset email" : "User must be enabled"}
                          >
                            <svg
                              width="18"
                              height="18"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke={user.user_enabled ? "#f59e0b" : "#ccc"}
                              strokeWidth="2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            >
                              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                              <polyline points="22,6 12,13 2,6"></polyline>
                            </svg>
                          </button>
                          <button
                            onClick={() => handleDeleteUser(user.id, user.email)}
                            style={{
                              padding: "0.35rem 0.5rem",
                              background: "transparent",
                              border: "none",
                              borderRadius: "4px",
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              transition: "background-color 0.2s",
                            }}
                            onMouseEnter={(e) => {
                              e.target.style.backgroundColor = "#fee";
                            }}
                            onMouseLeave={(e) => {
                              e.target.style.backgroundColor = "transparent";
                            }}
                            title="Delete user"
                          >
                            <svg
                              width="18"
                              height="18"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="#ef4444"
                              strokeWidth="2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            >
                              <polyline points="3 6 5 6 21 6"></polyline>
                              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                              <line x1="10" y1="11" x2="10" y2="17"></line>
                              <line x1="14" y1="11" x2="14" y2="17"></line>
                            </svg>
                          </button>
                        </td>
                        <td style={{ padding: "1rem", color: "#666" }}>{formatDate(user.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === "company-admin" && canAccessCompanyAdmin && (
        <div className="admin-section">
          <div style={{ padding: "2rem", background: "#ffffff", borderRadius: "8px", border: "1px solid #e8ecf1" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
              <div>
                <h2>Company Admin</h2>
                <p>Manage all companies in the system.</p>
              </div>
              <button
                onClick={() => {
                  if (showAddForm) {
                    handleCancelEdit();
                  } else {
                    setShowAddForm(true);
                  }
                }}
                style={{
                  padding: "0.75rem 1.5rem",
                  background: "#7265cf",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontWeight: "600",
                  fontSize: "0.95rem",
                }}
              >
                {showAddForm ? "Cancel" : "+ Add Company"}
              </button>
            </div>

            {showAddForm && (
              <div style={{ marginBottom: "2rem", padding: "1.5rem", background: "#f5f7fa", borderRadius: "8px", border: "1px solid #e8ecf1" }}>
                <h3 style={{ marginTop: 0 }}>{editingCompanyId ? "Edit Company" : "Add New Company"}</h3>
                <form onSubmit={handleAddCompany}>
                  <div style={{ marginBottom: "1rem" }}>
                    <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "500" }}>
                      Company Name
                    </label>
                    <input
                      type="text"
                      name="company_name"
                      value={formData.company_name}
                      onChange={handleFormChange}
                      placeholder="e.g., Acme Corporation"
                      style={{
                        width: "100%",
                        padding: "0.75rem 1rem",
                        border: "1px solid #d0d0d0",
                        borderRadius: "6px",
                        fontSize: "0.95rem",
                        boxSizing: "border-box",
                      }}
                    />
                  </div>

                  <div style={{ marginBottom: "1rem" }}>
                    <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "500" }}>
                      Company Email
                    </label>
                    <input
                      type="email"
                      name="company_email"
                      value={formData.company_email}
                      onChange={handleFormChange}
                      placeholder="e.g., info@acme.com"
                      style={{
                        width: "100%",
                        padding: "0.75rem 1rem",
                        border: "1px solid #d0d0d0",
                        borderRadius: "6px",
                        fontSize: "0.95rem",
                        boxSizing: "border-box",
                      }}
                    />
                  </div>

                  <div style={{ marginBottom: "1rem" }}>
                    <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "500" }}>
                      Organization ID
                    </label>
                    <input
                      type="text"
                      name="organization_id"
                      value={formData.organization_id}
                      onChange={handleFormChange}
                      placeholder="e.g., 556000-1234 (Swedish Org. No.)"
                      style={{
                        width: "100%",
                        padding: "0.75rem 1rem",
                        border: "1px solid #d0d0d0",
                        borderRadius: "6px",
                        fontSize: "0.95rem",
                        boxSizing: "border-box",
                      }}
                    />
                  </div>

                  <div style={{ marginBottom: "1rem" }}>
                    <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "500" }}>
                      Plan
                    </label>
                    <select
                      name="price_plan_key"
                      value={formData.price_plan_key}
                      onChange={handleFormChange}
                      style={{
                        width: "100%",
                        padding: "0.75rem 1rem",
                        border: "1px solid #d0d0d0",
                        borderRadius: "6px",
                        fontSize: "0.95rem",
                        boxSizing: "border-box",
                        backgroundColor: "#ffffff",
                        cursor: "pointer",
                      }}
                    >
                      <option value="10">Starter</option>
                      <option value="30">Medium</option>
                      <option value="40">Enterprise</option>
                      <option value="1000">Admin</option>
                    </select>
                  </div>

                  <div style={{ marginBottom: "1.5rem", display: "flex", alignItems: "center" }}>
                    <input
                      type="checkbox"
                      id="company_enabled"
                      name="company_enabled"
                      checked={formData.company_enabled}
                      onChange={handleFormChange}
                      style={{
                        width: "18px",
                        height: "18px",
                        cursor: "pointer",
                        marginRight: "0.5rem",
                      }}
                    />
                    <label htmlFor="company_enabled" style={{ cursor: "pointer", fontWeight: "500", marginBottom: 0 }}>
                      Enable company
                    </label>
                  </div>

                  {formError && (
                    <div style={{ marginBottom: "1rem", padding: "1rem", background: "#fee", borderRadius: "6px", borderLeft: "4px solid #ef4444", color: "#991b1b" }}>
                      {formError}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={formLoading}
                    style={{
                      padding: "0.75rem 1.5rem",
                      background: "#10b981",
                      color: "white",
                      border: "none",
                      borderRadius: "6px",
                      cursor: formLoading ? "not-allowed" : "pointer",
                      fontWeight: "600",
                      fontSize: "0.95rem",
                      opacity: formLoading ? 0.7 : 1,
                    }}
                  >
                    {formLoading ? (editingCompanyId ? "Updating..." : "Adding...") : (editingCompanyId ? "Update Company" : "Add Company")}
                  </button>
                </form>
              </div>
            )}

            {error && (
              <div style={{ marginTop: "1rem", padding: "1rem", background: "#fee", borderRadius: "6px", borderLeft: "4px solid #ef4444", color: "#991b1b" }}>
                Error: {error}
              </div>
            )}

            {loading && (
              <div style={{ marginTop: "1rem", padding: "1rem", background: "#f5f7fa", borderRadius: "6px", color: "#666" }}>
                Loading companies...
              </div>
            )}

            {!loading && companies.length === 0 && (
              <div style={{ marginTop: "1rem", padding: "1rem", background: "#f5f7fa", borderRadius: "6px", color: "#666" }}>
                No companies found.
              </div>
            )}

            {!loading && companies.length > 0 && (
              <div style={{ marginTop: "1.5rem", overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.95rem" }}>
                  <thead>
                    <tr style={{ borderBottom: "2px solid #e8ecf1", background: "#f5f7fa" }}>
                      <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600", color: "#1a1a1a" }}>Company Name</th>
                      <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600", color: "#1a1a1a" }}>Organization ID</th>
                      <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600", color: "#1a1a1a" }}>Email</th>
                      <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600", color: "#1a1a1a" }}>Plan</th>
                      <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600", color: "#1a1a1a" }}>Status</th>
                      <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600", color: "#1a1a1a" }}>Action</th>
                      <th style={{ padding: "1rem", textAlign: "left", fontWeight: "600", color: "#1a1a1a" }}>Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {companies.map((company) => (
                      <tr key={company.id} style={{ borderBottom: "1px solid #e8ecf1" }}>
                        <td 
                          onClick={() => handleEditCompany(company)}
                          style={{ padding: "1rem", color: "#1a1a1a", fontWeight: "500", cursor: "pointer", textDecoration: "underline", textDecorationColor: "#7265cf" }}
                        >
                          {company.company_name}
                        </td>
                        <td style={{ padding: "1rem", color: "#666" }}>{company.organization_id || "-"}</td>
                        <td style={{ padding: "1rem", color: "#666" }}>{company.company_email || "-"}</td>
                        <td style={{ padding: "1rem", color: "#1a1a1a", fontWeight: "500" }}>{planNameCache[company.price_plan_key] || "Unknown"}</td>
                        <td style={{ padding: "1rem" }}>{getEnabledBadge(company.company_enabled)}</td>
                        <td style={{ padding: "1rem", display: "flex", gap: "0.5rem", alignItems: "center" }}>
                          <button
                            onClick={() => handleToggleCompanyStatus(company.id, company.company_enabled)}
                            style={{
                              padding: "0.35rem 0.75rem",
                              background: "#7265cf",
                              color: "white",
                              border: "none",
                              borderRadius: "4px",
                              cursor: "pointer",
                              fontWeight: "500",
                              fontSize: "0.8rem",
                              transition: "all 0.2s ease",
                            }}
                            onMouseEnter={(e) => {
                              e.target.style.opacity = "0.8";
                            }}
                            onMouseLeave={(e) => {
                              e.target.style.opacity = "1";
                            }}
                          >
                            {company.company_enabled ? "Disable" : "Enable"}
                          </button>
                          <button
                            onClick={() => handleDeleteCompany(company.id, company.company_name)}
                            style={{
                              padding: "0.35rem 0.5rem",
                              background: "transparent",
                              border: "none",
                              borderRadius: "4px",
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              transition: "background-color 0.2s",
                            }}
                            onMouseEnter={(e) => {
                              e.target.style.backgroundColor = "#fee";
                            }}
                            onMouseLeave={(e) => {
                              e.target.style.backgroundColor = "transparent";
                            }}
                            title="Delete company"
                          >
                            <svg
                              width="18"
                              height="18"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="#ef4444"
                              strokeWidth="2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            >
                              <polyline points="3 6 5 6 21 6"></polyline>
                              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                              <line x1="10" y1="11" x2="10" y2="17"></line>
                              <line x1="14" y1="11" x2="14" y2="17"></line>
                            </svg>
                          </button>
                        </td>
                        <td style={{ padding: "1rem", color: "#666" }}>{formatDate(company.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === "company-admin" && !canAccessCompanyAdmin && (
        <div className="admin-section">
          <div style={{ padding: "2rem", background: "#ffffff", borderRadius: "8px", border: "1px solid #e8ecf1" }}>
            <h2>Access Denied</h2>
            <p>You do not have permission to access Company Admin features.</p>
            <p>Only Strawbay Admins can manage companies.</p>
          </div>
        </div>
      )}

      {passwordResetDialog.open && (
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
            zIndex: 999,
          }}
          onClick={() => setPasswordResetDialog({ ...passwordResetDialog, open: false })}
        />
      )}

      <dialog
        open={passwordResetDialog.open}
        style={{
          padding: "0",
          border: "none",
          borderRadius: "8px",
          boxShadow: "0 10px 40px rgba(0,0,0,0.15)",
          maxWidth: "400px",
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          zIndex: 1000,
        }}
      >
        <div style={{ padding: "1.5rem" }}>
          <h2 style={{ marginTop: 0, color: passwordResetDialog.type === "success" ? "#10b981" : "#ef4444" }}>
            {passwordResetDialog.type === "success" ? "Email Sent" : "Error"}
          </h2>
          <p style={{ marginBottom: "1.5rem", color: "#666" }}>
            {passwordResetDialog.message}
          </p>
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              onClick={() => setPasswordResetDialog({ ...passwordResetDialog, open: false })}
              style={{
                padding: "0.75rem 1.5rem",
                background: passwordResetDialog.type === "success" ? "#10b981" : "#ef4444",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
                fontWeight: "600",
                fontSize: "0.95rem",
              }}
            >
              OK
            </button>
          </div>
        </div>
      </dialog>
    </>
  );
}

export default Admin;
