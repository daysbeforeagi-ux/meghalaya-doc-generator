"use client";

import { CSSProperties } from "react";

type Option = { label: string; value: string };

interface QuestionProps {
  step: number;
  totalSteps: number;
  question: string;
  hint?: string;
  type: "choice" | "textarea" | "text";
  options?: Option[];
  value: string;
  onChange: (value: string) => void;
  onNext: () => void;
  onBack?: () => void;
  nextLabel?: string;
  canSkip?: boolean;
}

export default function Question({
  step,
  totalSteps,
  question,
  hint,
  type,
  options,
  value,
  onChange,
  onNext,
  onBack,
  nextLabel = "Continue",
  canSkip = false,
}: QuestionProps) {
  const hasValue = value.trim().length > 0;

  const inputStyle: CSSProperties = {
    width: "100%",
    padding: "14px 16px",
    borderRadius: "12px",
    border: "1.5px solid var(--border)",
    background: "var(--surface)",
    color: "var(--text-primary)",
    fontSize: "17px",
    fontFamily: "inherit",
    outline: "none",
    transition: "border-color 200ms ease-out",
  };

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
      <div style={{ maxWidth: "640px", width: "100%" }}>
        {/* Step counter */}
        <p
          style={{
            fontSize: "13px",
            color: "var(--text-tertiary)",
            marginBottom: "40px",
            letterSpacing: "0.04em",
          }}
        >
          {step} of {totalSteps}
        </p>

        {/* Question */}
        <h2
          style={{
            fontSize: "clamp(24px, 4vw, 36px)",
            fontWeight: 700,
            lineHeight: 1.15,
            letterSpacing: "-0.01em",
            color: "var(--text-primary)",
            marginBottom: hint ? "12px" : "32px",
          }}
        >
          {question}
        </h2>

        {hint && (
          <p
            style={{
              fontSize: "15px",
              color: "var(--text-secondary)",
              marginBottom: "32px",
              lineHeight: 1.5,
            }}
          >
            {hint}
          </p>
        )}

        {/* Input */}
        <div style={{ marginBottom: "32px" }}>
          {type === "choice" && options && (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {options.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => onChange(opt.value)}
                  style={{
                    width: "100%",
                    padding: "16px 20px",
                    borderRadius: "12px",
                    border: `1.5px solid ${
                      value === opt.value ? "var(--accent)" : "var(--border)"
                    }`,
                    background:
                      value === opt.value
                        ? "color-mix(in srgb, var(--accent) 8%, var(--bg))"
                        : "var(--surface)",
                    color:
                      value === opt.value ? "var(--accent)" : "var(--text-primary)",
                    fontSize: "17px",
                    fontFamily: "inherit",
                    fontWeight: value === opt.value ? 600 : 400,
                    textAlign: "left",
                    cursor: "pointer",
                    transition: "all 200ms ease-out",
                    minHeight: "52px",
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}

          {type === "textarea" && (
            <textarea
              value={value}
              onChange={(e) => onChange(e.target.value)}
              rows={5}
              placeholder="Describe the occasion, key points to cover, audience..."
              style={{ ...inputStyle, resize: "vertical", lineHeight: 1.6 }}
              onFocus={(e) =>
                (e.currentTarget.style.borderColor = "var(--accent)")
              }
              onBlur={(e) =>
                (e.currentTarget.style.borderColor = "var(--border)")
              }
            />
          )}

          {type === "text" && (
            <input
              type="text"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              placeholder="Enter name..."
              style={inputStyle}
              onFocus={(e) =>
                (e.currentTarget.style.borderColor = "var(--accent)")
              }
              onBlur={(e) =>
                (e.currentTarget.style.borderColor = "var(--border)")
              }
            />
          )}
        </div>

        {/* Actions */}
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          {onBack && (
            <button
              onClick={onBack}
              style={{
                height: "48px",
                padding: "0 20px",
                borderRadius: "12px",
                border: "1.5px solid var(--border)",
                background: "transparent",
                color: "var(--text-secondary)",
                fontSize: "15px",
                fontFamily: "inherit",
                cursor: "pointer",
                minWidth: "44px",
              }}
            >
              Back
            </button>
          )}

          <button
            onClick={onNext}
            disabled={!hasValue && !canSkip}
            style={{
              height: "48px",
              padding: "0 28px",
              borderRadius: "12px",
              background:
                hasValue || canSkip ? "var(--accent)" : "var(--border)",
              color: hasValue || canSkip ? "#fff" : "var(--text-tertiary)",
              fontSize: "17px",
              fontWeight: 600,
              fontFamily: "inherit",
              border: "none",
              cursor: hasValue || canSkip ? "pointer" : "not-allowed",
              transition: "background 200ms ease-out",
              flex: 1,
            }}
          >
            {nextLabel}
          </button>

          {canSkip && (
            <button
              onClick={() => { onChange(""); onNext(); }}
              style={{
                height: "48px",
                padding: "0 20px",
                borderRadius: "12px",
                border: "none",
                background: "transparent",
                color: "var(--text-secondary)",
                fontSize: "15px",
                fontFamily: "inherit",
                cursor: "pointer",
              }}
            >
              Skip
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
