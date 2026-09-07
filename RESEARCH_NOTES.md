# Research notes

Sources consulted while building, and the implementation problems actually hit. Kept short on purpose (BUILD_SPEC §18).

## Sources

| Source | Link | Used for | One useful thing learned |
|---|---|---|---|
| OpenClaw docs: OpenAI-compatible HTTP API | https://docs.openclaw.ai/gateway/openai-http-api | How an external backend hands OpenClaw a task and gets text back | It is off by default; enable `gateway.http.endpoints.chatCompletions.enabled`. `response_format` is not supported, so the JSON shape goes in the prompt and is validated app-side. |
| OpenClaw docs: webhooks, remote access, security | https://docs.openclaw.ai/automation/webhook, https://docs.openclaw.ai/gateway/remote, https://docs.openclaw.ai/gateway/security | Choosing the integration path and the network path to the box | The `/hooks/agent` webhook never returns model output, so it cannot drive a request/response UI. The gateway refuses a non-loopback bind without auth; SSH tunnel or Tailscale is the sanctioned route. |
| OpenClaw docs: web tools | https://docs.openclaw.ai/tools/web, https://docs.openclaw.ai/tools/brave-search | Making the agent able to research | Managed `web_search` needs a provider key (`BRAVE_API_KEY`); `web_fetch` runs locally without one. |
| Replit docs: configuration, ports, deployment types, databases | https://docs.replit.com/features/project-setup/configuration, https://docs.replit.com/replit-workspace/ports, https://docs.replit.com/features/publishing/deployment-types, https://docs.replit.com/features/data-and-storage/connection-details | `.replit`, running two processes, database choice | Deployments expose one external port and the filesystem resets on publish. So Next.js fronts FastAPI on one port, and Postgres via `DATABASE_URL` replaces SQLite in deployment. |
| OpenAI docs: structured outputs | https://developers.openai.com/api/docs/guides/structured-outputs | Getting valid JSON out of the extraction and scoring calls | `client.chat.completions.parse(response_format=PydanticModel)`; strict mode needs every field required (nullable via `| None`), `additionalProperties: false`, and no `minimum`/`maximum`, so range checks live in validators. |
| Brave Search API docs | https://api-dashboard.search.brave.com/app/documentation/web-search/get-started | Public research panel without an agent loop | `GET /res/v1/web/search?q=&count=` with `X-Subscription-Token`; results under `web.results[]` with `title`, `url`, `description`, `age`/`page_age`. |
| PyMuPDF docs: basics and Page | https://pymupdf.readthedocs.io/en/latest/the-basics.html, https://pymupdf.readthedocs.io/en/latest/page.html | Page-level text extraction with page numbers | `page.get_text("text", sort=True)`; `page.number` is zero-based, so citations use `number + 1`. The `fitz` import name is deprecated in favour of `pymupdf`. |

## Problems encountered

- **OpenAI key rejected.** The `OPENAI_API_KEY` present in the shell environment returned 401 from the models endpoint. Everything was built and tested against a fake LLM in the test suite and a labelled `canned` provider for UI work; the real extraction run is still pending a valid key.
- **Half-up rounding drifted.** Summing `(score-1)/4*weight` in floating point produced 57.4999 for a true 57.5, so the total rounded down. Fixed by computing the total in integers (`sum((s-1)*w)*25` over the used weight) with explicit half-up rounding.
- **Strict schema vs provenance.** The spec's flat extraction JSON had no room for page and quote per claim. Each claim became an object with `source_page`, `supporting_text`, `evidence_strength`, and `missing_proof`, which the Decision Room ledger needs anyway.
- **"Exactly five" cannot be left to the prompt.** The service checks the count, retries once with feedback, and fails with 502 rather than persisting a wrong number.
- **Agent reply parsing.** Agent output arrives as prose with a fenced JSON block, or bare JSON. The parser tries fenced, bare, and first-brace-to-last-brace candidates, normalises the event type and URL, and validates leniently, so the app is not brittle to formatting.
- **Open gap selection.** The agent is pointed at the weakest claim that still lists a missing proof (LOW strength first), not the first claim. This surfaced in a test that assumed otherwise.
- **Next.js 16 lint rule.** `react-hooks/set-state-in-effect` rejects calling a state-setting async loader directly inside `useEffect`; the loaders now resolve promises inside the effect with an `active` guard.
- **New shadcn CLI.** The current shadcn generates Base UI components and a `cn` package rather than Radix; component APIs differ slightly from older tutorials.
- **Port collision.** Local port 8000 was already in use, so local development runs the backend on 8011 with `BACKEND_URL` pointing the Next.js proxy at it; Replit uses 8000.
- **Sticky rail taller than the viewport.** A sticky left rail hid its lower half on long pages; it now scrolls with the page.
- **Replit database.** Replit hands out a driverless `postgresql://` URL; SQLAlchemy needs `postgresql+psycopg://`, so the settings layer rewrites it.

