"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { SessionPublic, SessionStatus } from "@/types/session";

const STATUS_LABELS: Record<SessionStatus, string> = {
  intake: "Preparing…",
  researching: "Gathering verified sources…",
  drafting: "Drafting…",
  review: "Compiling Sources Dossier…",
  done: "Ready",
  error: "Something went wrong",
};

const STATUS_SUBLABELS: Record<SessionStatus, string> = {
  intake: "Setting up your session.",
  researching:
    "Searching official and verified sources for every factual claim in the brief.",
  drafting:
    "Applying the house style profile and composing the draft against vetted evidence only.",
  review:
    "Binding each claim to its source and producing the review checklist.",
  done: "Your draft and Sources Dossier are ready for download.",
  error: "",
};

export default function OutputPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const router = useRouter();

  const [session, setSession] = useState<SessionPublic | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const s = await api.getSession(sessionId);
        if (!cancelled) {
          setSession(s);
          if (s.status !== "review" && s.status !== "done" && s.status !== "error") {
            setTimeout(poll, 2500);
          }
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load session.");
        }
      }
    }

    poll();
    return () => { cancelled = true; };
  }, [sessionId]);

  const isDone = session?.status === "review" || session?.status === "done";
  const isError = session?.status === "error";
  const status = session?.status ?? "intake";

  return (
    <div className="min-h-dvh flex flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-4 border-b"
           style={{ borderColor: "var(--border)" }}>
        <button
          onClick={() => router.push("/")}
          className="font-semibold tracking-tight"
          style={{ color: "var(--fg)" }}
        >
          Orator
        </button>
        {session && (
          <span className="text-xs font-mono px-2 py-1 rounded" style={{ background: "var(--bg-secondary)", color: "var(--fg-secondary)" }}>
            {sessionId}
          </span>
        )}
      </div>

      <main className="flex-1 flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-prose">
          {error && (
            <div className="mb-6 px-4 py-3 rounded-xl text-sm"
                 style={{ background: "#fff0f0", color: "#c00", border: "1px solid #fcc" }}>
              {error}
            </div>
          )}

          {/* Status card */}
          <div className="rounded-2xl p-8 border" style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
            {!isDone && !isError && (
              <div className="flex items-center gap-3 mb-6">
                <PulsingDot />
                <span className="text-sm font-medium" style={{ color: "var(--accent)" }}>
                  In progress
                </span>
              </div>
            )}

            {isError ? (
              <div>
                <h2 className="text-2xl font-semibold mb-3" style={{ color: "var(--fg)" }}>
                  Generation failed
                </h2>
                <p className="text-sm mb-6" style={{ color: "var(--fg-secondary)" }}>
                  {session?.error_message || "An unexpected error occurred."}
                </p>
                <button
                  onClick={() => router.push(`/flow/${sessionId}`)}
                  className="px-6 py-3 rounded-full text-white font-medium"
                  style={{ background: "var(--accent)" }}
                >
                  Try again
                </button>
              </div>
            ) : (
              <div>
                <h2 className="text-2xl font-semibold mb-2" style={{ color: "var(--fg)" }}>
                  {STATUS_LABELS[status]}
                </h2>
                <p className="text-base mb-8" style={{ color: "var(--fg-secondary)" }}>
                  {STATUS_SUBLABELS[status]}
                </p>

                {/* Progress steps */}
                <StatusTimeline status={status} />
              </div>
            )}
          </div>

          {/* Download area */}
          {isDone && (
            <div className="mt-6 space-y-3">
              <Notice />
              <div className="grid sm:grid-cols-2 gap-3">
                <DownloadCard
                  title="Draft Deliverable"
                  subtitle="Clean prose, no citations"
                  icon="📄"
                  href={api.downloadUrl(sessionId, "deliverable")}
                  primary
                />
                <DownloadCard
                  title="Sources Dossier"
                  subtitle="Evidence records & review checklist"
                  icon="🗂"
                  href={api.downloadUrl(sessionId, "dossier")}
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => router.push(`/flow/${sessionId}`)}
                  className="text-sm px-5 py-2.5 rounded-full font-medium transition-all duration-200"
                  style={{ background: "var(--bg-secondary)", color: "var(--fg-secondary)" }}
                >
                  Regenerate
                </button>
                <button
                  onClick={() => router.push("/")}
                  className="text-sm px-5 py-2.5 rounded-full font-medium transition-all duration-200"
                  style={{ color: "var(--fg-secondary)" }}
                >
                  New document
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

const TIMELINE_STEPS: { key: SessionStatus; label: string }[] = [
  { key: "researching", label: "Gathering verified sources" },
  { key: "drafting", label: "Drafting against evidence" },
  { key: "review", label: "Compiling Sources Dossier" },
];

function StatusTimeline({ status }: { status: SessionStatus }) {
  const order: SessionStatus[] = ["researching", "drafting", "review", "done"];
  const currentIdx = order.indexOf(status);

  return (
    <div className="space-y-3">
      {TIMELINE_STEPS.map((s, i) => {
        const done = currentIdx > i;
        const active = currentIdx === i;
        return (
          <div key={s.key} className="flex items-center gap-3 text-sm">
            <div
              className="w-5 h-5 rounded-full flex items-center justify-center shrink-0 text-xs"
              style={{
                background: done ? "var(--accent)" : active ? "color-mix(in srgb, var(--accent) 20%, var(--bg))" : "var(--border)",
                color: done ? "#fff" : active ? "var(--accent)" : "var(--fg-secondary)",
              }}
            >
              {done ? "✓" : i + 1}
            </div>
            <span style={{ color: active ? "var(--fg)" : done ? "var(--fg-secondary)" : "var(--fg-secondary)", fontWeight: active ? 500 : 400 }}>
              {s.label}
              {active && <span className="ml-2 inline-flex gap-0.5">{["·", "·", "·"].map((d, i) => (
                <span key={i} className="animate-bounce" style={{ animationDelay: `${i * 0.15}s` }}>{d}</span>
              ))}</span>}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function DownloadCard({
  title,
  subtitle,
  icon,
  href,
  primary,
}: {
  title: string;
  subtitle: string;
  icon: string;
  href: string;
  primary?: boolean;
}) {
  return (
    <a
      href={href}
      download
      className="flex items-center gap-4 px-5 py-4 rounded-2xl border transition-all duration-200 no-underline"
      style={{
        borderColor: primary ? "var(--accent)" : "var(--border)",
        background: primary ? "color-mix(in srgb, var(--accent) 8%, var(--bg))" : "var(--bg-secondary)",
        color: "var(--fg)",
      }}
    >
      <span className="text-2xl">{icon}</span>
      <div>
        <div className="font-medium text-sm">{title}</div>
        <div className="text-xs mt-0.5" style={{ color: "var(--fg-secondary)" }}>
          {subtitle}
        </div>
      </div>
    </a>
  );
}

function Notice() {
  return (
    <div
      className="px-4 py-3 rounded-xl text-sm"
      style={{ background: "color-mix(in srgb, #ff9f0a 10%, var(--bg))", color: "var(--fg)", border: "1px solid color-mix(in srgb, #ff9f0a 30%, transparent)" }}
    >
      <strong>For human review before use.</strong> This is a machine-generated
      draft. Verify facts against the Sources Dossier before publishing or
      delivering.
    </div>
  );
}

function PulsingDot() {
  return (
    <span className="relative flex h-2.5 w-2.5">
      <span
        className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
        style={{ background: "var(--accent)" }}
      />
      <span
        className="relative inline-flex rounded-full h-2.5 w-2.5"
        style={{ background: "var(--accent)" }}
      />
    </span>
  );
}
