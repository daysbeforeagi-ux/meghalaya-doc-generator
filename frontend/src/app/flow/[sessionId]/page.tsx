"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { DocType, IntakePayload, LengthTarget, SessionPublic, SpeakerRole } from "@/types/session";

// ─── Step definitions ────────────────────────────────────────────────────────

type Step =
  | "doc_type"
  | "speaker_role"
  | "speaker_name"
  | "use_pictures"
  | "brief"
  | "length_target"
  | "upload"
  | "confirm";

interface FlowState {
  doc_type: DocType | null;
  speaker_role: SpeakerRole | null;
  speaker_name: string;
  use_pictures: boolean | null;
  brief: string;
  length_target: LengthTarget | null;
  uploads: File[];
}

const LENGTH_OPTIONS: { value: LengthTarget; label: string; hint: string }[] = [
  { value: "100-150", label: "100 – 150 words", hint: "Short statement" },
  { value: "150-500", label: "150 – 500 words", hint: "One page or less" },
  { value: "500-750", label: "500 – 750 words", hint: "Full single A4 page" },
  { value: "750-1250", label: "750 – 1,250 words", hint: "Two–three pages" },
  { value: "1250+", label: "More than 1,250 words", hint: "Extended address" },
  {
    value: "quality-based",
    label: "As per quality content available",
    hint: "Length follows verified evidence",
  },
];

// ─── Main component ───────────────────────────────────────────────────────────

