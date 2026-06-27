"use client";

interface ProgressBarProps {
  label: string;
  sublabel?: string;
}

export default function ProgressBar({ label, sublabel }: ProgressBarProps) {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
        background: "var(--bg)",
      }}
    >
      <div style={{ maxWidth: "480px", width: "100%", textAlign: "center" }}>
        {/* Spinner */}
        <div
          style={{
            width: "44px",
            height: "44px",
            borderRadius: "50%",
            border: "3px solid var(--border)",
            borderTopColor: "var(--accent)",
            animation: "spin 0.8s linear infinite",
            margin: "0 auto 32px",
          }}
        />

        <style>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>

        <h2
          style={{
            fontSize: "24px",
            fontWeight: 600,
            color: "var(--text-primary)",
            marginBottom: "8px",
            letterSpacing: "-0.01em",
          }}
        >
          {label}
        </h2>

        {sublabel && (
          <p
            style={{
              fontSize: "15px",
              color: "var(--text-secondary)",
              lineHeight: 1.5,
            }}
          >
            {sublabel}
          </p>
        )}
      </div>
    </div>
  );
}
