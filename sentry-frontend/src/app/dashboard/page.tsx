"use client";
import ProtectedRoute from "@/lib/auth/ProtectedRoute";
import { useAuth } from "@/lib/auth/AuthContext";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function Dashboard() {
  const { logout, token } = useAuth();
  const router = useRouter();
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    if (token) {
      fetch("http://localhost:8000/api/v1/users/me", {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => res.json())
        .then((data) => setUser(data));
    }
  }, [token]);

  const isAdmin = user?.role === "admin";
  const isLeadership = user?.role === "leadership";
  const isManager = user?.role === "manager";
  const isEmployee = user?.role === "employee";

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

  return (
    <ProtectedRoute>
      <div style={{ minHeight: "100vh", backgroundColor: "#0f0f1a", color: "#ffffff", fontFamily: "Arial, sans-serif" }}>

        {/* Navbar */}
        <nav style={{
          backgroundColor: "#1a1a2e",
          borderBottom: "1px solid #2a2a4a",
          padding: "16px 32px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "28px" }}>🛡️</span>
            <h1 style={{ fontSize: "22px", fontWeight: "bold", margin: 0, color: "#a78bfa" }}>Sentry</h1>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            {user && (
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ color: "#94a3b8", fontSize: "14px" }}>👤 {user.full_name}</span>
                <span style={{
                  backgroundColor: roleColor[user.role] || "#a78bfa",
                  color: "#000",
                  fontSize: "11px",
                  fontWeight: "bold",
                  padding: "3px 10px",
                  borderRadius: "20px",
                  textTransform: "uppercase" as const,
                }}>
                  {user.role}
                </span>
              </div>
            )}
            <button
              onClick={logout}
              style={{
                padding: "8px 20px",
                backgroundColor: "#dc2626",
                color: "#fff",
                border: "none",
                borderRadius: "8px",
                cursor: "pointer",
                fontSize: "14px",
                fontWeight: "bold",
              }}
            >
              Logout
            </button>
          </div>
        </nav>

        <main style={{ padding: "40px 32px" }}>

          {/* Welcome */}
          <div style={{ marginBottom: "36px" }}>
            <h2 style={{ fontSize: "36px", fontWeight: "bold", margin: 0 }}>
              Welcome Back{user ? `, ${user.full_name}` : ""} 👋
            </h2>
            <p style={{ color: "#64748b", marginTop: "8px", fontSize: "16px" }}>
              Security Monitoring Dashboard · {new Date().toDateString()}
            </p>
          </div>

          {/* Stats */}
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

          {/* Recent Activity */}
          <div style={{
            backgroundColor: "#1a1a2e",
            border: "1px solid #2a2a4a",
            borderRadius: "16px",
            padding: "28px",
            marginBottom: "32px",
          }}>
            <h3 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "20px", marginTop: 0 }}>
              📋 Recent Activity
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {[
                { icon: "✅", text: "User logged in successfully", time: "Just now" },
                { icon: "🔑", text: "JWT authentication active", time: "2 min ago" },
                { icon: "🚀", text: "Backend connected", time: "5 min ago" },
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

          {/* Quick Actions — role based */}
          <div>
            <h3 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "20px" }}>⚡ Quick Actions</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" }}>

              {canViewAlerts && (
                <button style={{
                  backgroundColor: "#1d4ed8",
                  color: "#fff",
                  border: "none",
                  borderRadius: "12px",
                  padding: "18px",
                  fontSize: "16px",
                  fontWeight: "bold",
                  cursor: "pointer",
                }}>
                  🔔 View Alerts
                </button>
              )}

              {canManageUsers && (
                <button
                  onClick={() => router.push("/users")}
                  style={{
                    backgroundColor: "#7c3aed",
                    color: "#fff",
                    border: "none",
                    borderRadius: "12px",
                    padding: "18px",
                    fontSize: "16px",
                    fontWeight: "bold",
                    cursor: "pointer",
                  }}
                >
                  👥 Manage Users
                </button>
              )}

              {canViewReports && (
                <button style={{
                  backgroundColor: "#0891b2",
                  color: "#fff",
                  border: "none",
                  borderRadius: "12px",
                  padding: "18px",
                  fontSize: "16px",
                  fontWeight: "bold",
                  cursor: "pointer",
                }}>
                  📊 View Reports
                </button>
              )}

              {canViewSettings && (
                <button style={{
                  backgroundColor: "#059669",
                  color: "#fff",
                  border: "none",
                  borderRadius: "12px",
                  padding: "18px",
                  fontSize: "16px",
                  fontWeight: "bold",
                  cursor: "pointer",
                }}>
                  ⚙️ Settings
                </button>
              )}

              <button style={{
                backgroundColor: "#475569",
                color: "#fff",
                border: "none",
                borderRadius: "12px",
                padding: "18px",
                fontSize: "16px",
                fontWeight: "bold",
                cursor: "pointer",
              }}>
                👤 My Profile
              </button>

            </div>
          </div>

          {/* Role permissions info */}
          {user && (
            <div style={{
              marginTop: "32px",
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

        </main>
      </div>
    </ProtectedRoute>
  );
}