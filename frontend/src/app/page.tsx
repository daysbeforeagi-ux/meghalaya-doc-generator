"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleStart() {
    setLoading(true);
    setError(null);
    try {
      const session = await api.createSession();
      router.push(`/flow/${session.session_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setLoading(false);
    }
  }

  return (
    <main className="min-h-dvh flex flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-prose text-center">
        <p className="text-sm font-medium tracking-widest uppercase mb-6"
           style={{ color: "var(--fg-secondary)" }}>
          Government Content Studio
        </p>

        <h1
          className="text-5xl sm:text-6xl font-semibold leading-tight tracking-tight mb-6"
          style={{ color: "var(--fg)" }}
        >
          Orator
        </h1>

        <p
          className="text-xl leading-relaxed mb-12 mx-auto"
          style={{ color: "var(--fg-secondary)", maxWidth: "520px" }}
        >
          Speeches and press releases that are stylistically authentic,
          factually airtight, and fully source-traceable.
        </p>

        <button
          onClick={handleStart}
          disabled={loading}
          className="inline-flex items-center gap-2 px-8 py-4 rounded-full text-white font-medium text-base transition-all duration-250 disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            background: loading ? "var(--fg-secondary)" : "var(--accent)",
          }}
          onMouseEnter={e => {
            if (!loading) (e.currentTarget as HTMLButtonElement).style.background = "var(--accent-hover)";
          }}
          onMouseLeave={e => {
            if (!loading) (e.currentTarget as HTMLButtonElement).style.background = "var(--accent)";
          }}
        >
          {loading ? (
            <>
              <Spinner />
              Starting…
            </>
          ) : (
            "Get started"
          )}
        </button>

        {error && (
          <p className="mt-6 text-sm" style={{ color: "#ff3b30" }}>
            {error}
          </p>
        )}

        <div className="mt-20 pt-8 border-t flex flex-col sm:flex-row gap-8 text-sm justify-center"
             style={{ borderColor: "var(--border)", color: "var(--fg-secondary)" }}>
          <Feature icon="✦" text="One question at a time" />
          <Feature icon="✦" text="Every fact verified at source" />
          <Feature icon="✦" text="Clean draft + Sources Dossier" />
        </div>
      </div>
    </main>
  );
}

function Feature({ icon, text }: { icon: string; text: string }) {
  return (
    <span className="flex items-center gap-2">
      <span style={{ color: "var(--accent)" }}>{icon}</span>
      {text}
    </span>
  );
}

function Spinner() {
  return (
    <svg
      className="animate-spin h-4 w-4"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
