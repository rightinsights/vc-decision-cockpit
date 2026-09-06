# VC Decision Cockpit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Assignment prototype: upload a pitch deck, extract claims and evidence with page references, score against the thesis in Python, generate exactly five diligence questions, record a human decision, trigger one real OpenClaw research run, and show what changed.

**Architecture:** FastAPI backend owns all logic (PDF pages via PyMuPDF, OpenAI structured outputs validated by Pydantic, scoring and band logic in Python, SQLAlchemy over SQLite locally / Postgres on Replit). Next.js frontend is a thin client that proxies `/api/*` to the backend so Replit exposes one port. Agent access is behind a two-implementation adapter (`MockMonitoringAgent`, `OpenClawMonitoringAgent` via the gateway's OpenAI-compatible chat endpoint).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2, openai SDK (`chat.completions.parse`), PyMuPDF, pytest. Next.js (App Router), TypeScript, Tailwind, shadcn/ui. SQLite local, Postgres on Replit.

**Spec:** `BUILD_SPEC.md` (repo root, copy of `BUILD_SPEC_assignment_v5.md`).

## Global Constraints

- Human decision enum: `PASS | WATCH | DILIGENCE`. AI recommendation uses the same three values. The system **must not change the human decision automatically** (§5, §7, §10).
- Weights verbatim from §7: founder_domain_fit 15, workflow_pain 15, workflow_frequency 10, buyer_clarity 10, customer_evidence 10, roi_clarity 10, defensibility 15, scalability 10, stage_geography_fit 5.
- Formula verbatim: `normalized = (score - 1) / 4; weighted = normalized × weight; overall = sum(weighted)`; null criteria excluded and rescaled over used weights. Bands: 0–49 PASS, 50–69 WATCH, 70–100 DILIGENCE. Total computed by the application, never the LLM.
- Exactly 5 diligence questions, enforced in code.
- `null` for absent facts; deck content is untrusted source material (§6).
- One LLM provider (OpenAI). One agent (OpenClaw) plus a mock. No queues, no multi-provider, no auth, no scheduler (§4, §12, §13).
- Never overwrite assessments or decisions; always insert (§11).
- Secrets only in env; `.env` is git-ignored.
- Long calls may be synchronous; UI shows loading state (§13).

---

## File Map

```
backend/
  requirements.txt, requirements-dev.txt, pyproject.toml (pytest config)
  app/config.py        Settings (env). BACKEND_DIR-relative paths.
  app/db.py            engine, SessionLocal, Base, get_db, init_db
  app/models.py        thesis, companies, documents, claims, evidence, assessments,
                       diligence_questions, decisions, founder_notes, monitoring_events
  app/thesis.py        THESIS_TEXT, CRITERIA (key,label,weight,description), WEIGHTS, band()
  app/scoring.py       compute_overall(), recommend(), diff_scores()   [pure]
  app/pdf.py           validate_pdf_bytes(), extract_pages()            [pure]
  app/llm_schemas.py   strict Pydantic models the LLM must return
  app/schemas.py       API request/response models
  app/llm.py           LLMClient.parse(prompt_name, variables, schema) + FakeLLM
  app/prompts/*.md     extraction, assessment, questions, note_analysis, agent_task
  app/services/analysis.py    analyze_company(): extraction -> claims/evidence -> assessment
  app/services/questions.py   generate_questions(): exactly 5
  app/services/decisions.py   record_decision(), latest_decision()
  app/services/changes.py     build_timeline(): before/new evidence/after
  app/services/reassess.py    reassess_with_evidence(): fresh assessment + diff
  app/services/agent_check.py run_agent_check(): adapter -> monitoring_event -> reassess
  app/agents/base.py   MonitoringAgent protocol, AgentRequest
  app/agents/mock.py   MockMonitoringAgent
  app/agents/openclaw.py OpenClawMonitoringAgent (POST {gateway}/v1/chat/completions)
  app/api/*.py         routers: companies, analysis, decisions, agent, changes, thesis
  app/main.py          app factory, CORS, routers, startup init_db + seed thesis
  app/seed.py          seed_thesis()
  tests/               conftest (tmp sqlite, FakeLLM override), one test file per module
frontend/
  next.config.ts       rewrites /api/* -> BACKEND_URL
  app/page.tsx                         Pipeline
  app/companies/[id]/page.tsx          Decision Room
  app/companies/[id]/changes/page.tsx  What Changed
  components/*.tsx     pipeline-table, add-company-dialog, deck-upload, snapshot,
                       thesis-fit, claims-table, questions, decision-panel,
                       agent-check, founder-update, timeline
  lib/api.ts, lib/types.ts
.replit, package.json (root start script), README.md, RESEARCH_NOTES.md, .env.example
```

## Interfaces (shared across tasks)

```python
# scoring.py
class ScoreResult(TypedDict): overall: int | None; used_weight: int
def compute_overall(scores: Mapping[str, int | None]) -> ScoreResult
def recommend(overall: int | None) -> Literal["PASS","WATCH","DILIGENCE"] | None
def diff_scores(old: dict[str, dict], new: dict[str, dict]) -> list[CriterionDelta]
# CriterionDelta = {key, label, old: int|None, new: int|None, reason: str}

# pdf.py
class PageText(TypedDict): page: int; text: str      # page is 1-based
def validate_pdf_bytes(data: bytes, max_mb: int) -> None   # raises ValueError
def extract_pages(path: str, max_pages: int) -> list[PageText]

# llm.py
class LLMClient:
    def parse(self, prompt_name: str, variables: dict[str, str], schema: type[T]) -> T
class FakeLLM(LLMClient):   # tests: canned responses keyed by schema
    def __init__(self, responses: dict[type, BaseModel | list[BaseModel]])

# agents/base.py
@dataclass class AgentRequest: company_name, website, concern, open_gap, last_review_date, investment_question
class MonitoringAgent(Protocol):
    async def check_company(self, request: AgentRequest) -> AgentFinding
```

---

### Task 1: Backend foundation — config, db, thesis, scoring, pdf, LLM schemas
**Files:** create `backend/app/{config,db,thesis,scoring,pdf,llm_schemas}.py`, `backend/tests/{test_scoring,test_pdf,test_llm_schemas}.py`, `backend/requirements*.txt`, `backend/pyproject.toml`, `.gitignore`, `.env.example`.
- [ ] Tests: `test_scoring.py` — all-5s → 100; all-1s → 0; null criterion excluded and rescaled (`customer_evidence=None`, rest 3 → 50); all null → overall None; bands at 49/50/69/70; `diff_scores` reports changed keys only.
- [ ] Tests: `test_pdf.py` — build a 3-page PDF with PyMuPDF in `tmp_path`, `extract_pages` returns 3 entries with pages 1..3 and the injected text; `validate_pdf_bytes` rejects non-`%PDF` bytes and oversize.
- [ ] Tests: `test_llm_schemas.py` — `CriterionScore(score=6)` raises; `normalize_criteria` fills missing keys with `score=None`; JSON schema of `DeckExtraction` has `additionalProperties: false` and every property required (strict-mode compatible).
- [ ] Run `pytest` → fail. Implement. Run → pass. Commit `feat: backend foundation (scoring, pdf, schemas)`.

### Task 2: Models, API for companies + deck upload
**Files:** `app/models.py`, `app/schemas.py`, `app/main.py`, `app/seed.py`, `app/api/{companies,thesis}.py`, `tests/conftest.py`, `tests/test_api_companies.py`.
- [ ] conftest: tmp sqlite file, `app.dependency_overrides[get_db]`, `TestClient`.
- [ ] Tests: create company → 201 with id; list; get 404; upload valid PDF → document with `page_count=3`; upload non-PDF → 400; `GET /thesis` returns 9 criteria summing to 100.
- [ ] Implement; run; commit `feat: company + deck upload API`.

### Task 3: LLM client, prompts, analysis service, questions, decisions, analysis endpoint
**Files:** `app/llm.py`, `app/prompts/{extraction,assessment,questions}.md`, `app/services/{analysis,questions,decisions}.py`, `app/api/{analysis,decisions}.py`, `tests/test_api_analysis.py`, `tests/test_questions.py`, `tests/test_api_decisions.py`.
- [ ] Tests with FakeLLM: `POST /analyze` persists snapshot, N claims each with a DECK evidence row on the same page, one assessment with `overall_score` computed in Python from canned criterion scores (not from the fake), recommendation band correct; re-analyze replaces DECK claims without duplicating.
- [ ] Tests: `POST /meeting-questions` with fake returning 4 → retries once → still 4 → 502; returning 5 → persisted with positions 1..5.
- [ ] Tests: `POST /decisions` requires rationale (422 if blank); two decisions → both returned by `GET /decisions`, latest first; `GET /analysis` returns current decision, latest assessment, claims with evidence, questions.
- [ ] Implement; run; commit `feat: deck analysis, questions, decisions`.

### Task 4: Real OpenAI wiring smoke test
- [ ] `python -c` model list check (read-only). Set `OPENAI_MODEL` default to a model confirmed present and supporting structured outputs.
- [ ] One real extraction on a small public deck via the API. Record cost and latency in `RESEARCH_NOTES.md`.

### Task 5: Frontend skeleton — Pipeline + Decision Room (Phase 1/2 UI)
**Files:** `frontend/*` via `create-next-app`, shadcn init, `next.config.ts` rewrites, `lib/api.ts`, `lib/types.ts`, pages and components listed in the file map (excluding agent-check, founder-update, timeline).
- [ ] Pipeline table with the 8 columns from §5, Add Company dialog, Open Decision Room link, empty state.
- [ ] Decision Room: deck upload + Run Analysis (loading state), snapshot, thesis fit (9 criteria, reason, secondary score), claims table with 5 columns and Relation badges, 5 questions, decision panel with required rationale and current decision.
- [ ] Verify in browser at 1440 and 768. Commit `feat: pipeline and decision room UI`.

### Task 6: Agent adapter + agent-check + What Changed (Phase 3)
**Files:** `app/agents/{base,mock,openclaw}.py`, `app/prompts/agent_task.md`, `app/services/{agent_check,reassess,changes}.py`, `app/api/{agent,changes}.py`, `tests/test_agent.py`, `tests/test_changes.py`, frontend `agent-check.tsx`, `changes/page.tsx`, `timeline.tsx`.
- [ ] Tests: mock agent returns a finding → `monitoring_events` row with `source_url`; an `AGENT` evidence row; a new assessment with `trigger=AGENT`; `GET /changes` timeline contains deck, assessment, decision, agent event, reassessment entries in time order, with `before/after` diff and the human decision unchanged.
- [ ] Tests: `OpenClawMonitoringAgent` builds the request body (`model: openclaw/<agent>`, bearer header, task text contains company + question), parses fenced or bare JSON from `choices[0].message.content`, raises on missing token. Use `httpx.MockTransport`.
- [ ] Agent-check disabled in UI unless current decision is WATCH or DILIGENCE.
- [ ] Commit `feat: agent check and what-changed timeline`.

### Task 7: Founder update (Phase 4, optional)
- [ ] `POST /founder-notes` + `POST /reassess` with `note_analysis.md`; diff shown in Decision Room and timeline. Only after Task 6 is verified with the real OpenClaw box.

### Task 8: Replit packaging + docs (Phase 5)
- [ ] `.replit` (single external port on Next.js, `deploymentTarget = "vm"`), root `package.json` start script, README run instructions, `RESEARCH_NOTES.md` with 4–6 sources and the problems log, `.env.example` complete.
- [ ] Empty states, error toasts, screenshot pass.

## Self-review against spec
- §5 screens: Task 5 (1, 2), Task 6 (3). §6 extraction: Task 1 schemas + Task 3 prompt. §7 scoring: Task 1. §8 five questions: Task 3. §9 founder update: Task 7. §10 OpenClaw: Task 6. §11 model: Task 2. §12 stack: Tasks 2, 5, 8. §13 endpoints: Tasks 2, 3, 6, 7. §14 build order respected. §15 DoD: Task 8 + real run. §18 research notes: Task 8.
