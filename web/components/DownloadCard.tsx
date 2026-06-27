"use client";

interface DownloadCardProps {
  title: string;
  description: string;
  downloadUrl: string;
  filename: string;
  isPrimary?: boolean;
}

export default function DownloadCard({
  title,
  description,
  downloadUrl,
  filename,
  isPrimary = false,
}: DownloadCardProps) {
  return (
    <div
      style={{
        padding: "24px",
        borderRadius: "16px",
        border: `1.5px solid ${isPrimary ? "var(--accent)" : "var(--border)"}`,
        background: isPrimary
          ? "color-mix(in srgb, var(--accent) 6%, var(--bg))"
          : "var(--surface)",
        boxShadow: "var(--shadow-sm)",
        display: "flex",
        flexDirection: "column",
        gap: "16px",
      }}
    >
      {/* Doc icon + title */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
        <div
          style={{
            width: "36px",
            height: "36px",
            borderRadius: "8px",
            background: isPrimary ? "var(--accent)" : "var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke={isPrimary ? "#fff" : "var(--text-secondary)"}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
        </div>

        <div>
          <h3
            style={{
              fontSize: "17px",
              fontWeight: 600,
              color: "var(--text-primary)",
              margin: 0,
              marginBottom: "4px",
            }}
          >
            {title}
          </h3>
          <p
            style={{
              fontSize: "14px",
              color: "var(--text-secondary)",
              margin: 0,
              lineHeight: 1.4,
            }}
          >
            {description}
          </p>
        </div>
      </div>

      {/* Download button */}
      <a
        href={downloadUrl}
        download={filename}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "8px",
          height: "44px",
          borderRadius: "10px",
          background: isPrimary ? "var(--accent)" : "transparent",
          border: isPrimary ? "none" : "1.5px solid var(--border)",
          color: isPrimary ? "#fff" : "var(--text-primary)",
          fontSize: "15px",
          fontWeight: 600,
          fontFamily: "inherit",
          textDecoration: "none",
          cursor: "pointer",
          transition: "all 200ms ease-out",
        }}
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
        Download .docx
      </a>
    </div>
  );
}
