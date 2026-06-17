"use client";
import ProtectedRoute from "@/lib/auth/ProtectedRoute";
import { useAuth } from "@/lib/auth/AuthContext";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

type IngestionResult = {
  message: string;
  total_rows: number;
  ingested: number;
  skipped: number;
};

type RunHistory = {
  timestamp: string;
  result: IngestionResult;
  status: "success" | "error";
  error?: string;
};

type QASummary = {
  overall_status: string;
  checks: {
    unresolved_codes: {
      total_events: number;
      unresolved_count: number;
      unresolved_pct: number;
      threshold_pct: number;
      status: string;
    };
    duplicate_clusters: {
      duplicate_clusters: number;
      status: string;
      clusters: { email: string; id_count: number; person_ids: string[] }[];
    };
    unmatched_sessions: {
      total_entries: number;
      unmatched_count: number;
      unmatched_pct: number;
      threshold_pct: number;
      status: string;
      unmatched_person_ids: string[];
    };
  };
};

export default function Dashboard() {
  const { logout, token, login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [user, setUser] = useState<any>(null);
  const [activeMenu, setActiveMenu] = useState("dashboard");
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [editingUser, setEditingUser] = useState<any>(null);
  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("");
  const [userMessage, setUserMessage] = useState("");

  // Ingestion state
  const [ingestFile, setIngestFile] = useState<File | null>(null);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [ingestResult, setIngestResult] = useState<IngestionResult | null>(null);
  const [ingestError, setIngestError] = useState("");
  const [runHistory, setRunHistory] = useState<RunHistory[]>([]);

  // Identity QA state
  const [qa, setQA] = useState<QASummary | null>(null);
  const [qaLoading, setQaLoading] = useState(false);
  const [qaError, setQaError] = useState("");
  const [merging, setMerging] = useState<string | null>(null);
  const [qaMessage, setQaMessage] = useState("");

  // Handle GitHub OAuth token in URL
  useEffect(() => {
    const githubToken = searchParams.get("token");
    if (githubToken) {
      login(githubToken);
      router.replace("/dashboard");
    }
  }, [searchParams]);

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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected && selected.name.endsWith(".xlsx")) {
      setIngestFile(selected);
      setIngestError("");
    } else {
      setIngestError("❌ Only .xlsx files are accepted");
      setIngestFile(null);
    }
  };

  const handleIngest = async () => {
    if (!ingestFile) {
      setIngestError("Please select a file first");
      return;
    }
    setIngestLoading(true);
    setIngestError("");
    setIngestResult(null);

    const formData = new FormData();
    formData.append("file", ingestFile);

    try {
      const res = await fetch("http://localhost:8000/api/v1/ingest/access", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Ingestion failed");
      }

      const data: IngestionResult = await res.json();
      setIngestResult(data);
      setRunHistory((prev) => [
        { timestamp: new Date().toLocaleString(), result: data, status: "success" },
        ...prev,
      ]);
    } catch (err: any) {
      setIngestError(`❌ ${err.message}`);
      setRunHistory((prev) => [
        {
          timestamp: new Date().toLocaleString(),
          result: { message: "", total_rows: 0, ingested: 0, skipped: 0 },
          status: "error",
          error: err.message,
        },
        ...prev,
      ]);
    } finally {
      setIngestLoading(false);
    }
  };

  const loadQA = async () => {
    setQaLoading(true);
    setQaError("");
    try {
      const res = await fetch("http://localhost:8000/api/v1/identity-qa/summary", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setQA(data);
    } catch {
      setQaError("Failed to load QA data");
    } finally {
      setQaLoading(false);
    }
  };

  const handleMerge = async (primaryId: string, duplicateId: string) => {
    setMerging(duplicateId);
    await new Promise((r) => setTimeout(r, 1000));
    setQaMessage(`✅ Merged ${duplicateId} into ${primaryId}`);
    setMerging(null);
  };

  const statusBadge = (status: string) => (
    <span style={{
      padding: "3px 12px", borderRadius: "20px", fontSize: "12px", fontWeight: "bold",
      backgroundColor: status === "OK" ? "#14532d" : "#78350f",
      color: status === "OK" ? "#34d399" : "#fbbf24",
      border: `1px solid ${status === "OK" ? "#16a34a" : "#d97706"}`,
    }}>
      {status === "OK" ? "✅ OK" : "⚠️ WARNING"}
    </span>
  );

  const menuItems = [
    { id: "dashboard", icon: "🏠", label: "Dashboard", show: true },
    { id: "activity", icon: "📋", label: "Recent Activity", show: true },
    { id: "alerts", icon: "🔔", label: "View Alerts", show: canViewAlerts },
    { id: "users", icon: "👥", label: "Manage Users", show: canManageUsers },
    { id: "reports", icon: "📊", label: "View Reports", show: canViewReports },
    { id: "audit", icon: "🔍", label: "Audit Logs", show: isAdmin },
    { id: "ingestion", icon: "📥", label: "Data Ingestion", show: isAdmin },
    { id: "identity-qa", icon: "🔎", label: "Identity QA", show: isAdmin },
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
                  backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a",
                  borderRadius: "16px", padding: "28px",
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
                backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a",
                borderRadius: "16px", padding: "24px",
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
                      padding: "6px 14px", borderRadius: "20px", fontSize: "13px", fontWeight: "bold",
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
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "28px" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {[
                  { icon: "✅", text: "User logged in successfully", time: "Just now" },
                  { icon: "🔑", text: "JWT authentication active", time: "2 min ago" },
                  { icon: "🚀", text: "Backend connected", time: "5 min ago" },
                  { icon: "👥", text: "User management accessed", time: "10 min ago" },
                  { icon: "🔒", text: "Role-based access enforced", time: "15 min ago" },
                ].map((item) => (
                  <div key={item.text} style={{
                    backgroundColor: "#0f0f1a", border: "1px solid #2a2a4a",
                    borderRadius: "10px", padding: "14px 18px",
                    display: "flex", justifyContent: "space-between", alignItems: "center",
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
            {editingUser && (
              <div style={{
                position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
                backgroundColor: "rgba(0,0,0,0.7)",
                display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
              }}>
                <div style={{
                  backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a",
                  borderRadius: "16px", padding: "32px", width: "400px",
                }}>
                  <h3 style={{ margin: "0 0 24px", fontSize: "20px" }}>Edit User</h3>
                  <label style={{ color: "#94a3b8", fontSize: "14px" }}>Full Name</label>
                  <input
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    style={{
                      width: "100%", padding: "12px", marginTop: "8px", marginBottom: "16px",
                      backgroundColor: "#0f0f1a", border: "1px solid #2a2a4a",
                      borderRadius: "8px", color: "#fff", fontSize: "15px",
                      boxSizing: "border-box" as const,
                    }}
                  />
                  <label style={{ color: "#94a3b8", fontSize: "14px" }}>Role</label>
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    style={{
                      width: "100%", padding: "12px", marginTop: "8px", marginBottom: "24px",
                      backgroundColor: "#0f0f1a", border: "1px solid #2a2a4a",
                      borderRadius: "8px", color: "#fff", fontSize: "15px",
                      boxSizing: "border-box" as const,
                    }}
                  >
                    {["admin", "leadership", "manager", "employee"].map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                  <div style={{ display: "flex", gap: "12px" }}>
                    <button onClick={handleSave} style={{
                      flex: 1, padding: "12px", backgroundColor: "#7c3aed", color: "#fff",
                      border: "none", borderRadius: "8px", cursor: "pointer", fontWeight: "bold",
                    }}>Save</button>
                    <button onClick={() => setEditingUser(null)} style={{
                      flex: 1, padding: "12px", backgroundColor: "#374151", color: "#fff",
                      border: "none", borderRadius: "8px", cursor: "pointer", fontWeight: "bold",
                    }}>Cancel</button>
                  </div>
                </div>
              </div>
            )}
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
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", overflow: "hidden" }}>
              <div style={{
                display: "grid", gridTemplateColumns: "2fr 2fr 1fr 1fr 2fr",
                padding: "16px 24px", backgroundColor: "#0f0f1a",
                borderBottom: "1px solid #2a2a4a", color: "#64748b",
                fontSize: "13px", fontWeight: "bold", textTransform: "uppercase" as const,
              }}>
                <span>Name</span><span>Email</span><span>Role</span><span>Status</span><span>Actions</span>
              </div>
              {users.length === 0 ? (
                <p style={{ padding: "24px", color: "#64748b" }}>No users found.</p>
              ) : (
                users.map((u) => (
                  <div key={u.id} style={{
                    display: "grid", gridTemplateColumns: "2fr 2fr 1fr 1fr 2fr",
                    padding: "16px 24px", borderBottom: "1px solid #2a2a4a",
                    alignItems: "center", opacity: u.is_active ? 1 : 0.5,
                  }}>
                    <span style={{ fontWeight: "bold" }}>{u.full_name}</span>
                    <span style={{ color: "#94a3b8", fontSize: "14px" }}>{u.email}</span>
                    <span>
                      <span style={{
                        backgroundColor: roleColor[u.role] || "#a78bfa", color: "#000",
                        fontSize: "11px", fontWeight: "bold", padding: "3px 10px",
                        borderRadius: "20px", textTransform: "uppercase" as const,
                      }}>{u.role}</span>
                    </span>
                    <span style={{ color: u.is_active ? "#34d399" : "#f87171", fontWeight: "bold", fontSize: "13px" }}>
                      {u.is_active ? "● Active" : "● Disabled"}
                    </span>
                    <div style={{ display: "flex", gap: "8px" }}>
                      <button onClick={() => handleEdit(u)} style={{
                        padding: "6px 14px", backgroundColor: "#7c3aed", color: "#fff",
                        border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "13px",
                      }}>✏️ Edit</button>
                      {u.is_active && (
                        <button onClick={() => handleDisable(u)} style={{
                          padding: "6px 14px", backgroundColor: "#dc2626", color: "#fff",
                          border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "13px",
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
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", marginBottom: "24px" }}>
              {[
                { label: "Critical", count: 0, color: "#f87171", bg: "#7f1d1d", border: "#dc2626", icon: "🚨" },
                { label: "Warning", count: 0, color: "#fbbf24", bg: "#78350f", border: "#d97706", icon: "⚠️" },
                { label: "Info", count: 0, color: "#60a5fa", bg: "#1e3a5f", border: "#2563eb", icon: "ℹ️" },
              ].map((s) => (
                <div key={s.label} style={{
                  backgroundColor: s.bg, border: `1px solid ${s.border}`,
                  borderRadius: "12px", padding: "20px 24px",
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                }}>
                  <div>
                    <p style={{ color: s.color, margin: "0 0 4px", fontSize: "13px", fontWeight: "bold" }}>{s.label}</p>
                    <p style={{ fontSize: "32px", fontWeight: "bold", color: "#fff", margin: 0 }}>{s.count}</p>
                  </div>
                  <span style={{ fontSize: "28px" }}>{s.icon}</span>
                </div>
              ))}
            </div>
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", overflow: "hidden" }}>
              <div style={{
                display: "grid", gridTemplateColumns: "1fr 2fr 3fr 1.5fr 1fr",
                padding: "16px 24px", backgroundColor: "#0f0f1a",
                borderBottom: "1px solid #2a2a4a", color: "#64748b",
                fontSize: "13px", fontWeight: "bold", textTransform: "uppercase" as const,
              }}>
                <span>Severity</span><span>Type</span><span>Message</span><span>Time</span><span>Status</span>
              </div>
              <div style={{
                padding: "60px 24px", display: "flex", flexDirection: "column",
                alignItems: "center", gap: "12px", color: "#475569",
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
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px", marginBottom: "28px" }}>
              {[
                { label: "Total Users", value: users.length, icon: "👥", color: "#a78bfa" },
                { label: "Active Users", value: activeUsers, icon: "✅", color: "#34d399" },
                { label: "Disabled Users", value: disabledUsers, icon: "🚫", color: "#f87171" },
                { label: "Total Audit Logs", value: auditLogs.length, icon: "🔍", color: "#60a5fa" },
              ].map((card) => (
                <div key={card.label} style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "12px", padding: "20px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <p style={{ color: "#94a3b8", margin: 0, fontSize: "13px" }}>{card.label}</p>
                    <span style={{ fontSize: "20px" }}>{card.icon}</span>
                  </div>
                  <p style={{ fontSize: "36px", fontWeight: "bold", color: card.color, margin: "8px 0 0" }}>{card.value}</p>
                </div>
              ))}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", marginBottom: "28px" }}>
              <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "24px" }}>
                <h3 style={{ margin: "0 0 20px", fontSize: "16px", color: "#94a3b8" }}>👤 Role Distribution</h3>
                {Object.keys(roleCounts).length === 0 ? <p style={{ color: "#475569" }}>No user data.</p> : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    {Object.entries(roleCounts).map(([role, count]) => {
                      const total = users.length;
                      const pct = Math.round((count / total) * 100);
                      const color = roleColor[role] || "#a78bfa";
                      return (
                        <div key={role}>
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                            <span style={{ backgroundColor: color, color: "#000", fontSize: "11px", fontWeight: "bold", padding: "2px 10px", borderRadius: "20px", textTransform: "uppercase" as const }}>{role}</span>
                            <span style={{ color: "#94a3b8", fontSize: "13px" }}>{count} · {pct}%</span>
                          </div>
                          <div style={{ backgroundColor: "#0f0f1a", borderRadius: "999px", height: "8px" }}>
                            <div style={{ width: `${pct}%`, backgroundColor: color, height: "8px", borderRadius: "999px" }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
              <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "24px" }}>
                <h3 style={{ margin: "0 0 20px", fontSize: "16px", color: "#94a3b8" }}>🔍 Audit Action Breakdown</h3>
                {Object.keys(actionCounts).length === 0 ? <p style={{ color: "#475569" }}>No audit data.</p> : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    {Object.entries(actionCounts).map(([action, count]) => {
                      const total = auditLogs.length;
                      const pct = Math.round((count / total) * 100);
                      return (
                        <div key={action}>
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                            <span style={{ backgroundColor: "#312e81", color: "#a78bfa", fontSize: "11px", fontWeight: "bold", padding: "2px 10px", borderRadius: "20px" }}>{action}</span>
                            <span style={{ color: "#94a3b8", fontSize: "13px" }}>{count} · {pct}%</span>
                          </div>
                          <div style={{ backgroundColor: "#0f0f1a", borderRadius: "999px", height: "8px" }}>
                            <div style={{ width: `${pct}%`, backgroundColor: "#7c3aed", height: "8px", borderRadius: "999px" }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", overflow: "hidden" }}>
              <div style={{ padding: "20px 24px", borderBottom: "1px solid #2a2a4a" }}>
                <h3 style={{ margin: 0, fontSize: "16px", color: "#94a3b8" }}>📋 Activity Summary</h3>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", padding: "14px 24px", backgroundColor: "#0f0f1a", borderBottom: "1px solid #2a2a4a", color: "#64748b", fontSize: "13px", fontWeight: "bold", textTransform: "uppercase" as const }}>
                <span>Metric</span><span>Value</span><span>Notes</span>
              </div>
              {[
                { metric: "Total Audit Events", value: auditLogs.length, note: "All time" },
                { metric: "User Listing Actions", value: listActions, note: "READ operations" },
                { metric: "User Update Actions", value: updateActions, note: "WRITE operations" },
                { metric: "Active Users", value: activeUsers, note: `Out of ${users.length} total` },
                { metric: "Disabled Accounts", value: disabledUsers, note: "Access revoked" },
                { metric: "Unique Roles", value: Object.keys(roleCounts).length, note: Object.keys(roleCounts).join(", ") || "—" },
              ].map((row) => (
                <div key={row.metric} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", padding: "14px 24px", borderBottom: "1px solid #2a2a4a", alignItems: "center" }}>
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
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", overflow: "hidden" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1.5fr 2fr 1.5fr", padding: "16px 24px", backgroundColor: "#0f0f1a", borderBottom: "1px solid #2a2a4a", color: "#64748b", fontSize: "13px", fontWeight: "bold", textTransform: "uppercase" as const }}>
                <span>Action</span><span>User</span><span>Details</span><span>Time</span>
              </div>
              {auditLogs.length === 0 ? (
                <p style={{ padding: "24px", color: "#64748b" }}>No audit logs yet.</p>
              ) : (
                auditLogs.map((log) => (
                  <div key={log.id} style={{ display: "grid", gridTemplateColumns: "1.5fr 1.5fr 2fr 1.5fr", padding: "16px 24px", borderBottom: "1px solid #2a2a4a", alignItems: "center" }}>
                    <span><span style={{ backgroundColor: "#312e81", color: "#a78bfa", fontSize: "11px", fontWeight: "bold", padding: "3px 10px", borderRadius: "20px" }}>{log.action}</span></span>
                    <span style={{ color: "#94a3b8", fontSize: "14px" }}>{log.user_email}</span>
                    <span style={{ color: "#64748b", fontSize: "13px" }}>{log.details || "—"}</span>
                    <span style={{ color: "#475569", fontSize: "13px" }}>{new Date(log.created_at).toLocaleString()}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        );

      case "ingestion":
        return (
          <div>
            <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>📥 Data Ingestion</h2>
            <p style={{ color: "#64748b", marginBottom: "32px" }}>Upload access log xlsx and trigger ingestion</p>
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "28px", marginBottom: "24px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "20px", marginTop: 0 }}>📂 Upload File</h3>
              <div style={{ border: "2px dashed #2a2a4a", borderRadius: "12px", padding: "32px", textAlign: "center", marginBottom: "20px", backgroundColor: "#0f0f1a" }}>
                <p style={{ color: "#64748b", marginBottom: "16px" }}>
                  {ingestFile ? `✅ Selected: ${ingestFile.name}` : "Select an .xlsx file to upload"}
                </p>
                <input type="file" accept=".xlsx" onChange={handleFileChange} style={{ display: "none" }} id="file-upload" />
                <label htmlFor="file-upload" style={{ padding: "10px 24px", backgroundColor: "#312e81", color: "#a78bfa", borderRadius: "8px", cursor: "pointer", fontWeight: "bold", fontSize: "14px" }}>
                  Browse File
                </label>
              </div>
              {ingestError && (
                <div style={{ padding: "12px 20px", borderRadius: "10px", marginBottom: "16px", backgroundColor: "#7f1d1d", border: "1px solid #dc2626", color: "#f87171" }}>
                  {ingestError}
                </div>
              )}
              <button onClick={handleIngest} disabled={ingestLoading || !ingestFile} style={{
                width: "100%", padding: "14px",
                backgroundColor: ingestLoading || !ingestFile ? "#374151" : "#7c3aed",
                color: "#fff", border: "none", borderRadius: "10px",
                cursor: ingestLoading || !ingestFile ? "not-allowed" : "pointer",
                fontSize: "16px", fontWeight: "bold",
              }}>
                {ingestLoading ? "⏳ Ingesting..." : "🚀 Start Ingestion"}
              </button>
            </div>
            {ingestResult && (
              <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #16a34a", borderRadius: "16px", padding: "28px", marginBottom: "24px" }}>
                <h3 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "20px", marginTop: 0, color: "#34d399" }}>✅ Ingestion Complete</h3>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" }}>
                  {[
                    { label: "Total Rows", value: ingestResult.total_rows, color: "#a78bfa" },
                    { label: "Ingested", value: ingestResult.ingested, color: "#34d399" },
                    { label: "Skipped", value: ingestResult.skipped, color: "#f87171" },
                  ].map((stat) => (
                    <div key={stat.label} style={{ backgroundColor: "#0f0f1a", border: "1px solid #2a2a4a", borderRadius: "12px", padding: "20px", textAlign: "center" as const }}>
                      <p style={{ color: "#64748b", margin: "0 0 8px", fontSize: "13px" }}>{stat.label}</p>
                      <p style={{ fontSize: "36px", fontWeight: "bold", color: stat.color, margin: 0 }}>{stat.value}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {runHistory.length > 0 && (
              <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "28px" }}>
                <h3 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "20px", marginTop: 0 }}>🕐 Run History</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  {runHistory.map((run, i) => (
                    <div key={i} style={{ backgroundColor: "#0f0f1a", border: `1px solid ${run.status === "success" ? "#16a34a" : "#dc2626"}`, borderRadius: "10px", padding: "14px 18px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <span style={{ color: run.status === "success" ? "#34d399" : "#f87171", fontWeight: "bold", marginRight: "12px" }}>
                          {run.status === "success" ? "✅ Success" : "❌ Failed"}
                        </span>
                        {run.status === "success" ? (
                          <span style={{ color: "#94a3b8", fontSize: "14px" }}>{run.result.ingested} ingested · {run.result.skipped} skipped · {run.result.total_rows} total</span>
                        ) : (
                          <span style={{ color: "#f87171", fontSize: "14px" }}>{run.error}</span>
                        )}
                      </div>
                      <span style={{ color: "#475569", fontSize: "13px" }}>{run.timestamp}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );

      case "identity-qa":
        return (
          <div>
            <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>🔎 Identity QA</h2>
            <p style={{ color: "#64748b", marginBottom: "24px" }}>Review and clean identity issues before trusting any KPI</p>
            <button onClick={loadQA} disabled={qaLoading} style={{
              padding: "10px 24px", backgroundColor: "#7c3aed", color: "#fff",
              border: "none", borderRadius: "8px", cursor: qaLoading ? "not-allowed" : "pointer",
              fontWeight: "bold", fontSize: "14px", marginBottom: "24px",
              opacity: qaLoading ? 0.6 : 1,
            }}>
              {qaLoading ? "⏳ Loading..." : "🔄 Run QA Checks"}
            </button>
            {qaError && (
              <div style={{ padding: "12px 20px", borderRadius: "10px", marginBottom: "24px", backgroundColor: "#7f1d1d", border: "1px solid #dc2626", color: "#f87171" }}>
                {qaError}
              </div>
            )}
            {qaMessage && (
              <div style={{ padding: "12px 20px", borderRadius: "10px", marginBottom: "24px", backgroundColor: "#14532d", border: "1px solid #16a34a", color: "#34d399" }}>
                {qaMessage}
              </div>
            )}
            {qa && qa.checks && (
              <>
                <div style={{
                  backgroundColor: qa.overall_status === "OK" ? "#14532d" : "#78350f",
                  border: `1px solid ${qa.overall_status === "OK" ? "#16a34a" : "#d97706"}`,
                  borderRadius: "12px", padding: "16px 24px", marginBottom: "24px",
                  display: "flex", alignItems: "center", gap: "12px",
                }}>
                  <span style={{ fontSize: "24px" }}>{qa.overall_status === "OK" ? "✅" : "⚠️"}</span>
                  <div>
                    <p style={{ margin: 0, fontWeight: "bold", fontSize: "16px" }}>Overall Status: {qa.overall_status}</p>
                    <p style={{ margin: 0, fontSize: "13px", color: "#94a3b8" }}>
                      {qa.overall_status === "OK" ? "All identity checks passed. KPIs can be trusted." : "Some checks need attention before trusting KPIs."}
                    </p>
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", marginBottom: "28px" }}>
                  {[
                    { label: "Unresolved Codes", value: `${qa.checks.unresolved_codes.unresolved_pct}%`, sub: `${qa.checks.unresolved_codes.unresolved_count} of ${qa.checks.unresolved_codes.total_events} events`, threshold: `Threshold: ${qa.checks.unresolved_codes.threshold_pct}%`, status: qa.checks.unresolved_codes.status, icon: "🏷️" },
                    { label: "Duplicate Clusters", value: qa.checks.duplicate_clusters.duplicate_clusters, sub: "persons with multiple IDs", threshold: "Threshold: 0", status: qa.checks.duplicate_clusters.status, icon: "👥" },
                    { label: "Unmatched Sessions", value: `${qa.checks.unmatched_sessions.unmatched_pct}%`, sub: `${qa.checks.unmatched_sessions.unmatched_count} of ${qa.checks.unmatched_sessions.total_entries} entries`, threshold: `Threshold: ${qa.checks.unmatched_sessions.threshold_pct}%`, status: qa.checks.unmatched_sessions.status, icon: "🚪" },
                  ].map((card) => (
                    <div key={card.label} style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "12px", padding: "20px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                        <span style={{ fontSize: "20px" }}>{card.icon}</span>
                        {statusBadge(card.status)}
                      </div>
                      <p style={{ color: "#94a3b8", margin: "0 0 4px", fontSize: "13px" }}>{card.label}</p>
                      <p style={{ fontSize: "32px", fontWeight: "bold", color: "#a78bfa", margin: "0 0 4px" }}>{card.value}</p>
                      <p style={{ color: "#64748b", fontSize: "12px", margin: "0 0 2px" }}>{card.sub}</p>
                      <p style={{ color: "#475569", fontSize: "11px", margin: 0 }}>{card.threshold}</p>
                    </div>
                  ))}
                </div>
                <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", overflow: "hidden", marginBottom: "24px" }}>
                  <div style={{ padding: "20px 24px", borderBottom: "1px solid #2a2a4a" }}>
                    <h3 style={{ margin: 0, fontSize: "16px", color: "#94a3b8" }}>👥 Duplicate Identity Clusters</h3>
                  </div>
                  {qa.checks.duplicate_clusters.clusters.length === 0 ? (
                    <div style={{ padding: "40px", textAlign: "center" as const, color: "#475569" }}>
                      <p style={{ fontSize: "32px", margin: "0 0 8px" }}>✅</p>
                      <p style={{ margin: 0 }}>No duplicate identities found</p>
                    </div>
                  ) : (
                    <>
                      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 2fr 1fr", padding: "12px 24px", backgroundColor: "#0f0f1a", borderBottom: "1px solid #2a2a4a", color: "#64748b", fontSize: "13px", fontWeight: "bold", textTransform: "uppercase" as const }}>
                        <span>Email</span><span>Count</span><span>Person IDs</span><span>Action</span>
                      </div>
                      {qa.checks.duplicate_clusters.clusters.map((cluster) => (
                        <div key={cluster.email} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 2fr 1fr", padding: "16px 24px", borderBottom: "1px solid #2a2a4a", alignItems: "center" }}>
                          <span style={{ color: "#94a3b8", fontSize: "14px" }}>{cluster.email}</span>
                          <span style={{ color: "#f87171", fontWeight: "bold" }}>{cluster.id_count}</span>
                          <div style={{ display: "flex", flexDirection: "column" as const, gap: "4px" }}>
                            {cluster.person_ids.map((id, i) => (
                              <span key={id} style={{ fontSize: "11px", color: i === 0 ? "#34d399" : "#f87171" }}>
                                {i === 0 ? "✅ Primary: " : "❌ Duplicate: "}{id.slice(0, 8)}...
                              </span>
                            ))}
                          </div>
                          <button onClick={() => handleMerge(cluster.person_ids[0], cluster.person_ids[1])} disabled={merging === cluster.person_ids[1]} style={{
                            padding: "6px 14px", backgroundColor: "#7c3aed", color: "#fff",
                            border: "none", borderRadius: "6px", cursor: "pointer",
                            fontSize: "13px", fontWeight: "bold",
                            opacity: merging === cluster.person_ids[1] ? 0.5 : 1,
                          }}>
                            {merging === cluster.person_ids[1] ? "Merging..." : "🔗 Merge"}
                          </button>
                        </div>
                      ))}
                    </>
                  )}
                </div>
                <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", overflow: "hidden" }}>
                  <div style={{ padding: "20px 24px", borderBottom: "1px solid #2a2a4a" }}>
                    <h3 style={{ margin: 0, fontSize: "16px", color: "#94a3b8" }}>🚪 Unmatched Sessions</h3>
                  </div>
                  {qa.checks.unmatched_sessions.unmatched_person_ids.length === 0 ? (
                    <div style={{ padding: "40px", textAlign: "center" as const, color: "#475569" }}>
                      <p style={{ fontSize: "32px", margin: "0 0 8px" }}>✅</p>
                      <p style={{ margin: 0 }}>No unmatched sessions found</p>
                    </div>
                  ) : (
                    qa.checks.unmatched_sessions.unmatched_person_ids.map((id) => (
                      <div key={id} style={{ padding: "14px 24px", borderBottom: "1px solid #2a2a4a", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ color: "#94a3b8", fontSize: "14px" }}>🚪 {id}</span>
                        <span style={{ padding: "3px 12px", borderRadius: "20px", fontSize: "12px", backgroundColor: "#7f1d1d", color: "#f87171", border: "1px solid #dc2626" }}>No matching EXIT</span>
                      </div>
                    ))
                  )}
                </div>
              </>
            )}
          </div>
        );

      case "settings":
        return (
          <div>
            <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 24px" }}>⚙️ Settings</h2>
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "28px" }}>
              <p style={{ color: "#64748b" }}>Settings coming soon.</p>
            </div>
          </div>
        );

      case "profile":
        return (
          <div>
            <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 24px" }}>👤 My Profile</h2>
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "28px" }}>
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
                    <span style={{ backgroundColor: roleColor[user.role] || "#a78bfa", color: "#000", fontSize: "12px", fontWeight: "bold", padding: "4px 12px", borderRadius: "20px", textTransform: "uppercase" as const }}>{user.role}</span>
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
        <div style={{ width: "240px", backgroundColor: "#1a1a2e", borderRight: "1px solid #2a2a4a", display: "flex", flexDirection: "column", position: "fixed", top: 0, left: 0, height: "100vh" }}>
          <div style={{ padding: "24px 20px", borderBottom: "1px solid #2a2a4a", display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "24px" }}>🛡️</span>
            <h1 style={{ fontSize: "20px", fontWeight: "bold", margin: 0, color: "#a78bfa" }}>Sentry</h1>
          </div>
          {user && (
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #2a2a4a" }}>
              <p style={{ margin: "0 0 4px", fontSize: "14px", fontWeight: "bold" }}>{user.full_name}</p>
              <span style={{ backgroundColor: roleColor[user.role] || "#a78bfa", color: "#000", fontSize: "10px", fontWeight: "bold", padding: "2px 8px", borderRadius: "20px", textTransform: "uppercase" as const }}>{user.role}</span>
            </div>
          )}
          <nav style={{ flex: 1, padding: "16px 0", overflowY: "auto" as const }}>
            {menuItems.filter((item) => item.show).map((item) => (
              <button key={item.id} onClick={() => setActiveMenu(item.id)} style={{
                width: "100%", padding: "12px 20px",
                display: "flex", alignItems: "center", gap: "12px",
                backgroundColor: activeMenu === item.id ? "#2a2a4a" : "transparent",
                color: activeMenu === item.id ? "#a78bfa" : "#94a3b8",
                border: "none",
                borderLeft: activeMenu === item.id ? "3px solid #a78bfa" : "3px solid transparent",
                cursor: "pointer", fontSize: "14px",
                fontWeight: activeMenu === item.id ? "bold" : "normal",
                textAlign: "left" as const,
              }}>
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </nav>
          <div style={{ padding: "16px 20px", borderTop: "1px solid #2a2a4a" }}>
            <button onClick={logout} style={{ width: "100%", padding: "10px", backgroundColor: "#dc2626", color: "#fff", border: "none", borderRadius: "8px", cursor: "pointer", fontSize: "14px", fontWeight: "bold" }}>Logout</button>
          </div>
        </div>
        <div style={{ marginLeft: "240px", flex: 1, padding: "40px 32px" }}>
          {renderContent()}
        </div>
      </div>
    </ProtectedRoute>
  );
}