- **Search routing.** A parallel build routed all web research through OpenClaw, which runs the box's own model for every query. Decision: the app calls Brave directly and uses one OpenAI call to turn results into sourced facts; every fact must cite a URL Brave returned or it is dropped. OpenClaw is used only for the one required agent check.

## Demo deck provenance

No thesis-fit seed deck exists anywhere public as a downloadable PDF: every deck library serves slide images or view-only Google Drive files with download disabled. The demo uses **Oii.ai** (AI supply-chain digital twin, seed 2023, founders ex-GSK supply chain and ex-Intel chief data scientist). TechCrunch published 7 of its 21 slides as images with the company's consent (https://techcrunch.com/2023/06/02/sample-seed-pitch-deck-oii-ai/). `backend/scripts/build_public_deck_oii.py` downloads those 7 public slides, transcribes each with the vision model, and writes a text-searchable PDF (`backend/data/demo/oii-ai-seed-deck-2023-techcrunch.pdf`) with the source URL printed on every page. The view-only Drive copy was deliberately not scraped.

## Real run, 2026-09-06

| Step | Provider | Time | Result |
|---|---|---|---|
| Deck analysis | OpenAI gpt-5-mini | 76 s | 7 claims with slide refs, score 38, PASS. Main concern: no customers, no quantified ROI, no buyer. |
| Five questions | OpenAI | 42 s | Company-specific (pilot list, before/after data, buyer title, sandbox demo, patent numbers). |
| Public research | Brave + OpenAI | 77 s | 20 results, 18 domains, 11 facts kept, 0 dropped. Rescored 38 to 50, PASS to WATCH. |
| Agent check | OpenClaw (real) | 106 s | Found a 2026 Logistics Tech Outlook profile with a named UK deployment (18,500 SKUs, 7 ERPs). Source URL resolves. Customer evidence 2 to 4. Recommendation stayed WATCH. Human decision untouched. |

Observed and fixed: criteria the new evidence never touched drifted between rescoring runs (founder fit 4 to 5 to 4). The assessment prompt now receives the previous scores and is told to hold untouched criteria identical. Also fixed: reasons leaked machine evidence ids; the prompt now cites sources by name and the UI strips any stragglers.

Cost note: a trivial OpenClaw call reports about 24K prompt tokens, so each agent run carries the box's full system prompt. One run per demo is fine; casual clicking is not.

## Image-only decks

A one-page investor overview exported as a tall image (2377 x 13564 points, 22 embedded images) carried 24 characters of live text: "Pre-Seed | $2M | ElevenLabs". The extractor named the company ElevenLabs. Fix: pages with under 40 characters of extractable text are rendered (tall pages tiled at 1800 px), transcribed by the vision model, and stored with an `ocr` flag; the document records how many pages were transcribed. Rerun on that deck: 1 page transcribed in about two minutes, 10 claims with the right company, five deck-specific questions.

## Research-first flow

Users expect a company created from a name and website to populate itself. Research now runs automatically on creation, fills the snapshot from public sources (labelled as such), and produces the first thesis fit with coverage shown. The deck, when added, overrides fields it states and rescoring uses its claims. Observed on Jimini Health: initial fit WATCH 61 from 12 sourced facts, then WATCH 60 after the deck with claims attached.

## Still open

- Replit import and publish: needs the GitHub push.
- Replit reach to the OpenClaw gateway needs a public HTTPS path (Tailscale Funnel or a TLS proxy) since the box is loopback-only behind an SSH tunnel today.
