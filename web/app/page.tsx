"use client";

import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  return (
    <main
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
      <div style={{ maxWidth: "640px", width: "100%", textAlign: "center" }}>
        {/* Wordmark */}
        <p
          style={{
            fontSize: "13px",
            fontWeight: 600,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--text-tertiary)",
            marginBottom: "32px",
          }}
        >
          Orator
        </p>

        {/* Headline */}
        <h1
          style={{
            fontSize: "clamp(32px, 5vw, 52px)",
            fontWeight: 700,
            lineHeight: 1.1,
            letterSpacing: "-0.02em",
            color: "var(--text-primary)",
            marginBottom: "16px",
          }}
        >
          Government speeches,
          <br />
          source-traced.
        </h1>

        {/* Subhead */}
        <p
          style={{
            fontSize: "18px",
            color: "var(--text-secondary)",
            lineHeight: 1.6,
            marginBottom: "48px",
            maxWidth: "480px",
            margin: "0 auto 48px",
          }}
        >
          Draft official speeches in the authentic voice of Indian government
          dignitaries — every fact verified against real sources.
        </p>

        {/* CTA */}
        <button
          onClick={() => router.push("/intake")}
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            height: "52px",
            padding: "0 36px",
            borderRadius: "14px",
            background: "var(--accent)",
            color: "#fff",
            fontSize: "17px",
            fontWeight: 600,
            border: "none",
            cursor: "pointer",
            transition: "background 200ms ease-out, transform 200ms ease-out",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background =
              "var(--accent-hover)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background =
              "var(--accent)";
          }}
        >
          Start creating
        </button>

        {/* Trust signals */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            gap: "32px",
            marginTop: "64px",
            flexWrap: "wrap",
          }}
        >
          {[
            "Verifiable sources",
            "Clean prose",
            "Sources dossier",
          ].map((label) => (
            <p
              key={label}
              style={{
                fontSize: "13px",
                color: "var(--text-tertiary)",
                margin: 0,
              }}
            >
              {label}
            </p>
          ))}
        </div>
      </div>
    </main>
  );
}
