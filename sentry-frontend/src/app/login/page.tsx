"use client";
import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth/AuthContext";
import { useRouter, useSearchParams } from "next/navigation";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Handle GitHub OAuth redirect with token
  useEffect(() => {
    const token = searchParams.get("token");
    if (token) {
      login(token);
    }
  }, [searchParams]);

  const handleLogin = async () => {
    setError("");
    setLoading(true);
    const res = await fetch("http://localhost:8000/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    setLoading(false);
    if (!res.ok) {
      setError("Invalid email or password");
      return;
    }
    const data = await res.json();
    login(data.access_token);
  };

  const handleGitHubLogin = () => {
    window.location.href = "http://localhost:8000/api/v1/auth/github";
  };

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: "#f0f2f5",
      fontFamily: "Arial, sans-serif",
    }}>
      <h1 style={{
        fontSize: "48px",
        fontWeight: "bold",
        color: "#1a1a2e",
        marginBottom: "8px",
        letterSpacing: "-1px",
      }}>
        Sentry
      </h1>
      <p style={{
        fontSize: "18px",
        color: "#444",
        marginBottom: "24px",
        textAlign: "center",
        maxWidth: "400px",
      }}></p>
      <div style={{
        backgroundColor: "#ffffff",
        borderRadius: "8px",
        boxShadow: "0 2px 12px rgba(0,0,0,0.15)",
        padding: "24px",
        width: "100%",
        maxWidth: "396px",
      }}>
        {error && (
          <div style={{
            backgroundColor: "#fff0f0",
            border: "1px solid #ffcccc",
            borderRadius: "6px",
            padding: "10px",
            marginBottom: "12px",
            color: "#cc0000",
            fontSize: "14px",
            textAlign: "center",
          }}>
            {error}
          </div>
        )}
        <input
          type="email"
          placeholder="Email address"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{
            width: "100%",
            padding: "14px 16px",
            fontSize: "17px",
            border: "1px solid #dddfe2",
            borderRadius: "6px",
            marginBottom: "12px",
            boxSizing: "border-box",
            outline: "none",
          }}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleLogin()}
          style={{
            width: "100%",
            padding: "14px 16px",
            fontSize: "17px",
            border: "1px solid #dddfe2",
            borderRadius: "6px",
            marginBottom: "16px",
            boxSizing: "border-box",
            outline: "none",
          }}
        />
        <button
          onClick={handleLogin}
          disabled={loading}
          style={{
            width: "100%",
            padding: "14px",
            backgroundColor: loading ? "#6e8fc9" : "#1a1a2e",
            color: "#ffffff",
            fontSize: "18px",
            fontWeight: "bold",
            border: "none",
            borderRadius: "6px",
            cursor: loading ? "not-allowed" : "pointer",
            marginBottom: "12px",
          }}
        >
          {loading ? "Signing in..." : "Log In"}
        </button>

        {/* Divider */}
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          marginBottom: "12px",
        }}>
          <div style={{ flex: 1, height: "1px", backgroundColor: "#dddfe2" }} />
          <span style={{ color: "#888", fontSize: "13px" }}>or</span>
          <div style={{ flex: 1, height: "1px", backgroundColor: "#dddfe2" }} />
        </div>

        {/* GitHub Login Button */}
        <button
          onClick={handleGitHubLogin}
          style={{
            width: "100%",
            padding: "14px",
            backgroundColor: "#24292e",
            color: "#ffffff",
            fontSize: "16px",
            fontWeight: "bold",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "10px",
          }}
        >
          <svg height="20" viewBox="0 0 16 16" width="20" fill="white">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
          </svg>
          Continue with GitHub
        </button>
      </div>
    </div>
  );
}