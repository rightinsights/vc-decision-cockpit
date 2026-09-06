# VC Decision Cockpit

An assignment prototype for the Venture Institute Builder challenge. Upload a startup deck, separate founder claims from evidence with page references, score the company against a real investment thesis, get exactly five diligence questions, record a human decision, then send an OpenClaw agent to find new external evidence and see what changed.

**Company → Claim → Evidence → Assessment → Human Decision → What Changed**

The AI recommends. The human decision is only ever changed by hand.

## What is in the box

| Part | Stack | Notes |
|---|---|---|
| `backend/` | FastAPI, SQLAlchemy 2, Pydantic 2, PyMuPDF, OpenAI SDK | All logic lives here. Scoring is computed in Python, never by the model. |
| `frontend/` | Next.js 16 (App Router), TypeScript, Tailwind 4, shadcn/ui | Thin client. Proxies `/api/*` to the backend so one port is public. |
| `backend/app/agents/` | `MockMonitoringAgent`, `OpenClawMonitoringAgent` | Same interface. Selected by `AGENT_PROVIDER`. |
| `backend/app/prompts/` | Markdown prompt files | `extraction`, `assessment`, `questions`, `note_analysis`, `agent_task`. |
| `BUILD_SPEC.md` | Product contract | The assignment spec this implements. |
| `RESEARCH_NOTES.md` | Sources and problems log | Required by the assignment. |

## Run locally

Prerequisites: Python 3.12, Node 22 or newer, an OpenAI API key.

```powershell
# backend
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt
Copy-Item ..\.env.example .env      # then set OPENAI_API_KEY
.venv\Scripts\python -m uvicorn app.main:app --port 8000

# frontend (second terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The backend also serves interactive docs at http://localhost:8000/docs.

If port 8000 is taken, start uvicorn on another port and set `BACKEND_URL` for the frontend, for example `$env:BACKEND_URL="http://127.0.0.1:8011"; npm run dev`.

### Without an API key

`LLM_PROVIDER=canned` in `backend/.env` returns clearly labelled placeholder outputs so the screens can be exercised. `python -m scripts.seed_demo` inserts a sample company with hand-written claims and scores; `--remove` deletes it. Neither is analysis. Use a real key for the assignment demo.

### Tests

```powershell
cd backend
.venv\Scripts\python -m pytest -q
```

The suite uses a fake LLM and the mock agent, so it needs no network and no key. It covers scoring and rescaling, PDF page extraction, strict-schema compatibility, the deck-to-decision API flow, the exactly-five rule, append-only decisions, the agent check, founder-note reassessment, the What Changed timeline, and the OpenClaw request/response handling against a mock transport.

## Configuration

All settings are environment variables, read from `backend/.env` locally and from Replit Secrets in deployment. See `.env.example`.

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY`, `OPENAI_MODEL` | One LLM provider. The model must support structured outputs. |
| `DATABASE_URL` | SQLite locally (`sqlite:///./data/app.db`). Replit injects a Postgres URL for its built-in database. |
| `AGENT_PROVIDER` | `mock` (default) or `openclaw`. |
| `OPENCLAW_GATEWAY_URL`, `OPENCLAW_GATEWAY_TOKEN`, `OPENCLAW_AGENT_ID` | Where and how to reach the OpenClaw gateway. |
| `LLM_PROVIDER` | `openai` (default) or `canned` for key-less UI work. |

## OpenClaw

The adapter calls the gateway's OpenAI-compatible endpoint, the one synchronous path that returns the agent's reply text:

```
POST {OPENCLAW_GATEWAY_URL}/v1/chat/completions
Authorization: Bearer {OPENCLAW_GATEWAY_TOKEN}
{"model": "openclaw/{OPENCLAW_AGENT_ID}", "messages": [...], "stream": false}
```

On the OpenClaw box, the endpoint must be enabled in the gateway config:

```json5
gateway: {
  auth: { mode: "token", token: "..." },
  http: { endpoints: { chatCompletions: { enabled: true } } }
}
```

The agent needs web search to do real research. OpenClaw's managed `web_search` requires a provider key such as `BRAVE_API_KEY` in the gateway environment (`tools.web.search.provider: "brave"`). `web_fetch` works without a key.

The gateway binds to loopback by default and refuses an unauthenticated non-loopback bind. To reach it from this app:

- from a laptop: an SSH tunnel, `ssh -N -L 18789:127.0.0.1:18789 user@box`, then `OPENCLAW_GATEWAY_URL=http://127.0.0.1:18789`;
- from Replit: expose the gateway through Tailscale Funnel or a TLS reverse proxy with the bearer token kept on, and set `OPENCLAW_GATEWAY_URL` to that public HTTPS address.

The app sends the agent the company name, website, current concern, open evidence gap, last review date, and the investment question (see `backend/app/prompts/agent_task.md`). The reply is parsed leniently (fenced JSON, bare JSON, or JSON inside prose) and stored as a `monitoring_event` with its source URL. The finding becomes an `AGENT` evidence row, the thesis is rescored, and the Decision Room shows before, new evidence, after. The human decision is never modified.

## Deploy on Replit

1. Push this repo to GitHub.
2. Import the GitHub repo into Replit. `.replit` declares the Node and Python modules, a Reserved VM deployment target, `build.sh`, and `start.sh`.
3. Add Secrets: `OPENAI_API_KEY`, and for the real agent `AGENT_PROVIDER=openclaw`, `OPENCLAW_GATEWAY_URL`, `OPENCLAW_GATEWAY_TOKEN`. Deployment secrets are a separate store from workspace secrets; add them in the Publishing pane too.
4. Create the built-in PostgreSQL database so `DATABASE_URL` is injected. The deployment filesystem resets on every publish, so SQLite is not suitable there.
5. Publish. Next.js listens on port 3000, mapped to external port 80, and proxies `/api/*` to FastAPI on 127.0.0.1:8000.

Uploaded PDFs are stored on the deployment filesystem and will not survive a republish; the extracted page text lives in the database, so analysis history is kept.

## Demo script

1. Pipeline, add company, upload a public deck, run analysis.
2. Decision Room: point at one claim, its slide, and its dashed missing-proof cell.
3. Thesis fit in the left rail, score secondary to the criteria.
4. Five questions with strong and weak answers.
5. Record WATCH with a rationale.
6. Run agent check. Show the finding, its source URL, which gap it bears on, and the before/after diff. The human decision stays WATCH.
7. Optional: paste a founder update and show only what moved.
8. What changed: the full timeline.
