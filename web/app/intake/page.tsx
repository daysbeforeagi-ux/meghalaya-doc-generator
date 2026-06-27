"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Question from "../../components/Question";

type LengthTarget =
  | "100-150"
  | "150-500"
  | "500-750"
  | "750-1250"
  | ">1250"
  | "as_per_content";

interface FormState {
  speaker_role: string;
  speaker_name: string;
  brief: string;
  length_target: LengthTarget;
}

const STEPS = ["speaker", "speaker_name", "brief", "length"] as const;
type Step = (typeof STEPS)[number];

const SPEAKER_OPTIONS = [
  { label: "Honourable Chief Minister", value: "cm" },
  { label: "Honourable Governor", value: "governor" },
  { label: "Honourable Deputy Chief Minister", value: "deputy_cm" },
  { label: "Other (specify below)", value: "other" },
];

const LENGTH_OPTIONS = [
  { label: "100–150 words", value: "100-150" },
  { label: "150–500 words", value: "150-500" },
  { label: "500–750 words", value: "500-750" },
  { label: "750–1,250 words", value: "750-1250" },
  { label: "Over 1,250 words", value: ">1250" },
  { label: "As per verified content available", value: "as_per_content" },
];

export default function IntakePage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("speaker");
  const [form, setForm] = useState<FormState>({
    speaker_role: "",
    speaker_name: "",
    brief: "",
    length_target: "500-750",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stepIndex = STEPS.indexOf(step) + 1;
  const visibleSteps = form.speaker_role === "other" ? 4 : 3;

  function update(field: keyof FormState, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          speaker_role: form.speaker_role || "cm",
          speaker_name: form.speaker_name || null,
          brief: form.brief,
          length_target: form.length_target,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Server error ${res.status}`);
      }
      const { session_id } = await res.json();
      router.push(`/review?session_id=${session_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setSubmitting(false);
    }
  }

  if (submitting) {
    return (
      <main
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "var(--bg)",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "50%",
              border: "3px solid var(--border)",
              borderTopColor: "var(--accent)",
              animation: "spin 0.8s linear infinite",
              margin: "0 auto 24px",
            }}
          />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          <p style={{ color: "var(--text-secondary)", fontSize: "17px" }}>
            Starting…
          </p>
        </div>
      </main>
    );
  }

  if (step === "speaker") {
    return (
      <>
        {error && (
          <div
            style={{
              position: "fixed",
              top: "16px",
              left: "50%",
              transform: "translateX(-50%)",
              background: "#ff3b30",
              color: "#fff",
              padding: "10px 20px",
              borderRadius: "10px",
              fontSize: "14px",
              zIndex: 100,
            }}
          >
            {error}
          </div>
        )}
        <Question
          step={1}
          totalSteps={visibleSteps}
          question="Who is the speaker?"
          hint="Select the dignitary delivering this speech."
          type="choice"
          options={SPEAKER_OPTIONS}
          value={form.speaker_role}
          onChange={(v) => update("speaker_role", v)}
          onNext={() =>
            setStep(form.speaker_role === "other" ? "speaker_name" : "brief")
          }
          nextLabel="Continue"
        />
      </>
    );
  }

  if (step === "speaker_name") {
    return (
      <Question
        step={2}
        totalSteps={visibleSteps}
        question="What is the speaker's name and title?"
        hint="Provide the full name and designation so we can research their background."
        type="text"
        value={form.speaker_name}
        onChange={(v) => update("speaker_name", v)}
        onNext={() => setStep("brief")}
        onBack={() => setStep("speaker")}
        nextLabel="Continue"
      />
    );
  }

  if (step === "brief") {
    return (
      <Question
        step={form.speaker_role === "other" ? 3 : 2}
        totalSteps={visibleSteps}
        question="What is this speech about?"
        hint="Describe the occasion, the key points you want covered, and the audience. The more specific you are, the better the research and draft will be."
        type="textarea"
        value={form.brief}
        onChange={(v) => update("brief", v)}
        onNext={() => setStep("length")}
        onBack={() =>
          setStep(form.speaker_role === "other" ? "speaker_name" : "speaker")
        }
        nextLabel="Continue"
      />
    );
  }

  if (step === "length") {
    return (
      <Question
        step={form.speaker_role === "other" ? 4 : 3}
        totalSteps={visibleSteps}
        question="How long should the speech be?"
        hint="One A4 page is approximately 350–500 words. 'As per verified content available' lets the evidence set the length — nothing will be padded or invented."
        type="choice"
        options={LENGTH_OPTIONS}
        value={form.length_target}
        onChange={(v) => update("length_target", v as LengthTarget)}
        onNext={submit}
        onBack={() => setStep("brief")}
        nextLabel="Generate speech"
      />
    );
  }

  return null;
}
