"use client";
import { useState } from "react";
import { useAuth } from "@/lib/auth/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

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
    login(data.access_token); // uses AuthContext to save token and redirect
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "#f0f2f5",
        fontFamily: "Arial, sans-serif",
      }}
    >
      <h1
        style={{
          fontSize: "48px",
          fontWeight: "bold",
          color: "#1a1a2e",
          marginBottom: "8px",
          letterSpacing: "-1px",
        }}
      >
        Sentry
      </h1>
      <p
        style={{
          fontSize: "18px",
          color: "#444",
          marginBottom: "24px",
          textAlign: "center",
          maxWidth: "400px",
        }}
      >

      </p>

      <div
        style={{
          backgroundColor: "#ffffff",
          borderRadius: "8px",
          boxShadow: "0 2px 12px rgba(0,0,0,0.15)",
          padding: "24px",
          width: "100%",
          maxWidth: "396px",
        }}
      >
        {error && (
          <div
            style={{
              backgroundColor: "#fff0f0",
              border: "1px solid #ffcccc",
              borderRadius: "6px",
              padding: "10px",
              marginBottom: "12px",
              color: "#cc0000",
              fontSize: "14px",
              textAlign: "center",
            }}
          >
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
          }}
        >
          {loading ? "Signing in..." : "Log In"}
        </button>
      </div>
    </div>
  );
}