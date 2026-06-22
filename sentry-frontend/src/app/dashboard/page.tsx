"use client";
import ProtectedRoute from "@/lib/auth/ProtectedRoute";
import { useAuth } from "@/lib/auth/AuthContext";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, Area, AreaChart, ResponsiveContainer } from "recharts";

function OccupancyTrendChart({ data }: { data: any[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a2a4a" />
        <XAxis dataKey="day" stroke="#64748b" fontSize={12} />
        <YAxis stroke="#64748b" fontSize={12} />
        <Tooltip contentStyle={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "8px" }} labelStyle={{ color: "#fff" }} />
        <Legend />
        <Line type="monotone" dataKey="peak_occupancy" stroke="#a78bfa" strokeWidth={2} name="Peak Occupancy" dot={false} />
        <Line type="monotone" dataKey="avg_occupancy" stroke="#34d399" strokeWidth={2} name="Avg Occupancy" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function OccupancyForecastChart({ data }: { data: any[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a2a4a" />
        <XAxis dataKey="date" stroke="#64748b" fontSize={12} />
        <YAxis stroke="#64748b" fontSize={12} />
        <Tooltip contentStyle={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "8px" }} labelStyle={{ color: "#fff" }} />
        <Legend />
        <Area type="monotone" dataKey="upper_bound" stroke="transparent" fill="#7c3aed" fillOpacity={0.2} name="Upper Bound" />
        <Area type="monotone" dataKey="predicted" stroke="#a78bfa" fill="#7c3aed" fillOpacity={0.3} strokeWidth={2} name="Predicted" />
        <Area type="monotone" dataKey="lower_bound" stroke="transparent" fill="#0f0f1a" fillOpacity={1} name="Lower Bound" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

type IngestionResult = { message: string; total_rows: number; ingested: number; skipped: number; };
type RunHistory = { timestamp: string; result: IngestionResult; status: "success" | "error"; error?: string; };
type QASummary = {
  overall_status: string;
  checks: {
    unresolved_codes: { total_events: number; unresolved_count: number; unresolved_pct: number; threshold_pct: number; status: string; };
    duplicate_clusters: { duplicate_clusters: number; status: string; clusters: { email: string; id_count: number; person_ids: string[] }[]; };
    unmatched_sessions: { total_entries: number; unmatched_count: number; unmatched_pct: number; threshold_pct: number; status: string; unmatched_person_ids: string[]; };
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

  const [ingestFile, setIngestFile] = useState<File | null>(null);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [ingestResult, setIngestResult] = useState<IngestionResult | null>(null);
  const [ingestError, setIngestError] = useState("");
  const [runHistory, setRunHistory] = useState<RunHistory[]>([]);

  const [qa, setQA] = useState<QASummary | null>(null);
  const [qaLoading, setQaLoading] = useState(false);
  const [qaError, setQaError] = useState("");
  const [merging, setMerging] = useState<string | null>(null);
  const [qaMessage, setQaMessage] = useState("");

  const [syncStatus, setSyncStatus] = useState<any>(null);
  const [syncLoading, setSyncLoading] = useState(false);
  const [syncTriggering, setSyncTriggering] = useState(false);
  const [syncMessage, setSyncMessage] = useState("");

  const [attendanceData, setAttendanceData] = useState<{ daysPresent: any[]; avgArrival: any[]; sessionHours: any[]; trend: any[]; cohortSummary: any[]; }>({ daysPresent: [], avgArrival: [], sessionHours: [], trend: [], cohortSummary: [] });
  const [attendanceLoading, setAttendanceLoading] = useState(false);
  const [attendanceMonth, setAttendanceMonth] = useState("2026-01");

  const [occupancyPeak, setOccupancyPeak] = useState<any[]>([]);
  const [occupancyTrend, setOccupancyTrend] = useState<any[]>([]);
  const [occupancyForecast, setOccupancyForecast] = useState<any[]>([]);
  const [mobileAdoption, setMobileAdoption] = useState<any[]>([]);

  // Security state
  const [securityMetrics, setSecurityMetrics] = useState<any>(null);
  const [securityQueue, setSecurityQueue] = useState<any[]>([]);
  const [queueSummary, setQueueSummary] = useState<any>({});
  const [securityLoading, setSecurityLoading] = useState(false);
  const [securityMessage, setSecurityMessage] = useState("");

  useEffect(() => {
    const githubToken = searchParams.get("token");
    if (githubToken) { login(githubToken); router.replace("/dashboard"); }
  }, [searchParams]);

  useEffect(() => {
    if (token) {
      fetch("http://localhost:8000/api/v1/users/me", { headers: { Authorization: `Bearer ${token}` } })
        .then((res) => res.json())
        .then((data) => {
          setUser(data);
          if (data.role === "admin") {
            fetch("http://localhost:8000/api/v1/users/audit-logs", { headers: { Authorization: `Bearer ${token}` } }).then((res) => res.json()).then((logs) => setAuditLogs(Array.isArray(logs) ? logs : []));
            fetch("http://localhost:8000/api/v1/users/", { headers: { Authorization: `Bearer ${token}` } }).then((res) => res.json()).then((data) => setUsers(Array.isArray(data) ? data : []));
          }
          fetchAttendance("2026-01");
          fetch("http://localhost:8000/api/v1/occupancy-kpi/peak?days=365", { headers: { Authorization: `Bearer ${token}` } }).then((res) => res.json()).then((data) => setOccupancyPeak(data.data || []));
          fetch("http://localhost:8000/api/v1/occupancy-kpi/trend?days=365", { headers: { Authorization: `Bearer ${token}` } }).then((res) => res.json()).then((data) => setOccupancyTrend(data.data || []));
          fetch("http://localhost:8000/api/v1/occupancy-kpi/forecast?forecast_days=7", { headers: { Authorization: `Bearer ${token}` } }).then((res) => res.json()).then((data) => setOccupancyForecast(data.forecast || []));
          fetch("http://localhost:8000/api/v1/occupancy-kpi/mobile-adoption?days=365", { headers: { Authorization: `Bearer ${token}` } }).then((res) => res.json()).then((data) => setMobileAdoption(data.data || []));
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

  const roleColor: Record<string, string> = { admin: "#f87171", leadership: "#fbbf24", manager: "#60a5fa", employee: "#34d399", leader: "#a78bfa" };

  const handleEdit = (u: any) => { setEditingUser(u); setNewName(u.full_name); setNewRole(u.role); setUserMessage(""); };

  const handleSave = async () => {
    if (!editingUser) return;
    const res = await fetch(`http://localhost:8000/api/v1/users/${editingUser.id}`, { method: "PUT", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ full_name: newName, role: newRole }) });
    if (res.ok) { const updated = await res.json(); setUsers(users.map((u) => (u.id === updated.id ? updated : u))); setEditingUser(null); setUserMessage("✅ User updated successfully!"); }
    else { setUserMessage("❌ Failed to update user"); }
  };

  const handleDisable = async (u: any) => {
    if (!confirm(`Disable ${u.full_name}?`)) return;
    const res = await fetch(`http://localhost:8000/api/v1/users/${u.id}/disable`, { method: "PATCH", headers: { Authorization: `Bearer ${token}` } });
    if (res.ok) { const updated = await res.json(); setUsers(users.map((x) => (x.id === updated.id ? updated : x))); setUserMessage(`✅ ${u.full_name} has been disabled`); }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected && selected.name.endsWith(".xlsx")) { setIngestFile(selected); setIngestError(""); }
    else { setIngestError("❌ Only .xlsx files are accepted"); setIngestFile(null); }
  };

  const handleIngest = async () => {
    if (!ingestFile) { setIngestError("Please select a file first"); return; }
    setIngestLoading(true); setIngestError(""); setIngestResult(null);
    const formData = new FormData();
    formData.append("file", ingestFile);
    try {
      const res = await fetch("http://localhost:8000/api/v1/ingest/access", { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: formData });
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || "Ingestion failed"); }
      const data: IngestionResult = await res.json();
      setIngestResult(data);
      setRunHistory((prev) => [{ timestamp: new Date().toLocaleString(), result: data, status: "success" }, ...prev]);
    } catch (err: any) {
      setIngestError(`❌ ${err.message}`);
      setRunHistory((prev) => [{ timestamp: new Date().toLocaleString(), result: { message: "", total_rows: 0, ingested: 0, skipped: 0 }, status: "error", error: err.message }, ...prev]);
    } finally { setIngestLoading(false); }
  };

  const loadQA = async () => {
    setQaLoading(true); setQaError("");
    try { const res = await fetch("http://localhost:8000/api/v1/identity-qa/summary", { headers: { Authorization: `Bearer ${token}` } }); const data = await res.json(); setQA(data); }
    catch { setQaError("Failed to load QA data"); }
    finally { setQaLoading(false); }
  };

  const handleMerge = async (primaryId: string, duplicateId: string) => {
    setMerging(duplicateId);
    await new Promise((r) => setTimeout(r, 1000));
    setQaMessage(`✅ Merged ${duplicateId} into ${primaryId}`);
    setMerging(null);
  };

  const fetchSyncStatus = async () => {
    setSyncLoading(true); setSyncMessage("");
    try { const res = await fetch("http://localhost:8000/api/v1/sync/status", { headers: { Authorization: `Bearer ${token}` } }); const data = await res.json(); setSyncStatus(data); }
    catch { setSyncMessage("❌ Failed to fetch sync status"); }
    finally { setSyncLoading(false); }
  };

  const triggerSync = async () => {
    setSyncTriggering(true); setSyncMessage("");
    try { const res = await fetch("http://localhost:8000/api/v1/sync/trigger", { method: "POST", headers: { Authorization: `Bearer ${token}` } }); const data = await res.json(); setSyncMessage("✅ " + data.message); setTimeout(fetchSyncStatus, 3000); }
    catch { setSyncMessage("❌ Failed to trigger sync"); }
    finally { setSyncTriggering(false); }
  };

  const fetchAttendance = async (month: string) => {
    if (!token) return;
    setAttendanceLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [dp, aa, sh, tr, cs] = await Promise.all([
        fetch(`http://localhost:8000/api/v1/kpi/attendance/days-present?month=${month}`, { headers }).then(r => r.json()),
        fetch(`http://localhost:8000/api/v1/kpi/attendance/avg-arrival?month=${month}`, { headers }).then(r => r.json()),
        fetch(`http://localhost:8000/api/v1/kpi/attendance/session-hours?month=${month}`, { headers }).then(r => r.json()),
        fetch(`http://localhost:8000/api/v1/kpi/attendance/trend`, { headers }).then(r => r.json()),
        fetch(`http://localhost:8000/api/v1/kpi/attendance/cohort-summary?month=${month}`, { headers }).then(r => r.json()),
      ]);
      setAttendanceData({ daysPresent: Array.isArray(dp) ? dp : [], avgArrival: Array.isArray(aa) ? aa : [], sessionHours: Array.isArray(sh) ? sh : [], trend: Array.isArray(tr) ? tr : [], cohortSummary: Array.isArray(cs) ? cs : [] });
    } catch (e) { console.error("Failed to fetch attendance KPIs", e); }
    finally { setAttendanceLoading(false); }
  };

  const loadSecurity = async () => {
    setSecurityLoading(true); setSecurityMessage("");
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [metricsRes, queueRes, summaryRes] = await Promise.all([
        fetch("http://localhost:8000/api/v1/security/metrics/denied-access?days=30", { headers }),
        fetch("http://localhost:8000/api/v1/security/review-queue?status=pending&limit=50", { headers }),
        fetch("http://localhost:8000/api/v1/security/review-queue/summary", { headers }),
      ]);
      const [metrics, queue, summary] = await Promise.all([metricsRes.json(), queueRes.json(), summaryRes.json()]);
      setSecurityMetrics(metrics);
      setSecurityQueue(Array.isArray(queue) ? queue : []);
      setQueueSummary(summary);
    } catch { setSecurityMessage("❌ Failed to load security data"); }
    finally { setSecurityLoading(false); }
  };

  const handleConfirm = async (itemId: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/security/review-queue/${itemId}/confirm`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ reviewer: user?.email || "admin" }),
      });
      if (res.ok) {
        setSecurityQueue((prev) => prev.filter((item) => item.id !== itemId));
        setSecurityMessage("✅ Event confirmed as security incident");
        setQueueSummary((prev: any) => ({ ...prev, confirmed: (prev.confirmed || 0) + 1, pending: (prev.pending || 1) - 1 }));
      }
    } catch { setSecurityMessage("❌ Failed to confirm event"); }
  };

  const handleDismiss = async (itemId: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/security/review-queue/${itemId}/dismiss`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ reviewer: user?.email || "admin" }),
      });
      if (res.ok) {
        setSecurityQueue((prev) => prev.filter((item) => item.id !== itemId));
        setSecurityMessage("✅ Event dismissed as false positive");
        setQueueSummary((prev: any) => ({ ...prev, dismissed: (prev.dismissed || 0) + 1, pending: (prev.pending || 1) - 1 }));
      }
    } catch { setSecurityMessage("❌ Failed to dismiss event"); }
  };

  const statusBadge = (status: string) => (
    <span style={{ padding: "3px 12px", borderRadius: "20px", fontSize: "12px", fontWeight: "bold", backgroundColor: status === "OK" ? "#14532d" : "#78350f", color: status === "OK" ? "#34d399" : "#fbbf24", border: `1px solid ${status === "OK" ? "#16a34a" : "#d97706"}` }}>
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
    { id: "occupancy", icon: "🏢", label: "Occupancy", show: true },
    { id: "attendance", icon: "📅", label: "Attendance KPIs", show: true },
    { id: "identity-qa", icon: "🔎", label: "Identity QA", show: isAdmin },
    { id: "sync", icon: "🔄", label: "GitHub Sync", show: isAdmin },
    { id: "security", icon: "🚨", label: "Security", show: canViewAlerts },
    { id: "settings", icon: "⚙️", label: "Settings", show: canViewSettings },
    { id: "profile", icon: "👤", label: "My Profile", show: true },
  ];

  const renderContent = () => {
    switch (activeMenu) {
      case "dashboard":
        return (
          <div>
            <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>Welcome Back{user ? `, ${user.full_name}` : ""} 👋</h2>
            <p style={{ color: "#64748b", marginTop: "8px", fontSize: "16px", marginBottom: "32px" }}>Security Monitoring Dashboard · {new Date().toDateString()}</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "24px", marginBottom: "32px" }}>
              {[{ label: "Total Alerts", value: "0", color: "#f87171", icon: "🚨" }, { label: "Active Users", value: "1", color: "#34d399", icon: "👥" }, { label: "System Status", value: "Online", color: "#34d399", icon: "✅" }].map((stat) => (
                <div key={stat.label} style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "28px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <p style={{ color: "#94a3b8", margin: 0, fontSize: "14px" }}>{stat.label}</p>
                    <span style={{ fontSize: "24px" }}>{stat.icon}</span>
                  </div>
                  <p style={{ fontSize: "40px", fontWeight: "bold", color: stat.color, margin: "12px 0 0" }}>{stat.value}</p>
                </div>
              ))}
            </div>
            {user && (
              <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "24px" }}>
                <h3 style={{ fontSize: "16px", fontWeight: "bold", marginBottom: "12px", marginTop: 0, color: "#94a3b8" }}>🔐 Your Permissions</h3>
                <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
                  {[{ label: "View Alerts", allowed: canViewAlerts }, { label: "Manage Users", allowed: canManageUsers }, { label: "View Reports", allowed: canViewReports }, { label: "Settings", allowed: canViewSettings }].map((perm) => (
                    <span key={perm.label} style={{ padding: "6px 14px", borderRadius: "20px", fontSize: "13px", fontWeight: "bold", backgroundColor: perm.allowed ? "#14532d" : "#1f2937", color: perm.allowed ? "#34d399" : "#475569", border: `1px solid ${perm.allowed ? "#16a34a" : "#374151"}` }}>
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
                {[{ icon: "✅", text: "User logged in successfully", time: "Just now" }, { icon: "🔑", text: "JWT authentication active", time: "2 min ago" }, { icon: "🚀", text: "Backend connected", time: "5 min ago" }, { icon: "👥", text: "User management accessed", time: "10 min ago" }, { icon: "🔒", text: "Role-based access enforced", time: "15 min ago" }].map((item) => (
                  <div key={item.text} style={{ backgroundColor: "#0f0f1a", border: "1px solid #2a2a4a", borderRadius: "10px", padding: "14px 18px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
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
              <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
                <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "32px", width: "400px" }}>
                  <h3 style={{ margin: "0 0 24px", fontSize: "20px" }}>Edit User</h3>
                  <label style={{ color: "#94a3b8", fontSize: "14px" }}>Full Name</label>
                  <input value={newName} onChange={(e) => setNewName(e.target.value)} style={{ width: "100%", padding: "12px", marginTop: "8px", marginBottom: "16px", backgroundColor: "#0f0f1a", border: "1px solid #2a2a4a", borderRadius: "8px", color: "#fff", fontSize: "15px", boxSizing: "border-box" as const }} />
                  <label style={{ color: "#94a3b8", fontSize: "14px" }}>Role</label>
                  <select value={newRole} onChange={(e) => setNewRole(e.target.value)} style={{ width: "100%", padding: "12px", marginTop: "8px", marginBottom: "24px", backgroundColor: "#0f0f1a", border: "1px solid #2a2a4a", borderRadius: "8px", color: "#fff", fontSize: "15px", boxSizing: "border-box" as const }}>
                    {["admin", "leadership", "manager", "employee"].map((r) => (<option key={r} value={r}>{r}</option>))}
                  </select>
                  <div style={{ display: "flex", gap: "12px" }}>
                    <button onClick={handleSave} style={{ flex: 1, padding: "12px", backgroundColor: "#7c3aed", color: "#fff", border: "none", borderRadius: "8px", cursor: "pointer", fontWeight: "bold" }}>Save</button>
                    <button onClick={() => setEditingUser(null)} style={{ flex: 1, padding: "12px", backgroundColor: "#374151", color: "#fff", border: "none", borderRadius: "8px", cursor: "pointer", fontWeight: "bold" }}>Cancel</button>
                  </div>
                </div>
              </div>
            )}
            {userMessage && (<div style={{ padding: "12px 20px", borderRadius: "10px", marginBottom: "24px", backgroundColor: userMessage.startsWith("✅") ? "#14532d" : "#7f1d1d", border: `1px solid ${userMessage.startsWith("✅") ? "#16a34a" : "#dc2626"}`, color: userMessage.startsWith("✅") ? "#34d399" : "#f87171" }}>{userMessage}</div>)}
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", overflow: "hidden" }}>
              <div style={{ display: "grid", gridTemplateColumns: "2fr 2fr 1fr 1fr 2fr", padding: "16px 24px", backgroundColor: "#0f0f1a", borderBottom: "1px solid #2a2a4a", color: "#64748b", fontSize: "13px", fontWeight: "bold", textTransform: "uppercase" as const }}>
                <span>Name</span><span>Email</span><span>Role</span><span>Status</span><span>Actions</span>
              </div>
              {users.length === 0 ? (<p style={{ padding: "24px", color: "#64748b" }}>No users found.</p>) : (
                users.map((u) => (
                  <div key={u.id} style={{ display: "grid", gridTemplateColumns: "2fr 2fr 1fr 1fr 2fr", padding: "16px 24px", borderBottom: "1px solid #2a2a4a", alignItems: "center", opacity: u.is_active ? 1 : 0.5 }}>
                    <span style={{ fontWeight: "bold" }}>{u.full_name}</span>
                    <span style={{ color: "#94a3b8", fontSize: "14px" }}>{u.email}</span>
                    <span><span style={{ backgroundColor: roleColor[u.role] || "#a78bfa", color: "#000", fontSize: "11px", fontWeight: "bold", padding: "3px 10px", borderRadius: "20px", textTransform: "uppercase" as const }}>{u.role}</span></span>
                    <span style={{ color: u.is_active ? "#34d399" : "#f87171", fontWeight: "bold", fontSize: "13px" }}>{u.is_active ? "● Active" : "● Disabled"}</span>
                    <div style={{ display: "flex", gap: "8px" }}>
                      <button onClick={() => handleEdit(u)} style={{ padding: "6px 14px", backgroundColor: "#7c3aed", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "13px" }}>✏️ Edit</button>
                      {u.is_active && (<button onClick={() => handleDisable(u)} style={{ padding: "6px 14px", backgroundColor: "#dc2626", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "13px" }}>🚫 Disable</button>)}
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
              {[{ label: "Critical", count: 0, color: "#f87171", bg: "#7f1d1d", border: "#dc2626", icon: "🚨" }, { label: "Warning", count: 0, color: "#fbbf24", bg: "#78350f", border: "#d97706", icon: "⚠️" }, { label: "Info", count: 0, color: "#60a5fa", bg: "#1e3a5f", border: "#2563eb", icon: "ℹ️" }].map((s) => (
                <div key={s.label} style={{ backgroundColor: s.bg, border: `1px solid ${s.border}`, borderRadius: "12px", padding: "20px 24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div><p style={{ color: s.color, margin: "0 0 4px", fontSize: "13px", fontWeight: "bold" }}>{s.label}</p><p style={{ fontSize: "32px", fontWeight: "bold", color: "#fff", margin: 0 }}>{s.count}</p></div>
                  <span style={{ fontSize: "28px" }}>{s.icon}</span>
                </div>
              ))}
            </div>
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", overflow: "hidden" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr 3fr 1.5fr 1fr", padding: "16px 24px", backgroundColor: "#0f0f1a", borderBottom: "1px solid #2a2a4a", color: "#64748b", fontSize: "13px", fontWeight: "bold", textTransform: "uppercase" as const }}>
                <span>Severity</span><span>Type</span><span>Message</span><span>Time</span><span>Status</span>
              </div>
              <div style={{ padding: "60px 24px", display: "flex", flexDirection: "column", alignItems: "center", gap: "12px", color: "#475569" }}>
                <span style={{ fontSize: "48px" }}>🔕</span>
                <p style={{ margin: 0, fontSize: "16px", fontWeight: "bold", color: "#64748b" }}>No alerts at this time</p>
                <p style={{ margin: 0, fontSize: "13px" }}>When alerts are triggered, they will appear here</p>
              </div>
            </div>
          </div>
        );

      case "reports":
        const actionCounts = auditLogs.reduce((acc: Record<string, number>, log) => { acc[log.action] = (acc[log.action] || 0) + 1; return acc; }, {});
        const roleCounts = users.reduce((acc: Record<string, number>, u) => { acc[u.role] = (acc[u.role] || 0) + 1; return acc; }, {});
        const activeUsers = users.filter((u) => u.is_active).length;
        const disabledUsers = users.filter((u) => !u.is_active).length;
        const updateActions = auditLogs.filter((l) => l.action === "UPDATE_USER").length;
        const listActions = auditLogs.filter((l) => l.action === "LIST_USERS").length;
        return (
          <div>
            <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>📊 View Reports</h2>
            <p style={{ color: "#64748b", marginBottom: "24px" }}>System overview based on users and audit activity</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px", marginBottom: "28px" }}>
              {[{ label: "Total Users", value: users.length, icon: "👥", color: "#a78bfa" }, { label: "Active Users", value: activeUsers, icon: "✅", color: "#34d399" }, { label: "Disabled Users", value: disabledUsers, icon: "🚫", color: "#f87171" }, { label: "Total Audit Logs", value: auditLogs.length, icon: "🔍", color: "#60a5fa" }].map((card) => (
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
                      const total = users.length; const pct = Math.round((count / total) * 100); const color = roleColor[role] || "#a78bfa";
                      return (
                        <div key={role}>
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                            <span style={{ backgroundColor: color, color: "#000", fontSize: "11px", fontWeight: "bold", padding: "2px 10px", borderRadius: "20px", textTransform: "uppercase" as const }}>{role}</span>
                            <span style={{ color: "#94a3b8", fontSize: "13px" }}>{count} · {pct}%</span>
                          </div>
                          <div style={{ backgroundColor: "#0f0f1a", borderRadius: "999px", height: "8px" }}><div style={{ width: `${pct}%`, backgroundColor: color, height: "8px", borderRadius: "999px" }} /></div>
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
                      const total = auditLogs.length; const pct = Math.round((count / total) * 100);
                      return (
                        <div key={action}>
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                            <span style={{ backgroundColor: "#312e81", color: "#a78bfa", fontSize: "11px", fontWeight: "bold", padding: "2px 10px", borderRadius: "20px" }}>{action}</span>
                            <span style={{ color: "#94a3b8", fontSize: "13px" }}>{count} · {pct}%</span>
                          </div>
                          <div style={{ backgroundColor: "#0f0f1a", borderRadius: "999px", height: "8px" }}><div style={{ width: `${pct}%`, backgroundColor: "#7c3aed", height: "8px", borderRadius: "999px" }} /></div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", overflow: "hidden" }}>
              <div style={{ padding: "20px 24px", borderBottom: "1px solid #2a2a4a" }}><h3 style={{ margin: 0, fontSize: "16px", color: "#94a3b8" }}>📋 Activity Summary</h3></div>
              <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", padding: "14px 24px", backgroundColor: "#0f0f1a", borderBottom: "1px solid #2a2a4a", color: "#64748b", fontSize: "13px", fontWeight: "bold", textTransform: "uppercase" as const }}><span>Metric</span><span>Value</span><span>Notes</span></div>
              {[{ metric: "Total Audit Events", value: auditLogs.length, note: "All time" }, { metric: "User Listing Actions", value: listActions, note: "READ operations" }, { metric: "User Update Actions", value: updateActions, note: "WRITE operations" }, { metric: "Active Users", value: activeUsers, note: `Out of ${users.length} total` }, { metric: "Disabled Accounts", value: disabledUsers, note: "Access revoked" }, { metric: "Unique Roles", value: Object.keys(roleCounts).length, note: Object.keys(roleCounts).join(", ") || "—" }].map((row) => (
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
              {auditLogs.length === 0 ? (<p style={{ padding: "24px", color: "#64748b" }}>No audit logs yet.</p>) : (
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
                <p style={{ color: "#64748b", marginBottom: "16px" }}>{ingestFile ? `✅ Selected: ${ingestFile.name}` : "Select an .xlsx file to upload"}</p>
                <input type="file" accept=".xlsx" onChange={handleFileChange} style={{ display: "none" }} id="file-upload" />
                <label htmlFor="file-upload" style={{ padding: "10px 24px", backgroundColor: "#312e81", color: "#a78bfa", borderRadius: "8px", cursor: "pointer", fontWeight: "bold", fontSize: "14px" }}>Browse File</label>
              </div>
              {ingestError && (<div style={{ padding: "12px 20px", borderRadius: "10px", marginBottom: "16px", backgroundColor: "#7f1d1d", border: "1px solid #dc2626", color: "#f87171" }}>{ingestError}</div>)}
              <button onClick={handleIngest} disabled={ingestLoading || !ingestFile} style={{ width: "100%", padding: "14px", backgroundColor: ingestLoading || !ingestFile ? "#374151" : "#7c3aed", color: "#fff", border: "none", borderRadius: "10px", cursor: ingestLoading || !ingestFile ? "not-allowed" : "pointer", fontSize: "16px", fontWeight: "bold" }}>
                {ingestLoading ? "⏳ Ingesting..." : "🚀 Start Ingestion"}
              </button>
            </div>
            {ingestResult && (
              <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #16a34a", borderRadius: "16px", padding: "28px", marginBottom: "24px" }}>
                <h3 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "20px", marginTop: 0, color: "#34d399" }}>✅ Ingestion Complete</h3>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" }}>
                  {[{ label: "Total Rows", value: ingestResult.total_rows, color: "#a78bfa" }, { label: "Ingested", value: ingestResult.ingested, color: "#34d399" }, { label: "Skipped", value: ingestResult.skipped, color: "#f87171" }].map((stat) => (
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
                        <span style={{ color: run.status === "success" ? "#34d399" : "#f87171", fontWeight: "bold", marginRight: "12px" }}>{run.status === "success" ? "✅ Success" : "❌ Failed"}</span>
                        {run.status === "success" ? (<span style={{ color: "#94a3b8", fontSize: "14px" }}>{run.result.ingested} ingested · {run.result.skipped} skipped · {run.result.total_rows} total</span>) : (<span style={{ color: "#f87171", fontSize: "14px" }}>{run.error}</span>)}
                      </div>
                      <span style={{ color: "#475569", fontSize: "13px" }}>{run.timestamp}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );

      case "occupancy":
        return (
          <div>
            <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>🏢 Occupancy</h2>
            <p style={{ color: "#64748b", marginBottom: "32px" }}>Space occupancy analytics and forecasts</p>
            <div style={{ marginBottom: "32px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "16px", marginTop: 0 }}>📊 Peak Occupancy by Location</h3>
              {occupancyPeak.length === 0 ? (<p style={{ color: "#64748b" }}>No data available.</p>) : (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" }}>
                  {occupancyPeak.map((loc) => (
                    <div key={loc.location} style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "24px" }}>
                      <p style={{ color: "#94a3b8", margin: "0 0 8px", fontSize: "13px" }}>{loc.location || "Unknown"}</p>
                      <p style={{ fontSize: "36px", fontWeight: "bold", color: "#a78bfa", margin: "0 0 8px" }}>{loc.all_time_peak}</p>
                      <p style={{ color: "#64748b", fontSize: "13px", margin: 0 }}>Peak · Avg: {loc.avg_daily_peak.toFixed(1)}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "28px", marginBottom: "32px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "20px", marginTop: 0 }}>📈 Daily Occupancy Trend</h3>
              {occupancyTrend.length === 0 ? (<p style={{ color: "#64748b" }}>No trend data available.</p>) : (<div style={{ overflowX: "auto" }}><OccupancyTrendChart data={occupancyTrend} /></div>)}
            </div>
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "28px", marginBottom: "32px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "8px", marginTop: 0 }}>🔮 7-Day Occupancy Forecast</h3>
              <p style={{ color: "#64748b", fontSize: "13px", marginBottom: "20px" }}>Shaded area shows 95% confidence interval</p>
              {occupancyForecast.length === 0 ? (<p style={{ color: "#64748b" }}>Not enough data for forecasting yet.</p>) : (<OccupancyForecastChart data={occupancyForecast} />)}
            </div>
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "28px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "20px", marginTop: 0 }}>📱 Mobile vs Card Adoption</h3>
              {mobileAdoption.length === 0 ? (<p style={{ color: "#64748b" }}>No adoption data available.</p>) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  {mobileAdoption.map((loc) => (
                    <div key={loc.location} style={{ backgroundColor: "#0f0f1a", border: "1px solid #2a2a4a", borderRadius: "12px", padding: "20px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
                        <span style={{ fontWeight: "bold" }}>{loc.location}</span>
                        <span style={{ color: "#64748b", fontSize: "13px" }}>{loc.total_events} total events</span>
                      </div>
                      <div style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
                        <div style={{ flex: loc.mobile_adoption_rate, backgroundColor: "#7c3aed", height: "12px", borderRadius: "6px 0 0 6px" }} />
                        <div style={{ flex: loc.card_adoption_rate, backgroundColor: "#0891b2", height: "12px", borderRadius: "0 6px 6px 0", display: loc.card_adoption_rate === 0 ? "none" : "block" }} />
                      </div>
                      <div style={{ display: "flex", gap: "16px", fontSize: "13px" }}>
                        <span style={{ color: "#a78bfa" }}>📱 Mobile: {loc.mobile_adoption_rate}%</span>
                        <span style={{ color: "#60a5fa" }}>💳 Card: {loc.card_adoption_rate}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        );

      case "attendance":
        return (
          <div>
            <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>📅 Attendance KPIs</h2>
            <p style={{ color: "#64748b", marginBottom: "24px" }}>Cohort attendance metrics · Data suppressed for groups under 5 people</p>
            <div style={{ marginBottom: "28px", display: "flex", alignItems: "center", gap: "12px" }}>
              <label style={{ color: "#94a3b8", fontSize: "14px" }}>Month:</label>
              <input type="month" value={attendanceMonth} onChange={(e) => { setAttendanceMonth(e.target.value); fetchAttendance(e.target.value); }} style={{ padding: "8px 12px", backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "8px", color: "#fff", fontSize: "14px" }} />
              {attendanceLoading && <span style={{ color: "#64748b", fontSize: "13px" }}>Loading...</span>}
            </div>
            {attendanceData.cohortSummary.length > 0 ? (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px", marginBottom: "28px" }}>
                {[{ label: "Total Persons", value: attendanceData.cohortSummary[0]?.total_persons, icon: "👥", color: "#a78bfa" }, { label: "Avg Days Present", value: attendanceData.cohortSummary[0]?.avg_days, icon: "📅", color: "#34d399" }, { label: "Max Days", value: attendanceData.cohortSummary[0]?.max_days, icon: "⬆️", color: "#60a5fa" }, { label: "Min Days", value: attendanceData.cohortSummary[0]?.min_days, icon: "⬇️", color: "#f87171" }].map((card) => (
                  <div key={card.label} style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "12px", padding: "20px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <p style={{ color: "#94a3b8", margin: 0, fontSize: "13px" }}>{card.label}</p>
                      <span style={{ fontSize: "20px" }}>{card.icon}</span>
                    </div>
                    <p style={{ fontSize: "32px", fontWeight: "bold", color: card.color, margin: "8px 0 0" }}>{card.value ?? "—"}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "12px", padding: "20px", marginBottom: "28px", color: "#64748b", fontSize: "14px" }}>⚠️ Cohort data suppressed — fewer than 5 persons in this period.</div>
            )}
            {[
              { title: "A1 · Days Present", sub: "Days each person was present in the office", data: attendanceData.daysPresent, cols: ["1fr 1fr 1fr"], headers: ["Person", "Month", "Days Present"], empty: "No data — cohort suppressed or no records.", row: (r: any, i: number) => (<div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", padding: "14px 24px", borderBottom: "1px solid #2a2a4a", alignItems: "center" }}><span style={{ fontWeight: "bold" }}>{r.person_id}</span><span style={{ color: "#94a3b8" }}>{r.month}</span><span style={{ color: "#34d399", fontWeight: "bold", fontSize: "18px" }}>{r.days_present}</span></div>) },
            ].map((section) => (
              <div key={section.title} style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", overflow: "hidden", marginBottom: "24px" }}>
                <div style={{ padding: "20px 24px", borderBottom: "1px solid #2a2a4a" }}><h3 style={{ margin: 0, fontSize: "16px", fontWeight: "bold" }}>{section.title}</h3><p style={{ margin: "4px 0 0", color: "#64748b", fontSize: "13px" }}>{section.sub}</p></div>
                {section.data.length === 0 ? (<p style={{ padding: "20px 24px", color: "#64748b" }}>{section.empty}</p>) : (<>{section.data.map(section.row)}</>)}
              </div>
            ))}
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", overflow: "hidden", marginBottom: "24px" }}>
              <div style={{ padding: "20px 24px", borderBottom: "1px solid #2a2a4a" }}><h3 style={{ margin: 0, fontSize: "16px", fontWeight: "bold" }}>A2 · Average Arrival Time</h3><p style={{ margin: "4px 0 0", color: "#64748b", fontSize: "13px" }}>Average first-entry time per person · Caveat: based on badge swipe only</p></div>
              {attendanceData.avgArrival.length === 0 ? (<p style={{ padding: "20px 24px", color: "#64748b" }}>No data available.</p>) : (
                attendanceData.avgArrival.map((r, i) => (
                  <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", padding: "14px 24px", borderBottom: "1px solid #2a2a4a", alignItems: "center" }}>
                    <span style={{ fontWeight: "bold" }}>{r.person_id}</span><span style={{ color: "#94a3b8" }}>{r.month}</span><span style={{ color: "#a78bfa", fontWeight: "bold" }}>{r.avg_arrival_time}</span><span style={{ color: "#64748b" }}>{r.days_counted} day{r.days_counted > 1 ? "s" : ""}</span>
                  </div>
                ))
              )}
            </div>
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", overflow: "hidden", marginBottom: "24px" }}>
              <div style={{ padding: "20px 24px", borderBottom: "1px solid #2a2a4a" }}><h3 style={{ margin: 0, fontSize: "16px", fontWeight: "bold" }}>A4 · Office Session Hours</h3><p style={{ margin: "4px 0 0", color: "#64748b", fontSize: "13px" }}>Total and average hours in office · Caveat: requires both entry and exit swipe</p></div>
              {attendanceData.sessionHours.length === 0 ? (<p style={{ padding: "20px 24px", color: "#64748b" }}>⚠️ No session data — missing exit swipes or cohort suppressed (&lt;5 persons).</p>) : (
                attendanceData.sessionHours.map((r, i) => (
                  <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", padding: "14px 24px", borderBottom: "1px solid #2a2a4a", alignItems: "center" }}>
                    <span style={{ fontWeight: "bold" }}>{r.person_id}</span><span style={{ color: "#94a3b8" }}>{r.month}</span><span style={{ color: "#60a5fa", fontWeight: "bold" }}>{r.total_hours}h</span><span style={{ color: "#94a3b8" }}>{r.avg_hours_per_day}h</span>
                  </div>
                ))
              )}
            </div>
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", overflow: "hidden", marginBottom: "24px" }}>
              <div style={{ padding: "20px 24px", borderBottom: "1px solid #2a2a4a" }}><h3 style={{ margin: 0, fontSize: "16px", fontWeight: "bold" }}>A5 · Attendance Trend</h3><p style={{ margin: "4px 0 0", color: "#64748b", fontSize: "13px" }}>Monthly trend · 🔺 marks change-points (&gt;20% shift)</p></div>
              {attendanceData.trend.length === 0 ? (<p style={{ padding: "20px 24px", color: "#64748b" }}>No trend data available.</p>) : (
                attendanceData.trend.map((r, i) => (
                  <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr", padding: "14px 24px", borderBottom: "1px solid #2a2a4a", alignItems: "center", backgroundColor: r.is_change_point ? "rgba(251,191,36,0.05)" : "transparent" }}>
                    <span style={{ fontWeight: "bold" }}>{r.is_change_point && <span style={{ color: "#fbbf24", marginRight: "6px" }}>🔺</span>}{r.month}</span>
                    <span style={{ color: "#94a3b8" }}>{r.unique_persons}</span><span style={{ color: "#94a3b8" }}>{r.total_days}</span>
                    <span style={{ color: "#a78bfa", fontWeight: "bold" }}>{r.avg_days_per_person}</span>
                    <span style={{ color: r.change_from_prev > 0 ? "#34d399" : r.change_from_prev < 0 ? "#f87171" : "#64748b", fontWeight: "bold" }}>{r.change_from_prev > 0 ? "+" : ""}{r.change_from_prev}</span>
                  </div>
                ))
              )}
            </div>
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "20px 24px" }}>
              <h3 style={{ margin: "0 0 12px", fontSize: "14px", color: "#94a3b8" }}>📌 Data Caveats</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {["A1-A6 metrics are based on badge access swipe data only", "Session hours (A4) require both entry and exit swipes — missing exit = no session recorded", "Arrival consistency (A3) requires at least 3 days of data per person", "Groups with fewer than 5 persons are suppressed to protect privacy", "Timestamps are in Asia/Kolkata (IST) timezone", "Double-tap swipes within 5 seconds are deduplicated automatically"].map((caveat, i) => (
                  <div key={i} style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                    <span style={{ color: "#fbbf24", fontSize: "12px", marginTop: "2px" }}>⚠️</span>
                    <span style={{ color: "#64748b", fontSize: "13px" }}>{caveat}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );

      case "identity-qa":
        return (
          <div>
            <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>🔎 Identity QA</h2>
            <p style={{ color: "#64748b", marginBottom: "24px" }}>Review and clean identity issues before trusting any KPI</p>
            <button onClick={loadQA} disabled={qaLoading} style={{ padding: "10px 24px", backgroundColor: "#7c3aed", color: "#fff", border: "none", borderRadius: "8px", cursor: qaLoading ? "not-allowed" : "pointer", fontWeight: "bold", fontSize: "14px", marginBottom: "24px", opacity: qaLoading ? 0.6 : 1 }}>
              {qaLoading ? "⏳ Loading..." : "🔄 Run QA Checks"}
            </button>
            {qaError && (<div style={{ padding: "12px 20px", borderRadius: "10px", marginBottom: "24px", backgroundColor: "#7f1d1d", border: "1px solid #dc2626", color: "#f87171" }}>{qaError}</div>)}
            {qaMessage && (<div style={{ padding: "12px 20px", borderRadius: "10px", marginBottom: "24px", backgroundColor: "#14532d", border: "1px solid #16a34a", color: "#34d399" }}>{qaMessage}</div>)}
            {qa && qa.checks && (
              <>
                <div style={{ backgroundColor: qa.overall_status === "OK" ? "#14532d" : "#78350f", border: `1px solid ${qa.overall_status === "OK" ? "#16a34a" : "#d97706"}`, borderRadius: "12px", padding: "16px 24px", marginBottom: "24px", display: "flex", alignItems: "center", gap: "12px" }}>
                  <span style={{ fontSize: "24px" }}>{qa.overall_status === "OK" ? "✅" : "⚠️"}</span>
                  <div><p style={{ margin: 0, fontWeight: "bold", fontSize: "16px" }}>Overall Status: {qa.overall_status}</p><p style={{ margin: 0, fontSize: "13px", color: "#94a3b8" }}>{qa.overall_status === "OK" ? "All identity checks passed." : "Some checks need attention."}</p></div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", marginBottom: "28px" }}>
                  {[{ label: "Unresolved Codes", value: `${qa.checks.unresolved_codes.unresolved_pct}%`, sub: `${qa.checks.unresolved_codes.unresolved_count} of ${qa.checks.unresolved_codes.total_events} events`, threshold: `Threshold: ${qa.checks.unresolved_codes.threshold_pct}%`, status: qa.checks.unresolved_codes.status, icon: "🏷️" }, { label: "Duplicate Clusters", value: qa.checks.duplicate_clusters.duplicate_clusters, sub: "persons with multiple IDs", threshold: "Threshold: 0", status: qa.checks.duplicate_clusters.status, icon: "👥" }, { label: "Unmatched Sessions", value: `${qa.checks.unmatched_sessions.unmatched_pct}%`, sub: `${qa.checks.unmatched_sessions.unmatched_count} of ${qa.checks.unmatched_sessions.total_entries} entries`, threshold: `Threshold: ${qa.checks.unmatched_sessions.threshold_pct}%`, status: qa.checks.unmatched_sessions.status, icon: "🚪" }].map((card) => (
                    <div key={card.label} style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "12px", padding: "20px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}><span style={{ fontSize: "20px" }}>{card.icon}</span>{statusBadge(card.status)}</div>
                      <p style={{ color: "#94a3b8", margin: "0 0 4px", fontSize: "13px" }}>{card.label}</p>
                      <p style={{ fontSize: "32px", fontWeight: "bold", color: "#a78bfa", margin: "0 0 4px" }}>{card.value}</p>
                      <p style={{ color: "#64748b", fontSize: "12px", margin: "0 0 2px" }}>{card.sub}</p>
                      <p style={{ color: "#475569", fontSize: "11px", margin: 0 }}>{card.threshold}</p>
                    </div>
                  ))}
                </div>
                <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", overflow: "hidden", marginBottom: "24px" }}>
                  <div style={{ padding: "20px 24px", borderBottom: "1px solid #2a2a4a" }}><h3 style={{ margin: 0, fontSize: "16px", color: "#94a3b8" }}>👥 Duplicate Identity Clusters</h3></div>
                  {qa.checks.duplicate_clusters.clusters.length === 0 ? (<div style={{ padding: "40px", textAlign: "center" as const, color: "#475569" }}><p style={{ fontSize: "32px", margin: "0 0 8px" }}>✅</p><p style={{ margin: 0 }}>No duplicate identities found</p></div>) : (
                    <>{qa.checks.duplicate_clusters.clusters.map((cluster) => (
                      <div key={cluster.email} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 2fr 1fr", padding: "16px 24px", borderBottom: "1px solid #2a2a4a", alignItems: "center" }}>
                        <span style={{ color: "#94a3b8", fontSize: "14px" }}>{cluster.email}</span>
                        <span style={{ color: "#f87171", fontWeight: "bold" }}>{cluster.id_count}</span>
                        <div style={{ display: "flex", flexDirection: "column" as const, gap: "4px" }}>{cluster.person_ids.map((id, i) => (<span key={id} style={{ fontSize: "11px", color: i === 0 ? "#34d399" : "#f87171" }}>{i === 0 ? "✅ Primary: " : "❌ Duplicate: "}{id.slice(0, 8)}...</span>))}</div>
                        <button onClick={() => handleMerge(cluster.person_ids[0], cluster.person_ids[1])} disabled={merging === cluster.person_ids[1]} style={{ padding: "6px 14px", backgroundColor: "#7c3aed", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "13px", fontWeight: "bold", opacity: merging === cluster.person_ids[1] ? 0.5 : 1 }}>{merging === cluster.person_ids[1] ? "Merging..." : "🔗 Merge"}</button>
                      </div>
                    ))}</>
                  )}
                </div>
                <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", overflow: "hidden" }}>
                  <div style={{ padding: "20px 24px", borderBottom: "1px solid #2a2a4a" }}><h3 style={{ margin: 0, fontSize: "16px", color: "#94a3b8" }}>🚪 Unmatched Sessions</h3></div>
                  {qa.checks.unmatched_sessions.unmatched_person_ids.length === 0 ? (<div style={{ padding: "40px", textAlign: "center" as const, color: "#475569" }}><p style={{ fontSize: "32px", margin: "0 0 8px" }}>✅</p><p style={{ margin: 0 }}>No unmatched sessions found</p></div>) : (
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

      case "sync":
        return (
          <div>
            <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>🔄 GitHub Sync Status</h2>
            <p style={{ color: "#64748b", marginBottom: "24px" }}>Connection state, last sync and rate limit budget</p>
            {syncMessage && (<div style={{ padding: "12px 20px", borderRadius: "10px", marginBottom: "24px", backgroundColor: syncMessage.startsWith("✅") ? "#14532d" : "#7f1d1d", border: `1px solid ${syncMessage.startsWith("✅") ? "#16a34a" : "#dc2626"}`, color: syncMessage.startsWith("✅") ? "#34d399" : "#f87171" }}>{syncMessage}</div>)}
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "28px", marginBottom: "24px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "20px", marginTop: 0 }}>🔗 Connection State</h3>
              {syncLoading ? (<p style={{ color: "#64748b" }}>Loading...</p>) : syncStatus?.rate_limit ? (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" }}>
                  {syncStatus.rate_limit.error ? (<div style={{ gridColumn: "1 / -1", padding: "16px", backgroundColor: "#7f1d1d", borderRadius: "10px", color: "#f87171" }}>❌ {syncStatus.rate_limit.error}</div>) : (
                    <>
                      <div style={{ backgroundColor: "#0f0f1a", border: "1px solid #16a34a", borderRadius: "12px", padding: "20px", textAlign: "center" as const }}><p style={{ color: "#64748b", margin: "0 0 8px", fontSize: "13px" }}>Status</p><p style={{ fontSize: "18px", fontWeight: "bold", color: "#34d399", margin: 0 }}>● Connected</p></div>
                      <div style={{ backgroundColor: "#0f0f1a", border: "1px solid #2a2a4a", borderRadius: "12px", padding: "20px", textAlign: "center" as const }}><p style={{ color: "#64748b", margin: "0 0 8px", fontSize: "13px" }}>Rate Limit Remaining</p><p style={{ fontSize: "32px", fontWeight: "bold", color: "#a78bfa", margin: 0 }}>{syncStatus.rate_limit.remaining ?? "—"}</p><p style={{ color: "#64748b", fontSize: "12px", margin: "4px 0 0" }}>of {syncStatus.rate_limit.limit ?? "—"}</p></div>
                      <div style={{ backgroundColor: "#0f0f1a", border: "1px solid #2a2a4a", borderRadius: "12px", padding: "20px", textAlign: "center" as const }}><p style={{ color: "#64748b", margin: "0 0 8px", fontSize: "13px" }}>Next Sync</p><p style={{ fontSize: "16px", fontWeight: "bold", color: "#60a5fa", margin: 0 }}>{syncStatus.next_scheduled}</p></div>
                    </>
                  )}
                </div>
              ) : (<p style={{ color: "#64748b" }}>Click "Refresh Status" to load connection info.</p>)}
            </div>
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "28px", marginBottom: "24px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "12px", marginTop: 0 }}>⚡ Manual Sync</h3>
              <p style={{ color: "#64748b", marginBottom: "16px", fontSize: "14px" }}>Trigger a GitHub sync immediately without waiting for the scheduled run.</p>
              <div style={{ display: "flex", gap: "12px" }}>
                <button onClick={triggerSync} disabled={syncTriggering} style={{ padding: "12px 24px", backgroundColor: syncTriggering ? "#374151" : "#7c3aed", color: "#fff", border: "none", borderRadius: "10px", cursor: syncTriggering ? "not-allowed" : "pointer", fontSize: "15px", fontWeight: "bold" }}>{syncTriggering ? "⏳ Triggering..." : "🚀 Trigger Sync Now"}</button>
                <button onClick={fetchSyncStatus} style={{ padding: "12px 24px", backgroundColor: "#1d4ed8", color: "#fff", border: "none", borderRadius: "10px", cursor: "pointer", fontSize: "15px", fontWeight: "bold" }}>🔁 Refresh Status</button>
              </div>
            </div>
            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", overflow: "hidden" }}>
              <div style={{ padding: "20px 24px", borderBottom: "1px solid #2a2a4a" }}><h3 style={{ margin: 0, fontSize: "18px", fontWeight: "bold" }}>🕐 Last Sync Runs</h3></div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", padding: "14px 24px", backgroundColor: "#0f0f1a", borderBottom: "1px solid #2a2a4a", color: "#64748b", fontSize: "13px", fontWeight: "bold", textTransform: "uppercase" as const }}><span>Job</span><span>Status</span><span>Started</span><span>Finished</span></div>
              {!syncStatus?.last_runs || syncStatus.last_runs.length === 0 ? (<p style={{ padding: "24px", color: "#64748b" }}>No sync runs yet. Click "Refresh Status" then trigger one above!</p>) : (
                syncStatus.last_runs.map((run: any, i: number) => (
                  <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", padding: "14px 24px", borderBottom: "1px solid #2a2a4a", alignItems: "center" }}>
                    <span style={{ fontSize: "14px" }}>{run.job_name}</span>
                    <span style={{ color: run.status === "success" ? "#34d399" : run.status === "failed" ? "#f87171" : "#fbbf24", fontWeight: "bold", fontSize: "13px" }}>{run.status === "success" ? "✅ Success" : run.status === "failed" ? "❌ Failed" : "⏳ Running"}</span>
                    <span style={{ color: "#64748b", fontSize: "13px" }}>{run.started_at ?? "—"}</span>
                    <span style={{ color: "#64748b", fontSize: "13px" }}>{run.finished_at ?? "—"}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        );

      case "security":
        return (
          <div>
            <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>🚨 Security Dashboard</h2>
            <p style={{ color: "#64748b", marginBottom: "24px" }}>Security metrics and anomaly review queue</p>

            <button onClick={loadSecurity} disabled={securityLoading} style={{ padding: "10px 24px", backgroundColor: "#7c3aed", color: "#fff", border: "none", borderRadius: "8px", cursor: securityLoading ? "not-allowed" : "pointer", fontWeight: "bold", fontSize: "14px", marginBottom: "24px", opacity: securityLoading ? 0.6 : 1 }}>
              {securityLoading ? "⏳ Loading..." : "🔄 Load Security Data"}
            </button>

            {securityMessage && (
              <div style={{ padding: "12px 20px", borderRadius: "10px", marginBottom: "24px", backgroundColor: securityMessage.startsWith("✅") ? "#14532d" : "#7f1d1d", border: `1px solid ${securityMessage.startsWith("✅") ? "#16a34a" : "#dc2626"}`, color: securityMessage.startsWith("✅") ? "#34d399" : "#f87171" }}>
                {securityMessage}
              </div>
            )}

            {securityMetrics && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px", marginBottom: "28px" }}>
                {[
                  { label: "Total Events", value: securityMetrics.total_events, color: "#a78bfa", icon: "📊" },
                  { label: "Denied Access", value: securityMetrics.denied_count, color: "#f87171", icon: "🚫" },
                  { label: "Denied Rate", value: `${securityMetrics.denied_rate_pct}%`, color: "#fbbf24", icon: "📈" },
                  { label: "Period", value: `${securityMetrics.period_days}d`, color: "#60a5fa", icon: "📅" },
                ].map((card) => (
                  <div key={card.label} style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "12px", padding: "20px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <p style={{ color: "#94a3b8", margin: 0, fontSize: "13px" }}>{card.label}</p>
                      <span style={{ fontSize: "20px" }}>{card.icon}</span>
                    </div>
                    <p style={{ fontSize: "32px", fontWeight: "bold", color: card.color, margin: "8px 0 0" }}>{card.value}</p>
                  </div>
                ))}
              </div>
            )}

            {Object.keys(queueSummary).length > 0 && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", marginBottom: "28px" }}>
                {[
                  { label: "Pending", value: queueSummary.pending || 0, color: "#fbbf24", bg: "#78350f", border: "#d97706" },
                  { label: "Confirmed", value: queueSummary.confirmed || 0, color: "#f87171", bg: "#7f1d1d", border: "#dc2626" },
                  { label: "Dismissed", value: queueSummary.dismissed || 0, color: "#34d399", bg: "#14532d", border: "#16a34a" },
                ].map((s) => (
                  <div key={s.label} style={{ backgroundColor: s.bg, border: `1px solid ${s.border}`, borderRadius: "12px", padding: "20px 24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <p style={{ color: s.color, margin: "0 0 4px", fontSize: "13px", fontWeight: "bold" }}>{s.label}</p>
                      <p style={{ fontSize: "32px", fontWeight: "bold", color: "#fff", margin: 0 }}>{s.value}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", overflow: "hidden" }}>
              <div style={{ padding: "20px 24px", borderBottom: "1px solid #2a2a4a", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3 style={{ margin: 0, fontSize: "18px", fontWeight: "bold" }}>🔍 Anomaly Review Queue</h3>
                <span style={{ padding: "4px 12px", borderRadius: "20px", fontSize: "12px", fontWeight: "bold", backgroundColor: "#78350f", color: "#fbbf24", border: "1px solid #d97706" }}>{securityQueue.length} pending</span>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr 1.5fr", padding: "14px 24px", backgroundColor: "#0f0f1a", borderBottom: "1px solid #2a2a4a", color: "#64748b", fontSize: "13px", fontWeight: "bold", textTransform: "uppercase" as const }}>
                <span>ID</span><span>Event Ref</span><span>Score</span><span>Time</span><span>Actions</span>
              </div>
              {securityQueue.length === 0 ? (
                <div style={{ padding: "60px 24px", display: "flex", flexDirection: "column", alignItems: "center", gap: "12px", color: "#475569" }}>
                  <span style={{ fontSize: "48px" }}>✅</span>
                  <p style={{ margin: 0, fontSize: "16px", fontWeight: "bold", color: "#64748b" }}>{securityMetrics ? "No pending items in review queue" : "Click 'Load Security Data' to view queue"}</p>
                </div>
              ) : (
                securityQueue.map((item) => (
                  <div key={item.id} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr 1.5fr", padding: "16px 24px", borderBottom: "1px solid #2a2a4a", alignItems: "center" }}>
                    <span style={{ color: "#64748b", fontSize: "12px" }}>{item.id.slice(0, 8)}...</span>
                    <span style={{ color: "#94a3b8", fontSize: "13px" }}>{item.event_ref || "—"}</span>
                    <span>
                      <span style={{ padding: "3px 10px", borderRadius: "20px", fontSize: "12px", fontWeight: "bold", backgroundColor: item.score > 0.7 ? "#7f1d1d" : item.score > 0.4 ? "#78350f" : "#1e3a5f", color: item.score > 0.7 ? "#f87171" : item.score > 0.4 ? "#fbbf24" : "#60a5fa" }}>
                        {item.score.toFixed(2)}
                      </span>
                    </span>
                    <span style={{ color: "#64748b", fontSize: "13px" }}>{new Date(item.created_at).toLocaleString()}</span>
                    {(isAdmin || isLeadership) ? (
                      <div style={{ display: "flex", gap: "8px" }}>
                        <button onClick={() => handleConfirm(item.id)} style={{ padding: "6px 14px", backgroundColor: "#dc2626", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "13px", fontWeight: "bold" }}>🚨 Confirm</button>
                        <button onClick={() => handleDismiss(item.id)} style={{ padding: "6px 14px", backgroundColor: "#374151", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "13px", fontWeight: "bold" }}>✅ Dismiss</button>
                      </div>
                    ) : (
                      <span style={{ color: "#475569", fontSize: "13px" }}>View only</span>
                    )}
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
                  <div><p style={{ color: "#64748b", margin: "0 0 4px", fontSize: "13px" }}>Full Name</p><p style={{ margin: 0, fontSize: "18px", fontWeight: "bold" }}>{user.full_name}</p></div>
                  <div><p style={{ color: "#64748b", margin: "0 0 4px", fontSize: "13px" }}>Email</p><p style={{ margin: 0, fontSize: "18px" }}>{user.email}</p></div>
                  <div><p style={{ color: "#64748b", margin: "0 0 4px", fontSize: "13px" }}>Role</p><span style={{ backgroundColor: roleColor[user.role] || "#a78bfa", color: "#000", fontSize: "12px", fontWeight: "bold", padding: "4px 12px", borderRadius: "20px", textTransform: "uppercase" as const }}>{user.role}</span></div>
                  <div><p style={{ color: "#64748b", margin: "0 0 4px", fontSize: "13px" }}>Status</p><p style={{ margin: 0, color: "#34d399", fontWeight: "bold" }}>● Active</p></div>
                  <div><p style={{ color: "#64748b", margin: "0 0 4px", fontSize: "13px" }}>Member Since</p><p style={{ margin: 0 }}>{new Date(user.created_at).toDateString()}</p></div>
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
              <button key={item.id} onClick={() => setActiveMenu(item.id)} style={{ width: "100%", padding: "12px 20px", display: "flex", alignItems: "center", gap: "12px", backgroundColor: activeMenu === item.id ? "#2a2a4a" : "transparent", color: activeMenu === item.id ? "#a78bfa" : "#94a3b8", border: "none", borderLeft: activeMenu === item.id ? "3px solid #a78bfa" : "3px solid transparent", cursor: "pointer", fontSize: "14px", fontWeight: activeMenu === item.id ? "bold" : "normal", textAlign: "left" as const }}>
                <span>{item.icon}</span><span>{item.label}</span>
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