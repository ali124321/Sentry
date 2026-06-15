"use client";
import ProtectedRoute from "@/lib/auth/ProtectedRoute";
import { useAuth } from "@/lib/auth/AuthContext";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type User = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
};

const ROLES = ["admin", "leadership", "manager", "employee"];

const roleColor: Record<string, string> = {
  admin: "#f87171",
  leadership: "#fbbf24",
  manager: "#60a5fa",
  employee: "#34d399",
  leader: "#a78bfa",
};

export default function UsersPage() {
  const { token, logout } = useAuth();
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (token) {
      fetch("http://localhost:8000/api/v1/users/me", {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => res.json())
        .then((data) => {
          setCurrentUser(data);
          if (data.role !== "admin" && data.role !== "leadership") {
            router.push("/dashboard");
          }
        });

      fetch("http://localhost:8000/api/v1/users/", {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => res.json())
        .then((data) => {
          setUsers(Array.isArray(data) ? data : []);
          setLoading(false);
        });
    }
  }, [token]);

  const handleEdit = (user: User) => {
    setEditingUser(user);
    setNewName(user.full_name);
    setNewRole(user.role);
    setMessage("");
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
      setMessage("✅ User updated successfully!");
    } else {
      setMessage("❌ Failed to update user");
    }
  };

  const handleDisable = async (user: User) => {
    if (!confirm(`Disable ${user.full_name}?`)) return;
    const res = await fetch(`http://localhost:8000/api/v1/users/${user.id}/disable`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      const updated = await res.json();
      setUsers(users.map((u) => (u.id === updated.id ? updated : u)));
      setMessage(`✅ ${user.full_name} has been disabled`);
    }
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
            <button
              onClick={() => router.push("/dashboard")}
              style={{
                padding: "8px 20px",
                backgroundColor: "#1d4ed8",
                color: "#fff",
                border: "none",
                borderRadius: "8px",
                cursor: "pointer",
                fontSize: "14px",
                fontWeight: "bold",
              }}
            >
              ← Dashboard
            </button>
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
          <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>👥 User Management</h2>
          <p style={{ color: "#64748b", marginBottom: "32px" }}>Manage users, roles and access</p>

          {/* Message */}
          {message && (
            <div style={{
              padding: "12px 20px",
              borderRadius: "10px",
              marginBottom: "24px",
              backgroundColor: message.startsWith("✅") ? "#14532d" : "#7f1d1d",
              border: `1px solid ${message.startsWith("✅") ? "#16a34a" : "#dc2626"}`,
              color: message.startsWith("✅") ? "#34d399" : "#f87171",
            }}>
              {message}
            </div>
          )}

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
                    width: "100%",
                    padding: "12px",
                    marginTop: "8px",
                    marginBottom: "16px",
                    backgroundColor: "#0f0f1a",
                    border: "1px solid #2a2a4a",
                    borderRadius: "8px",
                    color: "#fff",
                    fontSize: "15px",
                    boxSizing: "border-box" as const,
                  }}
                />

                <label style={{ color: "#94a3b8", fontSize: "14px" }}>Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "12px",
                    marginTop: "8px",
                    marginBottom: "24px",
                    backgroundColor: "#0f0f1a",
                    border: "1px solid #2a2a4a",
                    borderRadius: "8px",
                    color: "#fff",
                    fontSize: "15px",
                    boxSizing: "border-box" as const,
                  }}
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>

                <div style={{ display: "flex", gap: "12px" }}>
                  <button
                    onClick={handleSave}
                    style={{
                      flex: 1,
                      padding: "12px",
                      backgroundColor: "#7c3aed",
                      color: "#fff",
                      border: "none",
                      borderRadius: "8px",
                      cursor: "pointer",
                      fontWeight: "bold",
                    }}
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setEditingUser(null)}
                    style={{
                      flex: 1,
                      padding: "12px",
                      backgroundColor: "#374151",
                      color: "#fff",
                      border: "none",
                      borderRadius: "8px",
                      cursor: "pointer",
                      fontWeight: "bold",
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Users Table */}
          {loading ? (
            <p style={{ color: "#64748b" }}>Loading users...</p>
          ) : (
            <div style={{
              backgroundColor: "#1a1a2e",
              border: "1px solid #2a2a4a",
              borderRadius: "16px",
              overflow: "hidden",
            }}>
              {/* Table Header */}
              <div style={{
                display: "grid",
                gridTemplateColumns: "2fr 2fr 1fr 1fr 2fr",
                padding: "16px 24px",
                backgroundColor: "#0f0f1a",
                borderBottom: "1px solid #2a2a4a",
                color: "#64748b",
                fontSize: "13px",
                fontWeight: "bold",
                textTransform: "uppercase" as const,
              }}>
                <span>Name</span>
                <span>Email</span>
                <span>Role</span>
                <span>Status</span>
                <span>Actions</span>
              </div>

              {/* Table Rows */}
              {users.length === 0 ? (
                <p style={{ padding: "24px", color: "#64748b" }}>No users found.</p>
              ) : (
                users.map((user) => (
                  <div key={user.id} style={{
                    display: "grid",
                    gridTemplateColumns: "2fr 2fr 1fr 1fr 2fr",
                    padding: "16px 24px",
                    borderBottom: "1px solid #2a2a4a",
                    alignItems: "center",
                    opacity: user.is_active ? 1 : 0.5,
                  }}>
                    <span style={{ fontWeight: "bold" }}>{user.full_name}</span>
                    <span style={{ color: "#94a3b8", fontSize: "14px" }}>{user.email}</span>
                    <span>
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
                    </span>
                    <span style={{
                      color: user.is_active ? "#34d399" : "#f87171",
                      fontWeight: "bold",
                      fontSize: "13px",
                    }}>
                      {user.is_active ? "● Active" : "● Disabled"}
                    </span>
                    <div style={{ display: "flex", gap: "8px" }}>
                      <button
                        onClick={() => handleEdit(user)}
                        style={{
                          padding: "6px 14px",
                          backgroundColor: "#7c3aed",
                          color: "#fff",
                          border: "none",
                          borderRadius: "6px",
                          cursor: "pointer",
                          fontSize: "13px",
                        }}
                      >
                        ✏️ Edit
                      </button>
                      {user.is_active && (
                        <button
                          onClick={() => handleDisable(user)}
                          style={{
                            padding: "6px 14px",
                            backgroundColor: "#dc2626",
                            color: "#fff",
                            border: "none",
                            borderRadius: "6px",
                            cursor: "pointer",
                            fontSize: "13px",
                          }}
                        >
                          🚫 Disable
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </main>
      </div>
    </ProtectedRoute>
  );
}