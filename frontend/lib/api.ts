import type {
  Analysis, ChangeEntry, Company, Decision, DocumentInfo, PipelineRow, Question, Reassessment, Thesis, Verdict,
} from "./types";

const BASE = "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, { cache: "no-store", ...init });
  } catch {
    throw new ApiError(0, "The backend is not reachable. Is the API server running?");
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
      else if (Array.isArray(body?.detail)) detail = body.detail.map((d: { msg?: string }) => d.msg ?? "").join("; ");
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  listCompanies: () => request<PipelineRow[]>("/companies"),
  createCompany: (body: { name: string; website?: string; stage?: string; geography?: string }) =>
    request<Company>("/companies", json(body)),
  getAnalysis: (id: string) => request<Analysis>(`/companies/${id}/analysis`),
  uploadDeck: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentInfo>(`/companies/${id}/deck`, { method: "POST", body: form });
  },
  analyze: (id: string) => request<Analysis>(`/companies/${id}/analyze`, { method: "POST" }),
  meetingQuestions: (id: string) => request<Question[]>(`/companies/${id}/meeting-questions`, { method: "POST" }),
  listDecisions: (id: string) => request<Decision[]>(`/companies/${id}/decisions`),
  createDecision: (id: string, body: { decision: Verdict; rationale: string }) =>
    request<Decision>(`/companies/${id}/decisions`, json(body)),
  getThesis: () => request<Thesis>("/thesis"),
  agentCheck: (id: string, investment_question?: string) =>
    request<Reassessment>(`/companies/${id}/agent-check`, json({ investment_question: investment_question ?? null })),
  founderNote: (id: string, raw_notes: string) =>
    request<{ id: string }>(`/companies/${id}/founder-notes`, json({ raw_notes })),
  reassess: (id: string, note_id: string) => request<Reassessment>(`/companies/${id}/reassess`, json({ note_id })),
  getChanges: (id: string) => request<ChangeEntry[]>(`/companies/${id}/changes`),
};