export default function FlowPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const router = useRouter();

  const [step, setStep] = useState<Step>("doc_type");
  const [state, setState] = useState<FlowState>({
    doc_type: null,
    speaker_role: null,
    speaker_name: "",
    use_pictures: null,
    brief: "",
    length_target: null,
    uploads: [],
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visible, setVisible] = useState(true);

  const steps: Step[] =
    state.doc_type === "speech"
      ? ["doc_type", "speaker_role", ...(state.speaker_role === "other" ? ["speaker_name" as Step] : []), "brief", "length_target", "upload", "confirm"]
      : state.doc_type === "press_release"
      ? ["doc_type", "use_pictures", "brief", "length_target", "upload", "confirm"]
      : ["doc_type"];

  const currentIndex = steps.indexOf(step);
  const progress = steps.length > 1 ? (currentIndex / (steps.length - 1)) * 100 : 0;

  function transition(nextStep: Step) {
    setVisible(false);
    setTimeout(() => {
      setStep(nextStep);
      setVisible(true);
    }, 200);
  }

  function nextStep() {
    const idx = steps.indexOf(step);
    if (idx < steps.length - 1) transition(steps[idx + 1]);
  }

  function prevStep() {
    const idx = steps.indexOf(step);
    if (idx > 0) transition(steps[idx - 1]);
  }

  async function save(payload: IntakePayload) {
    setSaving(true);
    setError(null);
    try {
      await api.submitIntake(sessionId, payload);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  async function handleGenerate() {
    setSaving(true);
    setError(null);
    try {
      // Upload any queued files
      for (const file of state.uploads) {
        await api.uploadFile(sessionId, file);
      }
      await api.generate(sessionId);
      router.push(`/output/${sessionId}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start generation.");
      setSaving(false);
    }
  }

  // ─── Step renderers ─────────────────────────────────────────────────────

  function renderStep() {
    switch (step) {
      case "doc_type":
        return (
          <ChoiceStep
            question="What would you like to create today?"
            choices={[
              { value: "speech", label: "Speech", hint: "Draft in the speaker's authentic voice" },
              { value: "press_release", label: "Press Release", hint: "Formal release for media distribution" },
            ]}
            selected={state.doc_type}
            onSelect={async (v) => {
              const val = v as DocType;
              setState((s) => ({ ...s, doc_type: val }));
              await save({ doc_type: val });
              nextStep();
            }}
          />
        );

      case "speaker_role":
        return (
          <ChoiceStep
            question="Who is the speaker?"
            hint="Optional — skip to proceed without a specific speaker."
            choices={[
              { value: "cm", label: "Honorable Chief Minister", hint: "" },
              { value: "governor", label: "Honorable Governor", hint: "" },
              { value: "deputy_cm", label: "Honorable Deputy Chief Minister", hint: "" },
              { value: "other", label: "Other…", hint: "You will be asked to specify" },
            ]}
            selected={state.speaker_role}
            onSelect={async (v) => {
              const val = v as SpeakerRole;
              setState((s) => ({ ...s, speaker_role: val }));
              await save({ speaker_role: val });
              nextStep();
            }}
            onSkip={nextStep}
          />
        );

      case "speaker_name":
        return (
          <TextStep
            question="Please specify the speaker's name or designation."
            value={state.speaker_name}
            placeholder="e.g. Dr. A. Sample, Secretary, Dept. of Health"
            onChange={(v) => setState((s) => ({ ...s, speaker_name: v }))}
            onNext={async () => {
              await save({ speaker_name: state.speaker_name });
              nextStep();
            }}
            onBack={prevStep}
          />
        );

      case "use_pictures":
        return (
          <ChoiceStep
            question="Include pictures in the press release?"
            hint="Optional — you can upload images in the next steps."
            choices={[
              { value: "yes", label: "Yes", hint: "I will upload images" },
              { value: "no", label: "No", hint: "Text only" },
            ]}
            selected={state.use_pictures === null ? null : state.use_pictures ? "yes" : "no"}
            onSelect={async (v) => {
              const val = v === "yes";
              setState((s) => ({ ...s, use_pictures: val }));
              await save({ use_pictures: val });
              nextStep();
            }}
            onSkip={nextStep}
          />
        );

      case "brief":
        return (
          <TextStep
            question="Briefly describe what this should be about."
            value={state.brief}
            placeholder="e.g. Inauguration of the new district hospital — emphasise rural access and the 200-bed capacity."
            multiline
            onChange={(v) => setState((s) => ({ ...s, brief: v }))}
            onNext={async () => {
              if (!state.brief.trim()) {
                setError("Please provide a brief before continuing.");
                return;
              }
              await save({ brief: state.brief });
              nextStep();
            }}
            onBack={prevStep}
          />
        );

      case "length_target":
        return (
          <ChoiceStep
            question="How long should the output be?"
            choices={LENGTH_OPTIONS.map((o) => ({
              value: o.value,
              label: o.label,
              hint: o.hint,
            }))}
            selected={state.length_target}
            onSelect={async (v) => {
              const val = v as LengthTarget;
              setState((s) => ({ ...s, length_target: val }));
              await save({ length_target: val });
              nextStep();
            }}
            onBack={prevStep}
          />
        );

      case "upload":
        return (
          <UploadStep
            usePictures={state.use_pictures ?? false}
            uploads={state.uploads}
            onFilesChange={(files) => setState((s) => ({ ...s, uploads: files }))}
            onNext={nextStep}
            onBack={prevStep}
          />
        );

      case "confirm":
        return (
          <ConfirmStep
            state={state}
            saving={saving}
            onBack={prevStep}
            onGenerate={handleGenerate}
          />
        );
    }
  }

  return (
    <div className="min-h-dvh flex flex-col">
      {/* Progress bar */}
      <div className="h-0.5 w-full" style={{ background: "var(--border)" }}>
        <div
          className="h-full transition-all duration-500"
          style={{ width: `${progress}%`, background: "var(--accent)" }}
        />
      </div>

      {/* Step counter */}
      <div className="flex items-center justify-between px-6 py-4 text-sm"
           style={{ color: "var(--fg-secondary)" }}>
        <button
          onClick={() => router.push("/")}
          className="font-semibold tracking-tight"
          style={{ color: "var(--fg)" }}
        >
          Orator
        </button>
        <span>
          {currentIndex + 1} / {steps.length}
        </span>
      </div>

      {/* Main content */}
      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div
          className="w-full max-w-prose transition-all duration-200"
          style={{ opacity: visible ? 1 : 0, transform: visible ? "translateY(0)" : "translateY(8px)" }}
        >
          {error && (
            <div className="mb-6 px-4 py-3 rounded-xl text-sm"
                 style={{ background: "#fff0f0", color: "#c00", border: "1px solid #fcc" }}>
              {error}
            </div>
          )}
          {renderStep()}
        </div>
      </main>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function ChoiceStep({
  question,
  hint,
  choices,
  selected,
  onSelect,
  onSkip,
  onBack,
}: {
  question: string;
  hint?: string;
  choices: { value: string; label: string; hint: string }[];
  selected: string | null;
  onSelect: (v: string) => void;
  onSkip?: () => void;
  onBack?: () => void;
}) {
  return (
    <div>
      <Question text={question} hint={hint} />
      <div className="grid gap-3 mt-8">
        {choices.map((c) => (
          <button
            key={c.value}
            onClick={() => onSelect(c.value)}
            className="w-full text-left px-5 py-4 rounded-2xl border transition-all duration-200 flex items-center justify-between group"
            style={{
              borderColor: selected === c.value ? "var(--accent)" : "var(--border)",
              background: selected === c.value ? "color-mix(in srgb, var(--accent) 8%, var(--bg))" : "var(--bg-secondary)",
              color: "var(--fg)",
            }}
          >
            <div>
              <div className="font-medium">{c.label}</div>
              {c.hint && (
                <div className="text-sm mt-0.5" style={{ color: "var(--fg-secondary)" }}>
                  {c.hint}
                </div>
              )}
            </div>
            {selected === c.value && (
              <span style={{ color: "var(--accent)" }}>✓</span>
            )}
          </button>
        ))}
      </div>
      <div className="flex gap-3 mt-6">
        {onBack && <BackButton onClick={onBack} />}
        {onSkip && (
          <button
            onClick={onSkip}
            className="text-sm px-4 py-2 rounded-full"
            style={{ color: "var(--fg-secondary)" }}
          >
            Skip
          </button>
        )}
      </div>
    </div>
  );
}

function TextStep({
  question,
  hint,
  value,
  placeholder,
  multiline,
  onChange,
  onNext,
  onBack,
}: {
  question: string;
  hint?: string;
  value: string;
  placeholder: string;
  multiline?: boolean;
  onChange: (v: string) => void;
  onNext: () => void;
  onBack?: () => void;
}) {
  const ref = useRef<HTMLTextAreaElement & HTMLInputElement>(null);
  useEffect(() => { ref.current?.focus(); }, []);

  const inputClass =
    "w-full px-4 py-3 rounded-xl border text-base outline-none transition-all duration-200 resize-none";
  const inputStyle = {
    borderColor: "var(--border)",
    background: "var(--bg-secondary)",
    color: "var(--fg)",
  };

  return (
    <div>
      <Question text={question} hint={hint} />
      <div className="mt-8">
        {multiline ? (
          <textarea
            ref={ref as React.RefObject<HTMLTextAreaElement>}
            rows={5}
            className={inputClass}
            style={inputStyle}
            placeholder={placeholder}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) onNext();
            }}
          />
        ) : (
          <input
            ref={ref as React.RefObject<HTMLInputElement>}
            type="text"
            className={inputClass}
            style={inputStyle}
            placeholder={placeholder}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") onNext(); }}
          />
        )}
        {multiline && (
          <p className="text-xs mt-2" style={{ color: "var(--fg-secondary)" }}>
            ⌘ Return to continue
          </p>
        )}
      </div>
      <div className="flex gap-3 mt-6">
        {onBack && <BackButton onClick={onBack} />}
        <NextButton onClick={onNext} />
      </div>
    </div>
  );
}

function UploadStep({
  usePictures,
  uploads,
  onFilesChange,
  onNext,
  onBack,
}: {
  usePictures: boolean;
  uploads: File[];
  onFilesChange: (f: File[]) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  function handleFiles(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []);
    onFilesChange([...uploads, ...files]);
  }

  return (
    <div>
      <Question
        text="Add supporting documents or images."
        hint="Optional — these will be treated as additional source material."
      />
      <div className="mt-8 space-y-4">
        <label
          className="flex flex-col items-center justify-center w-full h-40 rounded-2xl border-2 border-dashed cursor-pointer transition-colors duration-200"
          style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}
        >
          <span className="text-3xl mb-2">↑</span>
          <span className="text-sm font-medium" style={{ color: "var(--fg)" }}>
            Click to choose files
          </span>
          <span className="text-xs mt-1" style={{ color: "var(--fg-secondary)" }}>
            PDF, DOCX, TXT{usePictures ? ", JPEG, PNG" : ""} — max 20 MB each
          </span>
          <input
            type="file"
            multiple
            accept=".pdf,.docx,.txt,.doc" + (usePictures ? ",.jpg,.jpeg,.png,.webp" : "")}
            className="sr-only"
            onChange={handleFiles}
          />
        </label>

        {uploads.length > 0 && (
          <ul className="space-y-2">
            {uploads.map((f, i) => (
              <li
                key={i}
                className="flex items-center justify-between px-4 py-2.5 rounded-xl text-sm"
                style={{ background: "var(--bg-secondary)", color: "var(--fg)" }}
              >
                <span className="truncate">{f.name}</span>
                <button
                  onClick={() => onFilesChange(uploads.filter((_, j) => j !== i))}
                  className="ml-4 text-xs px-2 py-0.5 rounded-full"
                  style={{ color: "var(--fg-secondary)" }}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="flex gap-3 mt-6">
        <BackButton onClick={onBack} />
        <NextButton onClick={onNext} label={uploads.length > 0 ? "Continue" : "Skip"} />
      </div>
    </div>
  );
}

function ConfirmStep({
  state,
  saving,
  onBack,
  onGenerate,
}: {
  state: FlowState;
  saving: boolean;
  onBack: () => void;
  onGenerate: () => void;
}) {
  const rows: [string, string][] = [
    ["Type", state.doc_type === "speech" ? "Speech" : "Press Release"],
    ...(state.speaker_role
      ? [["Speaker", state.speaker_role === "other" ? state.speaker_name || "Other" : state.speaker_role.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())] as [string, string]]
      : []),
    ...(state.use_pictures !== null
      ? [["Images", state.use_pictures ? "Yes" : "No"] as [string, string]]
      : []),
    ["Brief", state.brief || "—"],
    ["Length", state.length_target?.replace("-", " – ") || "—"],
    ["Uploads", state.uploads.length > 0 ? state.uploads.map((f) => f.name).join(", ") : "None"],
  ];

  return (
    <div>
      <Question
        text="Ready to generate."
        hint="Review your inputs, then start the research and drafting process."
      />
      <div className="mt-8 rounded-2xl overflow-hidden border" style={{ borderColor: "var(--border)" }}>
        {rows.map(([label, value], i) => (
          <div
            key={i}
            className="flex gap-4 px-5 py-4 text-sm"
            style={{
              borderBottom: i < rows.length - 1 ? `1px solid var(--border)` : undefined,
              background: "var(--bg-secondary)",
            }}
          >
            <span className="w-20 shrink-0 font-medium" style={{ color: "var(--fg-secondary)" }}>
              {label}
            </span>
            <span style={{ color: "var(--fg)" }} className="break-words min-w-0">
              {value}
            </span>
          </div>
        ))}
      </div>
      <p className="text-xs mt-4" style={{ color: "var(--fg-secondary)" }}>
        Generation typically takes 30 – 90 seconds. You will be shown a live status
        and can download the draft and Sources Dossier when ready.
      </p>
      <div className="flex gap-3 mt-6">
        <BackButton onClick={onBack} />
        <button
          onClick={onGenerate}
          disabled={saving}
          className="flex items-center gap-2 px-6 py-3 rounded-full text-white font-medium transition-all duration-200 disabled:opacity-50"
          style={{ background: "var(--accent)" }}
        >
          {saving ? (
            <>
              <Spinner />
              Starting…
            </>
          ) : (
            "Generate →"
          )}
        </button>
      </div>
    </div>
  );
}

// ─── Shared primitives ────────────────────────────────────────────────────────

function Question({ text, hint }: { text: string; hint?: string }) {
  return (
    <div>
      <h2 className="text-3xl font-semibold leading-tight" style={{ color: "var(--fg)" }}>
        {text}
      </h2>
      {hint && (
        <p className="mt-3 text-base" style={{ color: "var(--fg-secondary)" }}>
          {hint}
        </p>
      )}
    </div>
  );
}

function NextButton({ onClick, label = "Continue" }: { onClick: () => void; label?: string }) {
  return (
    <button
      onClick={onClick}
      className="px-6 py-3 rounded-full text-white font-medium transition-all duration-200"
      style={{ background: "var(--accent)" }}
    >
      {label} →
    </button>
  );
}

function BackButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="px-5 py-3 rounded-full text-sm font-medium transition-all duration-200"
      style={{ color: "var(--fg-secondary)", background: "var(--bg-secondary)" }}
    >
      ← Back
    </button>
  );
}

function Spinner() {
  return (
    <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}
