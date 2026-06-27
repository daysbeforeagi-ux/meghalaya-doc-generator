"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import DownloadCard from "../../components/DownloadCard";
import ProgressBar from "../../components/ProgressBar";

type Status = "processing" | "researching" | "drafting" | "review" | "done" | "error";

interface SessionState {
  status: Status;
  error_message: string | null;
  has_deliverable: boolean;
  has_dossier: boolean;
}

const STATUS_LABELS: Record<Status, string> = {
  processing:  "Starting up…",
  researching: "Gathering verified sources…",
  drafting:    "Drafting your speech…",
  review:      "Compiling sources dossier…",
  done:        "Done",
  error:       "Something went wrong",
};

const STATUS_SUB: Partial<Record<Status, string>> = {
  researching: "Searching official sources and verifying each fact. This may take a minute.",
  drafting:    "Writing in authentic government style using only verified evidence.",
  review:      "Building the sources dossier and running factuality gate checks.",
};

export default function ReviewInner() {
  const router = useRouter();
  const params = useSearchParams();
  const sessionId = params.get("session_id");

  const [state, setState] = useState<SessionState | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      router.replace("/");
      return;
    }

    let cancelled = false;

    async function poll() {
      try {
        const res = await fetch(`/api/sessions/${sessionId}`);
        if (!res.ok) throw new Error(`Status ${res.status}`);
        const data: SessionState = await res.json();
        if (!cancelled) setState(data);
        if (data.status !== "done" && data.status !== "error") {
          setTimeout(poll, 3000);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setPollError(err instanceof Error ? err.message : "Poll failed");
        }
      }
    }

    poll();
    return () => { cancelled = true; };
  }, [sessionId, router]);

  if (!sessionId) return null;

  if (pollError) {
    return (
      <main
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "var(--bg)",
          padding: "48px 24px",
        }}
      >
        <div style={{ maxWidth: "480px", textAlign: "center" }}>
          <p style={{ color: "var(--danger)", fontSize: "17px", marginBottom: "16px" }}>
            Could not reach the server: {pollError}
          </p>
          <button
            onClick={() => router.push("/")}
            style={secondaryBtnStyle}
          >
            Start over
          </button>
        </div>
      </main>
    );
  }

  if (!state || (state.status !== "done" && state.status !== "review" && state.status !== "error")) {
    const status = (state?.status as Status) ?? "processing";
    return (
      <ProgressBar
        label={STATUS_LABELS[status] ?? "Working…"}
        sublabel={STATUS_SUB[status]}
      />
    );
  }

  if (state.status === "error") {
    return (
      <main
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "var(--bg)",
          padding: "48px 24px",
        }}
      >
        <div style={{ maxWidth: "480px", textAlign: "center" }}>
          <h2
            style={{
              fontSize: "28px",
              fontWeight: 700,
              color: "var(--text-primary)",
              marginBottom: "12px",
            }}
          >
            Generation failed
          </h2>
          <p
            style={{
              color: "var(--text-secondary)",
              fontSize: "15px",
              marginBottom: "8px",
            }}
          >
            {state.error_message || "An unexpected error occurred."}
          </p>
          <p
            style={{
              color: "var(--text-tertiary)",
              fontSize: "13px",
              marginBottom: "32px",
            }}
          >
            Session: {sessionId}
          </p>
          <button onClick={() => router.push("/")} style={secondaryBtnStyle}>
            Start over
          </button>
        </div>
      </main>
    );
  }

  // Done or review
  const needsReview = state.status === "review";

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "var(--bg)",
        padding: "64px 24px",
      }}
    >
      <div style={{ maxWidth: "640px", margin: "0 auto" }}>
        {/* Header */}
        <p
          style={{
            fontSize: "13px",
            color: "var(--text-tertiary)",
            letterSpacing: "0.04em",
            marginBottom: "16px",
            textTransform: "uppercase",
          }}
        >
          Orator
        </p>
        <h1
          style={{
            fontSize: "clamp(28px, 4vw, 40px)",
            fontWeight: 700,
            letterSpacing: "-0.02em",
            color: "var(--text-primary)",
            marginBottom: "8px",
          }}
        >
          Your draft is ready.
        </h1>
        <p
          style={{
            fontSize: "16px",
            color: "var(--text-secondary)",
            lineHeight: 1.6,
            marginBottom: "40px",
          }}
        >
          Two documents are ready for download. Review and approve before publication.
        </p>

        {needsReview && (
          <div
            style={{
              padding: "14px 18px",
              borderRadius: "12px",
              background: "color-mix(in srgb, var(--warning) 10%, var(--bg))",
              border: "1.5px solid var(--warning)",
              marginBottom: "32px",
              fontSize: "14px",
              color: "var(--text-primary)",
              lineHeight: 1.5,
            }}
          >
            <strong>Gate check flagged issues.</strong> The sources dossier lists items that require human review before publication. Please read the dossier checklist carefully.
          </div>
        )}

        {/* Downloads */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "48px" }}>
          {state.has_deliverable && (
            <DownloadCard
              title="Speech Draft"
              description="Clean prose — no inline citations. Ready for review and delivery."
              downloadUrl={`/api/sessions/${sessionId}/download/deliverable`}
              filename={`speech_${sessionId.slice(0, 12)}.docx`}
              isPrimary
            />
          )}
          {state.has_dossier && (
            <DownloadCard
              title="Sources Dossier"
              description="Every factual claim keyed to a verified source. Includes review checklist."
              downloadUrl={`/api/sessions/${sessionId}/download/dossier`}
              filename={`sources_dossier_${sessionId.slice(0, 12)}.docx`}
            />
          )}
        </div>

        {/* Human-in-loop notice (§10.10) */}
        <div
          style={{
            padding: "16px 20px",
            borderRadius: "12px",
            background: "var(--surface)",
            border: "1.5px solid var(--border)",
            fontSize: "14px",
            color: "var(--text-secondary)",
            lineHeight: 1.6,
          }}
        >
          <strong style={{ color: "var(--text-primary)" }}>This is a draft for human review.</strong>
          {" "}All factual claims are sourced, but official approval is required before publication. The sources dossier provides the evidence trail.
        </div>

        {/* Start over */}
        <div style={{ marginTop: "32px", textAlign: "center" }}>
          <button onClick={() => router.push("/")} style={secondaryBtnStyle}>
            Create another
          </button>
        </div>
      </div>
    </main>
  );
}

const secondaryBtnStyle: React.CSSProperties = {
  height: "44px",
  padding: "0 24px",
  borderRadius: "12px",
  border: "1.5px solid var(--border)",
  background: "transparent",
  color: "var(--text-primary)",
  fontSize: "15px",
  fontFamily: "inherit",
  cursor: "pointer",
};
