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
| `OPENCLAW_GATEWAY_URL`, `OPENCLAW_GATEWAY_TOKEN`, `OPENCLAW_AGENT_ID` | Where and how to reach the OpenClaw gateway. Agent id `default` matches the gateway's `openclaw/default` model name. |
| `BRAVE_API_KEY` | Enables the Public research panel. The app calls Brave directly. |
| `LLM_PROVIDER` | `openai` (default) or `canned` for key-less UI work. |

## Public research (Brave, not OpenClaw)

The Decision Room has a Public research panel. It runs two or three Brave web searches built from the company name, website domain, and your brief, deduplicates the results, and makes one OpenAI call that may only cite URLs from those results. Facts citing anything else are dropped and counted. Kept facts are stored as `WEB` evidence rows, linked to a deck claim when the model names one, and if a thesis assessment already exists the company is rescored and the same Before / New evidence / After diff is shown.

This deliberately does not go through OpenClaw. An OpenClaw run spends the box's own model on an agent loop for every search; Brave plus one structured call is a few cents and deterministic. OpenClaw is reserved for the single Run Agent Check that the assignment requires.

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

- on the gateway box itself (recommended): `OPENCLAW_GATEWAY_URL=http://127.0.0.1:18789`, nothing to expose;
- from a laptop: an SSH tunnel, `ssh -N -L 18789:127.0.0.1:18789 user@gateway-box`, then `OPENCLAW_GATEWAY_URL=http://127.0.0.1:18789`;
- from Replit: the gateway must be reachable over public HTTPS. The least-friction way for a demo window is a Cloudflare quick tunnel run **on the gateway box**, which connects to the loopback port locally so the gateway keeps its loopback bind and bearer-token auth:

  ```bash
  # on the OpenClaw box
  curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared && chmod +x cloudflared
  ./cloudflared tunnel --url http://127.0.0.1:18789
  # prints a https://<random>.trycloudflare.com URL; it changes every time the tunnel restarts
  ```

  Then in Replit Secrets set `OPENCLAW_GATEWAY_URL=https://<random>.trycloudflare.com` (no trailing slash) and keep `OPENCLAW_GATEWAY_TOKEN`. Verify from anywhere: `curl https://<random>.trycloudflare.com/health` should return `{"ok":true,...}`. The token is a full operator credential for the box: stop the tunnel after the demo and rotate the token if the URL was ever shared.

The app sends the agent the company name, website, current concern, open evidence gap, last review date, and the investment question (see `backend/app/prompts/agent_task.md`). The reply is parsed leniently (fenced JSON, bare JSON, or JSON inside prose) and stored as a `monitoring_event` with its source URL. The finding becomes an `AGENT` evidence row, the thesis is rescored, and the Decision Room shows before, new evidence, after. The human decision is never modified.

## Deploy on the OpenClaw box (recommended)

Running the app on the same machine as the OpenClaw gateway removes the hardest part of any third-party host: the gateway stays loopback-only and the app reaches it at `http://127.0.0.1:18789`. SQLite and uploaded decks persist on disk. Tailscale Funnel gives a stable public HTTPS URL.

```bash
git clone https://github.com/rightinsights/vc-decision-cockpit.git ~/vc-decision-cockpit
cd ~/vc-decision-cockpit
cp .env.example .env
# edit .env: OPENAI_API_KEY, BRAVE_API_KEY, OPENCLAW_GATEWAY_TOKEN, AGENT_PROVIDER=openclaw
bash build.sh                     # installs backend deps, builds the frontend (Node 22+, Python 3.12)
nohup bash start.sh > app.log 2>&1 &
curl -s http://127.0.0.1:3000/api/health   # {"status":"ok"}
tailscale funnel 3000             # prints https://<host>.<tailnet>.ts.net
```

To survive reboots, install `deploy/vc-cockpit.service` (see that file for the two commands).

## Deploy on Replit (alternative)

1. Push this repo to GitHub (done: `rightinsights/vc-decision-cockpit`, private).
2. In Replit: Create App, Import from GitHub, authorise GitHub, pick the repo. `.replit` declares the Node and Python modules, a Reserved VM deployment target, `build.sh`, and `start.sh`. If the import wizard asks for a run command, keep `bash start.sh`.
3. Tools, Database, create the built-in PostgreSQL. This injects `DATABASE_URL`; the app rewrites it to the psycopg driver and creates tables on first start. The deployment filesystem resets on every publish, so SQLite is not used there.
4. Tools, Secrets, add:
   `OPENAI_API_KEY`, `OPENAI_MODEL=gpt-5-mini`, `BRAVE_API_KEY`,
   `AGENT_PROVIDER=openclaw`, `OPENCLAW_GATEWAY_URL` (the public HTTPS tunnel URL from the OpenClaw section), `OPENCLAW_GATEWAY_TOKEN`, `OPENCLAW_AGENT_ID=default`.
   Deployment secrets are a separate store from workspace secrets: when you publish, open the deployment's Secrets pane and confirm the same keys are present there.
5. Press Run once in the workspace to confirm `build.sh` and `start.sh` work (first run installs and builds, a few minutes). Open the webview: the pipeline should load and `/api/health` should return `{"status":"ok"}`.
6. Publish, choose Reserved VM (already the target in `.replit`), smallest size. Next.js listens on port 3000, mapped to external port 80, and proxies `/api/*` to FastAPI on 127.0.0.1:8000. The public URL is `https://<app-name>.replit.app`.
7. On the public URL: add Oii.ai, upload `backend/data/demo/oii-ai-seed-deck-2023-techcrunch.pdf` (download it from the repo first), run analysis, record WATCH, run research, run one agent check. That reproduces the recorded run in `RESEARCH_NOTES.md`.

If the build fails on module names, the two most likely fixes are changing `modules` in `.replit` to the ids Replit offers in its Modules pane (Node 20 or 22, Python 3.11 or 3.12) and re-running.

Uploaded PDFs are stored on the deployment filesystem and will not survive a republish; the extracted page text lives in the database, so analysis history is kept.

## Demo deck

`backend/data/demo/oii-ai-seed-deck-2023-techcrunch.pdf` is built by `backend/scripts/build_public_deck_oii.py` from the 7 Oii.ai slides TechCrunch published with the company's consent, transcribed with the vision model so every claim can cite a slide. See `RESEARCH_NOTES.md` for provenance and the recorded real run.

## Demo script

1. Pipeline, add company (Oii.ai, https://oii.ai, seed, United States), upload the demo deck, run analysis.
2. Decision Room: point at one claim, its slide, and its dashed missing-proof cell.
3. Thesis fit in the left rail, score secondary to the criteria.
4. Five questions with strong and weak answers.
5. Record WATCH with a rationale.
6. Run agent check. Show the finding, its source URL, which gap it bears on, and the before/after diff. The human decision stays WATCH.
7. Optional: paste a founder update and show only what moved.
8. What changed: the full timeline.
