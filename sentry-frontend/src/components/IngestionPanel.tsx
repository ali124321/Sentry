"use client";
import { useState } from "react";

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

export default function IngestionPanel({ token }: { token: string | null }) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<IngestionResult | null>(null);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<RunHistory[]>([]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected && selected.name.endsWith(".xlsx")) {
      setFile(selected);
      setError("");
    } else {
      setError("❌ Only .xlsx files are accepted");
      setFile(null);
    }
  };

  const handleIngest = async () => {
    if (!file) {
      setError("Please select a file first");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

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
      setResult(data);
      setHistory((prev) => [
        {
          timestamp: new Date().toLocaleString(),
          result: data,
          status: "success",
        },
        ...prev,
      ]);
    } catch (err: any) {
      setError(`❌ ${err.message}`);
      setHistory((prev) => [
        {
          timestamp: new Date().toLocaleString(),
          result: { message: "", total_rows: 0, ingested: 0, skipped: 0 },
          status: "error",
          error: err.message,
        },
        ...prev,
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>📥 Data Ingestion</h2>
      <p style={{ color: "#64748b", marginBottom: "32px" }}>Upload access log xlsx and trigger ingestion</p>

      {/* Upload Card */}
      <div style={{
        backgroundColor: "#1a1a2e",
        border: "1px solid #2a2a4a",
        borderRadius: "16px",
        padding: "28px",
        marginBottom: "24px",
      }}>
        <h3 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "20px", marginTop: 0 }}>
          📂 Upload File
        </h3>

        {/* File Drop Area */}
        <div style={{
          border: "2px dashed #2a2a4a",
          borderRadius: "12px",
          padding: "32px",
          textAlign: "center",
          marginBottom: "20px",
          backgroundColor: "#0f0f1a",
        }}>
          <p style={{ color: "#64748b", marginBottom: "16px" }}>
            {file ? `✅ Selected: ${file.name}` : "Select an .xlsx file to upload"}
          </p>
          <input
            type="file"
            accept=".xlsx"
            onChange={handleFileChange}
            style={{ display: "none" }}
            id="file-upload"
          />
          <label htmlFor="file-upload" style={{
            padding: "10px 24px",
            backgroundColor: "#312e81",
            color: "#a78bfa",
            borderRadius: "8px",
            cursor: "pointer",
            fontWeight: "bold",
            fontSize: "14px",
          }}>
            Browse File
          </label>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            padding: "12px 20px", borderRadius: "10px", marginBottom: "16px",
            backgroundColor: "#7f1d1d", border: "1px solid #dc2626", color: "#f87171",
          }}>
            {error}
          </div>
        )}

        {/* Ingest Button */}
        <button
          onClick={handleIngest}
          disabled={loading || !file}
          style={{
            width: "100%", padding: "14px",
            backgroundColor: loading || !file ? "#374151" : "#7c3aed",
            color: "#fff", border: "none", borderRadius: "10px",
            cursor: loading || !file ? "not-allowed" : "pointer",
            fontSize: "16px", fontWeight: "bold",
          }}
        >
          {loading ? "⏳ Ingesting..." : "🚀 Start Ingestion"}
        </button>
      </div>

      {/* Result Card */}
      {result && (
        <div style={{
          backgroundColor: "#1a1a2e",
          border: "1px solid #16a34a",
          borderRadius: "16px",
          padding: "28px",
          marginBottom: "24px",
        }}>
          <h3 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "20px", marginTop: 0, color: "#34d399" }}>
            ✅ Ingestion Complete
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" }}>
            {[
              { label: "Total Rows", value: result.total_rows, color: "#a78bfa" },
              { label: "Ingested", value: result.ingested, color: "#34d399" },
              { label: "Skipped", value: result.skipped, color: "#f87171" },
            ].map((stat) => (
              <div key={stat.label} style={{
                backgroundColor: "#0f0f1a",
                border: "1px solid #2a2a4a",
                borderRadius: "12px",
                padding: "20px",
                textAlign: "center",
              }}>
                <p style={{ color: "#64748b", margin: "0 0 8px", fontSize: "13px" }}>{stat.label}</p>
                <p style={{ fontSize: "36px", fontWeight: "bold", color: stat.color, margin: 0 }}>
                  {stat.value}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Run History */}
      {history.length > 0 && (
        <div style={{
          backgroundColor: "#1a1a2e",
          border: "1px solid #2a2a4a",
          borderRadius: "16px",
          padding: "28px",
        }}>
          <h3 style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "20px", marginTop: 0 }}>
            🕐 Run History
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {history.map((run, i) => (
              <div key={i} style={{
                backgroundColor: "#0f0f1a",
                border: `1px solid ${run.status === "success" ? "#16a34a" : "#dc2626"}`,
                borderRadius: "10px",
                padding: "14px 18px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}>
                <div>
                  <span style={{
                    color: run.status === "success" ? "#34d399" : "#f87171",
                    fontWeight: "bold",
                    marginRight: "12px",
                  }}>
                    {run.status === "success" ? "✅ Success" : "❌ Failed"}
                  </span>
                  {run.status === "success" ? (
                    <span style={{ color: "#94a3b8", fontSize: "14px" }}>
                      {run.result.ingested} ingested · {run.result.skipped} skipped · {run.result.total_rows} total
                    </span>
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
}
