"use client";
import ProtectedRoute from "@/lib/auth/ProtectedRoute";
import { useAuth } from "@/lib/auth/AuthContext";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function Dashboard() {
  const { logout, token } = useAuth();
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [activeMenu, setActiveMenu] = useState("dashboard");
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [editingUser, setEditingUser] = useState<any>(null);
  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("");
  const [userMessage, setUserMessage] = useState("");

  useEffect(() => {
    if (token) {
      fetch("http://localhost:8000/api/v1/users/me", {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => res.json())
        .then((data) => {
          setUser(data);
          if (data.role === "admin") {
            fetch("http://localhost:8000/api/v1/users/audit-logs", {
              headers: { Authorization: `Bearer ${token}` },
            })
              .then((res) => res.json())
              .then((logs) => setAuditLogs(Array.isArray(logs) ? logs : []));

            fetch("http://localhost:8000/api/v1/users/", {
              headers: { Authorization: `Bearer ${token}` },
            })
              .then((res) => res.json())
              .then((data) => setUsers(Array.isArray(data) ? data : []));
          }
        });
    }
  }, [token]);

  const isAdmin = user?.role === "admin";
  const isLeadership = user?.role === "leadership";
  const isManager = user?.role === "manager";

  const canManageUsers = isAdmin;
  const canViewReports = isAdmin || isLeadership || isManager;
  const canViewAlerts = isAdmin || isLeadership || isManager;
  const canViewSettings = isAdmin;

  const roleColor: Record<string, string> = {
    admin: "#f87171",
    leadership: "#fbbf24",
    manager: "#60a5fa",
    employee: "#34d399",
    leader: "#a78bfa",
  };

  const handleEdit = (u: any) => {
    setEditingUser(u);
    setNewName(u.full_name);
    setNewRole(u.role);
    setUserMessage("");
  };

  const handleSave = async () => {
    if (!editingUser) return;
    const res = await fetch(`http://localhost:8000/api/v1/users/${editingUser.id}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ full_name: newName, role: newRole }),
    });
    if (res.ok) {
      const updated = await res.json();
      setUsers(users.map((u) => (u.id === updated.id ? updated : u)));
      setEditingUser(null);
      setUserMessage("✅ User updated successfully!");
    } else {
      setUserMessage("❌ Failed to update user");
    }
  };

  const handleDisable = async (u: any) => {
    if (!confirm(`Disable ${u.full_name}?`)) return;
    const res = await fetch(`http://localhost:8000/api/v1/users/${u.id}/disable`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      const updated = await res.json();
      setUsers(users.map((x) => (x.id === updated.id ? updated : x)));
      setUserMessage(`✅ ${u.full_name} has been disabled`);
    }
  };

  const menuItems = [
    { id: "dashboard", icon: "🏠", label: "Dashboard", show: true },
    { id: "activity", icon: "📋", label: "Recent Activity", show: true },
    { id: "alerts", icon: "🔔", label: "View Alerts", show: canViewAlerts },
    { id: "users", icon: "👥", label: "Manage Users", show: canManageUsers },
    { id: "reports", icon: "📊", label: "View Reports", show: canViewReports },
    { id: "audit", icon: "🔍", label: "Audit Logs", show: isAdmin },
    { id: "settings", icon: "⚙️", label: "Settings", show: canViewSettings },
    { id: "profile", icon: "👤", label: "My Profile", show: true },
  ];

  const renderContent = () => {
    switch (activeMenu) {
      case "dashboard":
        return (
          <div>
            <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>
              Welcome Back{user ? `, ${user.full_name}` : ""} 👋
            </h2>
            <p style={{ color: "#64748b", marginTop: "8px", fontSize: "16px", marginBottom: "32px" }}>
              Security Monitoring Dashboard · {new Date().toDateString()}
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "24px", marginBottom: "32px" }}>
              {[
                { label: "Total Alerts", value: "0", color: "#f87171", icon: "🚨" },
                { label: "Active Users", value: "1", color: "#34d399", icon: "👥" },
                { label: "System Status", value: "Online", color: "#34d399", icon: "✅" },
              ].map((stat) => (
                <div key={stat.label} style={{
                  backgroundColor: "#1a1a2e",
                  border: "1px solid #2a2a4a",
                  borderRadius: "16px",
                  padding: "28px",
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <p style={{ color: "#94a3b8", margin: 0, fontSize: "14px" }}>{stat.label}</p>
                    <span style={{ fontSize: "24px" }}>{stat.icon}</span>
                  </div>
                  <p style={{ fontSize: "40px", fontWeight: "bold", color: stat.color, margin: "12px 0 0" }}>
                    {stat.value}
                  </p>
                </div>
              ))}
            </div>
            {user && (
              <div style={{
                backgroundColor: "#1a1a2e",
                border: "1px solid #2a2a4a",
                borderRadius: "16px",
                padding: "24px",
              }}>
                <h3 style={{ fontSize: "16px", fontWeight: "bold", marginBottom: "12px", marginTop: 0, color: "#94a3b8" }}>
                  🔐 Your Permissions
                </h3>
                <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
                  {[
                    { label: "View Alerts", allowed: canViewAlerts },
                    { label: "Manage Users", allowed: canManageUsers },
                    { label: "View Reports", allowed: canViewReports },
                    { label: "Settings", allowed: canViewSettings },
                  ].map((perm) => (
                    <span key={perm.label} style={{
                      padding: "6px 14px",
                      borderRadius: "20px",
                      fontSize: "13px",
                      fontWeight: "bold",
                      backgroundColor: perm.allowed ? "#14532d" : "#1f2937",
                      color: perm.allowed ? "#34d399" : "#475569",
                      border: `1px solid ${perm.allowed ? "#16a34a" : "#374151"}`,
                    }}>
                      {perm.allowed ? "✅" : "🔒"} {perm.label}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        );

      case "activity":
        return (
          <div>
            <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 24px" }}>📋 Recent Activity</h2>
            <div style={{
              backgroundColor: "#1a1a2e",
              border: "1px solid #2a2a4a",
              borderRadius: "16px",
              padding: "28px",
            }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {[
                  { icon: "✅", text: "User logged in successfully", time: "Just now" },
                  { icon: "🔑", text: "JWT authentication active", time: "2 min ago" },
                  { icon: "🚀", text: "Backend connected", time: "5 min ago" },
                  { icon: "👥", text: "User management accessed", time: "10 min ago" },
                  { icon: "🔒", text: "Role-based access enforced", time: "15 min ago" },
                ].map((item) => (
                  <div key={item.text} style={{
                    backgroundColor: "#0f0f1a",
                    border: "1px solid #2a2a4a",
                    borderRadius: "10px",
                    padding: "14px 18px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}>
                    <span>{item.icon} {item.text}</span>
                    <span style={{ color: "#475569", fontSize: "13px" }}>{item.time}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );

      case "users":
        return (
          <div>
            <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>👥 User Management</h2>
            <p style={{ color: "#64748b", marginBottom: "24px" }}>Manage users, roles and access</p>

            {/* Edit Modal */}
            {editingUser && (
              <div style={{
                position: "fixed",
                top: 0, left: 0, right: 0, bottom: 0,
                backgroundColor: "rgba(0,0,0,0.7)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 1000,
              }}>
                <div style={{
                  backgroundColor: "#1a1a2e",
                  border: "1px solid #2a2a4a",
                  borderRadius: "16px",
                  padding: "32px",
                  width: "400px",
                }}>
                  <h3 style={{ margin: "0 0 24px", fontSize: "20px" }}>Edit User</h3>
                  <label style={{ color: "#94a3b8", fontSize: "14px" }}>Full Name</label>
                  <input
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    style={{
                      width: "100%", padding: "12px",
                      marginTop: "8px", marginBottom: "16px",
                      backgroundColor: "#0f0f1a",
                      border: "1px solid #2a2a4a",
                      borderRadius: "8px", color: "#fff",
                      fontSize: "15px", boxSizing: "border-box" as const,
                    }}
                  />
                  <label style={{ color: "#94a3b8", fontSize: "14px" }}>Role</label>
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    style={{
                      width: "100%", padding: "12px",
                      marginTop: "8px", marginBottom: "24px",
                      backgroundColor: "#0f0f1a",
                      border: "1px solid #2a2a4a",
                      borderRadius: "8px", color: "#fff",
                      fontSize: "15px", boxSizing: "border-box" as const,
                    }}
                  >
                    {["admin", "leadership", "manager", "employee"].map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                  <div style={{ display: "flex", gap: "12px" }}>
                    <button onClick={handleSave} style={{
                      flex: 1, padding: "12px",
                      backgroundColor: "#7c3aed", color: "#fff",
                      border: "none", borderRadius: "8px",
                      cursor: "pointer", fontWeight: "bold",
                    }}>Save</button>
                    <button onClick={() => setEditingUser(null)} style={{
                      flex: 1, padding: "12px",
                      backgroundColor: "#374151", color: "#fff",
                      border: "none", borderRadius: "8px",
                      cursor: "pointer", fontWeight: "bold",
                    }}>Cancel</button>
                  </div>
                </div>
              </div>
            )}

            {/* Message */}
            {userMessage && (
              <div style={{
                padding: "12px 20px", borderRadius: "10px", marginBottom: "24px",
                backgroundColor: userMessage.startsWith("✅") ? "#14532d" : "#7f1d1d",
                border: `1px solid ${userMessage.startsWith("✅") ? "#16a34a" : "#dc2626"}`,
                color: userMessage.startsWith("✅") ? "#34d399" : "#f87171",
              }}>
                {userMessage}
              </div>
            )}

            {/* Table */}
            <div style={{
              backgroundColor: "#1a1a2e",
              border: "1px solid #2a2a4a",
              borderRadius: "16px",
              overflow: "hidden",
            }}>
              <div style={{
                display: "grid",
                gridTemplateColumns: "2fr 2fr 1fr 1fr 2fr",
                padding: "16px 24px",
                backgroundColor: "#0f0f1a",
                borderBottom: "1px solid #2a2a4a",
                color: "#64748b", fontSize: "13px",
                fontWeight: "bold",
                textTransform: "uppercase" as const,
              }}>
                <span>Name</span>
                <span>Email</span>
                <span>Role</span>
                <span>Status</span>
                <span>Actions</span>
              </div>

              {users.length === 0 ? (
                <p style={{ padding: "24px", color: "#64748b" }}>No users found.</p>
              ) : (
                users.map((u) => (
                  <div key={u.id} style={{
                    display: "grid",
                    gridTemplateColumns: "2fr 2fr 1fr 1fr 2fr",
                    padding: "16px 24px",
                    borderBottom: "1px solid #2a2a4a",
                    alignItems: "center",
                    opacity: u.is_active ? 1 : 0.5,
                  }}>
                    <span style={{ fontWeight: "bold" }}>{u.full_name}</span>
                    <span style={{ color: "#94a3b8", fontSize: "14px" }}>{u.email}</span>
                    <span>
                      <span style={{
                        backgroundColor: roleColor[u.role] || "#a78bfa",
                        color: "#000", fontSize: "11px", fontWeight: "bold",
                        padding: "3px 10px", borderRadius: "20px",
                        textTransform: "uppercase" as const,
                      }}>
                        {u.role}
                      </span>
                    </span>
                    <span style={{
                      color: u.is_active ? "#34d399" : "#f87171",
                      fontWeight: "bold", fontSize: "13px",
                    }}>
                      {u.is_active ? "● Active" : "● Disabled"}
                    </span>
                    <div style={{ display: "flex", gap: "8px" }}>
                      <button onClick={() => handleEdit(u)} style={{
                        padding: "6px 14px", backgroundColor: "#7c3aed",
                        color: "#fff", border: "none", borderRadius: "6px",
                        cursor: "pointer", fontSize: "13px",
                      }}>✏️ Edit</button>
                      {u.is_active && (
                        <button onClick={() => handleDisable(u)} style={{
                          padding: "6px 14px", backgroundColor: "#dc2626",
                          color: "#fff", border: "none", borderRadius: "6px",
                          cursor: "pointer", fontSize: "13px",
                        }}>🚫 Disable</button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        );

      case "alerts":
  return (
    <div>
      <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>🔔 View Alerts</h2>
      <p style={{ color: "#64748b", marginBottom: "24px" }}>System alerts and security notifications</p>

      {/* Summary Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", marginBottom: "24px" }}>
        {[
          { label: "Critical", count: 0, color: "#f87171", bg: "#7f1d1d", border: "#dc2626", icon: "🚨" },
          { label: "Warning", count: 0, color: "#fbbf24", bg: "#78350f", border: "#d97706", icon: "⚠️" },
          { label: "Info", count: 0, color: "#60a5fa", bg: "#1e3a5f", border: "#2563eb", icon: "ℹ️" },
        ].map((s) => (
          <div key={s.label} style={{
            backgroundColor: s.bg,
            border: `1px solid ${s.border}`,
            borderRadius: "12px",
            padding: "20px 24px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}>
            <div>
              <p style={{ color: s.color, margin: "0 0 4px", fontSize: "13px", fontWeight: "bold" }}>{s.label}</p>
              <p style={{ fontSize: "32px", fontWeight: "bold", color: "#fff", margin: 0 }}>{s.count}</p>
            </div>
            <span style={{ fontSize: "28px" }}>{s.icon}</span>
          </div>
        ))}
      </div>

      {/* Alerts Table */}
      <div style={{
        backgroundColor: "#1a1a2e",
        border: "1px solid #2a2a4a",
        borderRadius: "16px",
        overflow: "hidden",
      }}>
        {/* Table Header */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr 2fr 3fr 1.5fr 1fr",
          padding: "16px 24px",
          backgroundColor: "#0f0f1a",
          borderBottom: "1px solid #2a2a4a",
          color: "#64748b",
          fontSize: "13px",
          fontWeight: "bold",
          textTransform: "uppercase" as const,
        }}>
          <span>Severity</span>
          <span>Type</span>
          <span>Message</span>
          <span>Time</span>
          <span>Status</span>
        </div>

        {/* Empty State */}
        <div style={{
          padding: "60px 24px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "12px",
          color: "#475569",
        }}>
          <span style={{ fontSize: "48px" }}>🔕</span>
          <p style={{ margin: 0, fontSize: "16px", fontWeight: "bold", color: "#64748b" }}>No alerts at this time</p>
          <p style={{ margin: 0, fontSize: "13px" }}>When alerts are triggered, they will appear here</p>
        </div>
      </div>
    </div>
  );

     case "reports":
  const actionCounts = auditLogs.reduce((acc: Record<string, number>, log) => {
    acc[log.action] = (acc[log.action] || 0) + 1;
    return acc;
  }, {});

  const roleCounts = users.reduce((acc: Record<string, number>, u) => {
    acc[u.role] = (acc[u.role] || 0) + 1;
    return acc;
  }, {});

  const activeUsers = users.filter((u) => u.is_active).length;
  const disabledUsers = users.filter((u) => !u.is_active).length;

  const updateActions = auditLogs.filter((l) => l.action === "UPDATE_USER").length;
  const listActions = auditLogs.filter((l) => l.action === "LIST_USERS").length;

  return (
    <div>
      <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>📊 View Reports</h2>
      <p style={{ color: "#64748b", marginBottom: "24px" }}>System overview based on users and audit activity</p>

      {/* Summary Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px", marginBottom: "28px" }}>
        {[
          { label: "Total Users", value: users.length, icon: "👥", color: "#a78bfa" },
          { label: "Active Users", value: activeUsers, icon: "✅", color: "#34d399" },
          { label: "Disabled Users", value: disabledUsers, icon: "🚫", color: "#f87171" },
          { label: "Total Audit Logs", value: auditLogs.length, icon: "🔍", color: "#60a5fa" },
        ].map((card) => (
          <div key={card.label} style={{
            backgroundColor: "#1a1a2e",
            border: "1px solid #2a2a4a",
            borderRadius: "12px",
            padding: "20px",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <p style={{ color: "#94a3b8", margin: 0, fontSize: "13px" }}>{card.label}</p>
              <span style={{ fontSize: "20px" }}>{card.icon}</span>
            </div>
            <p style={{ fontSize: "36px", fontWeight: "bold", color: card.color, margin: "8px 0 0" }}>
              {card.value}
            </p>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", marginBottom: "28px" }}>

        {/* Role Distribution */}
        <div style={{
          backgroundColor: "#1a1a2e",
          border: "1px solid #2a2a4a",
          borderRadius: "16px",
          padding: "24px",
        }}>
          <h3 style={{ margin: "0 0 20px", fontSize: "16px", color: "#94a3b8" }}>👤 Role Distribution</h3>
          {Object.keys(roleCounts).length === 0 ? (
            <p style={{ color: "#475569" }}>No user data.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {Object.entries(roleCounts).map(([role, count]) => {
                const total = users.length;
                const pct = Math.round((count / total) * 100);
                const color = roleColor[role] || "#a78bfa";
                return (
                  <div key={role}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                      <span style={{
                        backgroundColor: color,
                        color: "#000", fontSize: "11px", fontWeight: "bold",
                        padding: "2px 10px", borderRadius: "20px",
                        textTransform: "uppercase" as const,
                      }}>{role}</span>
                      <span style={{ color: "#94a3b8", fontSize: "13px" }}>{count} user{count !== 1 ? "s" : ""} · {pct}%</span>
                    </div>
                    <div style={{ backgroundColor: "#0f0f1a", borderRadius: "999px", height: "8px" }}>
                      <div style={{
                        width: `${pct}%`,
                        backgroundColor: color,
                        height: "8px",
                        borderRadius: "999px",
                        transition: "width 0.4s ease",
                      }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Audit Action Breakdown */}
        <div style={{
          backgroundColor: "#1a1a2e",
          border: "1px solid #2a2a4a",
          borderRadius: "16px",
          padding: "24px",
        }}>
          <h3 style={{ margin: "0 0 20px", fontSize: "16px", color: "#94a3b8" }}>🔍 Audit Action Breakdown</h3>
          {Object.keys(actionCounts).length === 0 ? (
            <p style={{ color: "#475569" }}>No audit data.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {Object.entries(actionCounts).map(([action, count]) => {
                const total = auditLogs.length;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={action}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                      <span style={{
                        backgroundColor: "#312e81", color: "#a78bfa",
                        fontSize: "11px", fontWeight: "bold",
                        padding: "2px 10px", borderRadius: "20px",
                      }}>{action}</span>
                      <span style={{ color: "#94a3b8", fontSize: "13px" }}>{count} · {pct}%</span>
                    </div>
                    <div style={{ backgroundColor: "#0f0f1a", borderRadius: "999px", height: "8px" }}>
                      <div style={{
                        width: `${pct}%`,
                        backgroundColor: "#7c3aed",
                        height: "8px",
                        borderRadius: "999px",
                        transition: "width 0.4s ease",
                      }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Activity Summary Table */}
      <div style={{
        backgroundColor: "#1a1a2e",
        border: "1px solid #2a2a4a",
        borderRadius: "16px",
        overflow: "hidden",
      }}>
        <div style={{ padding: "20px 24px", borderBottom: "1px solid #2a2a4a" }}>
          <h3 style={{ margin: 0, fontSize: "16px", color: "#94a3b8" }}>📋 Activity Summary</h3>
        </div>
        <div style={{
          display: "grid", gridTemplateColumns: "2fr 1fr 1fr",
          padding: "14px 24px",
          backgroundColor: "#0f0f1a",
          borderBottom: "1px solid #2a2a4a",
          color: "#64748b", fontSize: "13px", fontWeight: "bold",
          textTransform: "uppercase" as const,
        }}>
          <span>Metric</span>
          <span>Value</span>
          <span>Notes</span>
        </div>
        {[
          { metric: "Total Audit Events", value: auditLogs.length, note: "All time" },
          { metric: "User Listing Actions", value: listActions, note: "READ operations" },
          { metric: "User Update Actions", value: updateActions, note: "WRITE operations" },
          { metric: "Active Users", value: activeUsers, note: `Out of ${users.length} total` },
          { metric: "Disabled Accounts", value: disabledUsers, note: "Access revoked" },
          { metric: "Unique Roles", value: Object.keys(roleCounts).length, note: Object.keys(roleCounts).join(", ") || "—" },
        ].map((row) => (
          <div key={row.metric} style={{
            display: "grid", gridTemplateColumns: "2fr 1fr 1fr",
            padding: "14px 24px",
            borderBottom: "1px solid #2a2a4a",
            alignItems: "center",
          }}>
            <span style={{ fontWeight: "bold", fontSize: "14px" }}>{row.metric}</span>
            <span style={{ color: "#a78bfa", fontWeight: "bold", fontSize: "18px" }}>{row.value}</span>
            <span style={{ color: "#475569", fontSize: "13px" }}>{row.note}</span>
          </div>
        ))}
      </div>
    </div>
  );

      case "audit":
        return (
          <div>
            <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>🔍 Audit Logs</h2>
            <p style={{ color: "#64748b", marginBottom: "24px" }}>Track all admin actions in the system</p>
            <div style={{
              backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a",
              borderRadius: "16px", overflow: "hidden",
            }}>
              <div style={{
                display: "grid", gridTemplateColumns: "1.5fr 1.5fr 2fr 1.5fr",
                padding: "16px 24px", backgroundColor: "#0f0f1a",
                borderBottom: "1px solid #2a2a4a", color: "#64748b",
                fontSize: "13px", fontWeight: "bold",
                textTransform: "uppercase" as const,
              }}>
                <span>Action</span>
                <span>User</span>
                <span>Details</span>
                <span>Time</span>
              </div>
              {auditLogs.length === 0 ? (
                <p style={{ padding: "24px", color: "#64748b" }}>No audit logs yet.</p>
              ) : (
                auditLogs.map((log) => (
                  <div key={log.id} style={{
                    display: "grid", gridTemplateColumns: "1.5fr 1.5fr 2fr 1.5fr",
                    padding: "16px 24px", borderBottom: "1px solid #2a2a4a",
                    alignItems: "center",
                  }}>
                    <span>
                      <span style={{
                        backgroundColor: "#312e81", color: "#a78bfa",
                        fontSize: "11px", fontWeight: "bold",
                        padding: "3px 10px", borderRadius: "20px",
                      }}>
                        {log.action}
                      </span>
                    </span>
                    <span style={{ color: "#94a3b8", fontSize: "14px" }}>{log.user_email}</span>
                    <span style={{ color: "#64748b", fontSize: "13px" }}>{log.details || "—"}</span>
                    <span style={{ color: "#475569", fontSize: "13px" }}>
                      {new Date(log.created_at).toLocaleString()}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        );

      case "settings":
        return (
          <div>
            <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 24px" }}>⚙️ Settings</h2>
            <div style={{
              backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a",
              borderRadius: "16px", padding: "28px",
            }}>
              <p style={{ color: "#64748b" }}>Settings coming soon.</p>
            </div>
          </div>
        );

      case "profile":
        return (
          <div>
            <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 24px" }}>👤 My Profile</h2>
            <div style={{
              backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a",
              borderRadius: "16px", padding: "28px",
            }}>
              {user && (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div>
                    <p style={{ color: "#64748b", margin: "0 0 4px", fontSize: "13px" }}>Full Name</p>
                    <p style={{ margin: 0, fontSize: "18px", fontWeight: "bold" }}>{user.full_name}</p>
                  </div>
                  <div>
                    <p style={{ color: "#64748b", margin: "0 0 4px", fontSize: "13px" }}>Email</p>
                    <p style={{ margin: 0, fontSize: "18px" }}>{user.email}</p>
                  </div>
                  <div>
                    <p style={{ color: "#64748b", margin: "0 0 4px", fontSize: "13px" }}>Role</p>
                    <span style={{
                      backgroundColor: roleColor[user.role] || "#a78bfa",
                      color: "#000", fontSize: "12px", fontWeight: "bold",
                      padding: "4px 12px", borderRadius: "20px",
                      textTransform: "uppercase" as const,
                    }}>
                      {user.role}
                    </span>
                  </div>
                  <div>
                    <p style={{ color: "#64748b", margin: "0 0 4px", fontSize: "13px" }}>Status</p>
                    <p style={{ margin: 0, color: "#34d399", fontWeight: "bold" }}>● Active</p>
                  </div>
                  <div>
                    <p style={{ color: "#64748b", margin: "0 0 4px", fontSize: "13px" }}>Member Since</p>
                    <p style={{ margin: 0 }}>{new Date(user.created_at).toDateString()}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <ProtectedRoute>
      <div style={{ display: "flex", minHeight: "100vh", backgroundColor: "#0f0f1a", color: "#ffffff", fontFamily: "Arial, sans-serif" }}>

        {/* Sidebar */}
        <div style={{
          width: "240px", backgroundColor: "#1a1a2e",
          borderRight: "1px solid #2a2a4a", display: "flex",
          flexDirection: "column", position: "fixed",
          top: 0, left: 0, height: "100vh",
        }}>
          <div style={{
            padding: "24px 20px", borderBottom: "1px solid #2a2a4a",
            display: "flex", alignItems: "center", gap: "10px",
          }}>
            <span style={{ fontSize: "24px" }}>🛡️</span>
            <h1 style={{ fontSize: "20px", fontWeight: "bold", margin: 0, color: "#a78bfa" }}>Sentry</h1>
          </div>

          {user && (
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #2a2a4a" }}>
              <p style={{ margin: "0 0 4px", fontSize: "14px", fontWeight: "bold" }}>{user.full_name}</p>
              <span style={{
                backgroundColor: roleColor[user.role] || "#a78bfa",
                color: "#000", fontSize: "10px", fontWeight: "bold",
                padding: "2px 8px", borderRadius: "20px",
                textTransform: "uppercase" as const,
              }}>
                {user.role}
              </span>
            </div>
          )}

          <nav style={{ flex: 1, padding: "16px 0", overflowY: "auto" as const }}>
            {menuItems.filter((item) => item.show).map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveMenu(item.id)}
                style={{
                  width: "100%", padding: "12px 20px",
                  display: "flex", alignItems: "center", gap: "12px",
                  backgroundColor: activeMenu === item.id ? "#2a2a4a" : "transparent",
                  color: activeMenu === item.id ? "#a78bfa" : "#94a3b8",
                  border: "none",
                  borderLeft: activeMenu === item.id ? "3px solid #a78bfa" : "3px solid transparent",
                  cursor: "pointer", fontSize: "14px",
                  fontWeight: activeMenu === item.id ? "bold" : "normal",
                  textAlign: "left" as const,
                }}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </nav>

          <div style={{ padding: "16px 20px", borderTop: "1px solid #2a2a4a" }}>
            <button
              onClick={logout}
              style={{
                width: "100%", padding: "10px",
                backgroundColor: "#dc2626", color: "#fff",
                border: "none", borderRadius: "8px",
                cursor: "pointer", fontSize: "14px", fontWeight: "bold",
              }}
            >
              Logout
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div style={{ marginLeft: "240px", flex: 1, padding: "40px 32px" }}>
          {renderContent()}
        </div>

      </div>
    </ProtectedRoute>
  );
}