import type { IntakePayload, SessionPublic } from "@/types/session";

const BASE = "/api";

async function req<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  createSession: () => req<SessionPublic>("POST", "/sessions"),

  getSession: (id: string) => req<SessionPublic>("GET", `/sessions/${id}`),

  submitIntake: (id: string, payload: IntakePayload) =>
    req<SessionPublic>("PATCH", `/sessions/${id}/intake`, payload),

  uploadFile: async (id: string, file: File): Promise<{ ref: string }> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/sessions/${id}/upload`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Upload failed");
    }
    return res.json();
  },

  generate: (id: string) =>
    req<SessionPublic>("POST", `/sessions/${id}/generate`),

  downloadUrl: (id: string, artifact: "deliverable" | "dossier") =>
    `${BASE}/sessions/${id}/download/${artifact}`,
};
