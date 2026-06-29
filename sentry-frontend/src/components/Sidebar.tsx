"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/AuthContext";

const roleColor: Record<string, string> = {
  admin: "#f87171",
  leadership: "#fbbf24",
  manager: "#60a5fa",
  employee: "#34d399",
  leader: "#a78bfa",
};

interface SidebarUser {
  full_name: string;
  role: string;
}

interface SubItem {
  id: string;
  icon: string;
  label: string;
  href: string;
}

interface NavItem {
  id: string;
  icon: string;
  label: string;
  href: string;
  subItems?: SubItem[];
}

const NAV_ITEMS: NavItem[] = [
  { id: "dashboard", icon: "🏠", label: "Dashboard", href: "/dashboard" },
  {
    id: "repos",
    icon: "📦",
    label: "Repositories",
    href: "/dashboard/repos",
    subItems: [
      { id: "repos-main", icon: "📦", label: "Repositories", href: "/dashboard/repos" },
      { id: "code-quality", icon: "🛠️", label: "Code Quality", href: "/dashboard?tab=code-quality" },
      { id: "dora", icon: "🚀", label: "DORA Metrics", href: "/dashboard?tab=dora" },
      { id: "sync", icon: "🔄", label: "GitHub Sync", href: "/dashboard?tab=sync" },
    ],
  },
  {
    id: "attendance",
    icon: "📅",
    label: "Attendance",
    href: "/dashboard?tab=attendance",
    subItems: [
      { id: "attendance-main", icon: "📅", label: "Attendance KPIs", href: "/dashboard?tab=attendance" },
      { id: "occupancy", icon: "🏢", label: "Occupancy", href: "/dashboard?tab=occupancy" },
      { id: "identity-qa", icon: "🔎", label: "Identity QA", href: "/dashboard?tab=identity-qa" },
      { id: "security", icon: "🚨", label: "Security", href: "/dashboard?tab=security" },
      { id: "alerts", icon: "🔔", label: "View Alerts", href: "/dashboard?tab=alerts" },
      { id: "ingestion", icon: "📥", label: "Data Ingestion", href: "/dashboard?tab=ingestion"},
    ],
  },
  {
    id: "settings",
    icon: "⚙️",
    label: "Settings",
    href: "/dashboard?tab=settings",
    subItems: [
      { id: "activity", icon: "📋", label: "Recent Activity", href: "/dashboard?tab=activity" },
      { id: "reports", icon: "📊", label: "View Reports", href: "/dashboard?tab=reports" },
      { id: "audit", icon: "🔍", label: "Audit Logs", href: "/dashboard?tab=audit" },
      { id: "users", icon: "👥", label: "Manage Users", href: "/dashboard?tab=users" },
    ],
  },
  { id: "profile", icon: "👤", label: "My Profile", href: "/dashboard?tab=profile" },
];

export default function Sidebar({ user }: { user: SidebarUser | null }) {
  const router = useRouter();
  const { logout } = useAuth();
  const [expanded, setExpanded] = useState<string | null>(null);

  const handleClick = (item: NavItem) => {
    if (item.subItems && item.subItems.length > 0) {
      setExpanded(expanded === item.id ? null : item.id);
    } else {
      router.push(item.href);
    }
  };

  return (
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
        {NAV_ITEMS.map((item) => (
          <div key={item.id}>
            <button
              onClick={() => handleClick(item)}
              style={{ width: "100%", padding: "12px 20px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", backgroundColor: "transparent", color: "#94a3b8", border: "none", borderLeft: "3px solid transparent", cursor: "pointer", fontSize: "14px", fontWeight: "normal", textAlign: "left" as const }}
            >
              <span style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <span>{item.icon}</span><span>{item.label}</span>
              </span>
              {item.subItems && (
                <span style={{ fontSize: "11px", transform: expanded === item.id ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.15s" }}>▶</span>
              )}
            </button>
            {item.subItems && expanded === item.id && (
              <div style={{ paddingLeft: "12px" }}>
                {item.subItems.map((sub) => (
                  <button
                    key={sub.id}
                    onClick={() => router.push(sub.href)}
                    style={{ width: "100%", padding: "10px 20px 10px 32px", display: "flex", alignItems: "center", gap: "10px", backgroundColor: "transparent", color: "#94a3b8", border: "none", borderLeft: "3px solid transparent", cursor: "pointer", fontSize: "13px", textAlign: "left" as const }}
                  >
                    <span>{sub.icon}</span><span>{sub.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </nav>
      <div style={{ padding: "16px 20px", borderTop: "1px solid #2a2a4a" }}>
        <button onClick={logout} style={{ width: "100%", padding: "10px", backgroundColor: "#dc2626", color: "#fff", border: "none", borderRadius: "8px", cursor: "pointer", fontSize: "14px", fontWeight: "bold" }}>Logout</button>
      </div>
    </div>
  );
}
