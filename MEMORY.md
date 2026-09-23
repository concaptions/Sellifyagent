# Sellify Agent — Project Memory

> Compact, current-state context so a new session does not need to re-read the
> whole repo or chat history. **Update this file whenever state changes**
> (see "Maintaining this file" at the bottom). Last updated: 2026-09-23.
> No secrets in this file — values live in Railway env vars and the gitignored `.env`.

## What this is
WhatsApp personal AI assistant. **Sellify IS Cue** — this repo is Cue rebuilt off n8n onto
Railway. Everything Cue does must move here; n8n Cue stays live until this version is ready. Users text a WhatsApp number; a
Claude Agent SDK manager agent delegates to subagents for Calendar, Gmail,
Notes, and Web research. Product direction: "Instinct"-style assistant
(instinct.com) — proactive, takes actions, not just answers.

## Current status
| Area | State |
|---|---|
| WhatsApp inbound → agent → reply | ✅ Verified end-to-end from a real phone |
| Google Calendar (read/create/delete) | ✅ Live, verified |
| Gmail read | ✅ Live, verified |
| Gmail send | ⚠️ Rewired SMTP → Gmail API (commit c97345a), deployed; **live send not yet confirmed** |
| Notes | ✅ Per-user isolated; on Cue's Supabase (`sellify_notes`), live-verified 2026-09-23 |
| Document upload (PDF/DOCX/text) | ✅ V1 live-verified 2026-09-23 via signed replay (15-page PDF → 40 chunks embedded → correct answer → delete). **Not yet tried from a real phone.** Stores extracted text only |
| Webhook security | ✅ Forged Twilio signature → 403, unsigned `/webhook/test` → 404 (live-verified). Real-Twilio signature path not yet confirmed from a phone |
| Web search (Tavily) | ❌ `TAVILY_API_KEY` not set on Railway |
| Proactive follow-ups / reminders | 🚧 Not started (designed only, see Backlog) |
| Browser automation | 🚧 Not started (see Backlog) |
| Code on `main` | ❌ Only README — all code is on branch `claude/jolly-ramanujan-l0q173`, draft PR #1 |

## Request flow
```
WhatsApp → Twilio → POST /whatsapp/webhook (FastAPI, returns empty TwiML at once)
  → asyncio.create_task → PersonalAssistant.ainvoke(msg, user_phone)
  → claude_agent_sdk.query(): manager prompt + 4 AgentDefinitions
  → tools run in-process via create_sdk_mcp_server
  → reply → WhatsAppChannel (Twilio REST, split at 1600 chars)
```
`POST /webhook/test` (form: phone, message) runs the same agent **synchronously**
and returns `{"phone","reply"}` — no Twilio involved. Best way to test.

## File map
- `app.py` — FastAPI routes: `/whatsapp/webhook`, `/webhook/test`, `/health`,
  `/oauth/google/start`, `/oauth/google/callback`, `/oauth/google/status`
- `src/agents/assistant.py` — builds `ClaudeAgentOptions`, per-user session ids
- `src/prompts/*.py` — manager + 4 subagent prompts (small, principle-based)
- `src/tools/{calendar,email,notes,research,documents}/` — SDK `@tool` functions
- `src/utils/documents.py` — media download (Twilio auth only to *.twilio.com), extract, chunk, embed, ingest
- `src/utils/google_auth.py` — web OAuth flow, PKCE verifier store, token refresh
- `src/database.py` — Sellify's own tables `sellify_users`, `sellify_notes`, `sellify_chat_history`,
  `sellify_documents`, `sellify_document_chunks` (pgvector 1536)
- `src/channels/whatsapp.py`, `src/utils/message_splitter.py`
- `Procfile` — `uvicorn app:app --host 0.0.0.0 --port $PORT`

## Infrastructure (IDs are not secrets)
**Railway** — workspace Buildberg, project `tender-energy`
- project `0c7eae52-1d94-48dd-9c39-b52478345c78`, env production `d42c52fe-fb47-4fbc-b5c2-feb509ecd8d4`
- service `Sellifyagent` `b4181c17-8822-45de-8a49-80b7d7c72110` — deploys from branch
  `claude/jolly-ramanujan-l0q173` on push; domain `https://sellifyagent-production.up.railway.app`
- volume `sellifyagent-data` mounted at `/data` (Google token at `/data/token.json`)
- `DATABASE_URL` → **Cue's Supabase** (project ref `nnktgpjvtmkqongeubat`, transaction pooler
  :6543, superuser — bypasses RLS). Railway `Postgres` `efca358d-a4c2-4900-aa37-286c6f44e9de` is
  no longer used (holds only old test data); don't delete without asking.
- Railway Function `delivery-status-check` `bc20f51f-b26e-4c0d-93ef-16f0ebbba3b3` — used as a
  network probe (Bun/TS script; Twilio creds via `${{Sellifyagent.*}}` refs). Leftover test
  services still exist: `twilio-webhook-config`, `agent-smoke-test`, `agent-test-suite`,
  `webhook-oauth-diag` — user has not approved deleting them.
- Env vars on Sellifyagent: ANTHROPIC_API_KEY, TWILIO_*, FROM_WHATSAPP_NUMBER, GOOGLE_CLIENT_ID/SECRET,
  GOOGLE_TOKEN_FILE, PUBLIC_BASE_URL, DATABASE_URL, OPENAI_API_KEY, TEST_WEBHOOK_TOKEN,
  GMAIL_ADDRESS/GMAIL_APP_PASSWORD (now unused). The probe function has `TEST_WEBHOOK_TOKEN` and
  `PUBLIC_BASE_URL` as `${{Sellifyagent.*}}` refs.

**Twilio** — WhatsApp number `+65 8415 1532`
- Messaging Service `MG5c93d431fb48a69979d4390d353e0b65` ("Alluora_WA_Agent"):
  `inbound_request_url` → Sellify `/whatsapp/webhook`
- WhatsApp Sender `XE4e11e1b1329072d9db0df649b8dc7ebf`: webhook → Sellify `/whatsapp/webhook`.
  **The Sender-level webhook overrides the Messaging Service URL.**
- Event Streams subscription `DF21bd8006e280b0ad56063e6c60e01d39` → sink → n8n Cue
  (`primary-production-302c.up.railway.app`). **Parallel run**: every message gets a Cue
  reply AND a Sellify reply. Deliberate; do not remove without user approval.

**Google OAuth** — client "cue" in GCP project `cue-rich-sng`, Web application type
- Redirect URI: `https://sellifyagent-production.up.railway.app/oauth/google/callback`
- Consent screen in **Testing** mode; test user `concaptions@gmail.com` (the connected account)
- Scopes: calendar, gmail.readonly, gmail.send. One shared Google account for ALL WhatsApp users.
- Reconnect: visit `/oauth/google/start` in a browser. Check: `GET /oauth/google/status`.

**Cue's Supabase (shared DB)** — Cue n8n owns and still writes:
- `pa_users` (phone, name, timezone, persona_name, profile jsonb: core_prompt, active_persona,
  google_tokens — must stay a JSON *object*), `pa_personas`, `pa_reminders`, `n8n_chat_histories`
- `pa_knowledge_chunks` (Canon: `embedding vector(1536)`, OpenAI `text-embedding-3-small`,
  ~1200-char chunks) + `match_cue_knowledge(query_embedding, match_count, filter)` — fails closed
  without `filter.user_id`.
- All `sellify_*` tables have RLS enabled with no policies (set at startup) so Supabase's public
  REST API/anon key can't read them; the app connects as table owner and bypasses RLS. Any new
  table must be added to `_lock_tables` in `src/database.py`. The DB also holds unrelated
  non-Cue tables (`documents`, `leads`, `products`) — never touch them.
- **Rule during parallel run:** Sellify reads `pa_*` but writes only `sellify_*` (writing
  `pa_users`/`pa_reminders` would double-count stats and double-fire reminders).
- Cue's reference docs (schema, workflows, prompt): Cue handover bundle, not in the repo.

**LLM** — Claude Agent SDK 0.2.157, metered `ANTHROPIC_API_KEY` (a claude.ai
subscription login is not allowed for a deployed product). Model is **not pinned** (SDK default).

## Hard-won gotchas (read before changing agent/tool code)
1. `AgentDefinition.tools` restricts but does not grant: top-level `allowed_tools` must contain
   the union of every subagent tool name (`ALL_TOOL_NAMES`).
2. `permission_mode="bypassPermissions"` fails when running as root; use `"dontAsk"`.
3. Dict-style `@tool` schemas mark every field required. Use explicit JSON Schema with `required`.
4. Per-user data: notes tools are built per request via a closure (`build_notes_tools(user_phone)`),
   not via tool args or contextvars (those don't survive the SDK subprocess boundary).
5. Sessions: always pass an explicit `session_id` (new user) or `resume` (returning user), and
   blank `CLAUDE_CODE_SESSION_ID` in `env` — otherwise users can bleed into one ambient session.
6. Tool names are `mcp__<server>__<tool>`.
7. google-auth-oauthlib enables PKCE by default; `/start` and `/callback` are separate requests,
   so the `code_verifier` is stored in memory keyed by `state` (10-minute TTL).
8. Twilio v2 Senders API needs a JSON body for nested fields (form-encoded returns 415).
9. Inside `src/tools/email/`, the package `__init__` rebinds `send_email` to the tool object —
   import the submodule with `importlib.import_module("src.tools.email.send_email")` in tests.
10. This sandbox cannot reach `*.railway.app` or `api.twilio.com` (egress proxy 403). To hit
    live services, deploy a one-off script to the `delivery-status-check` Railway Function and
    read its deploy logs. Railway log timestamps lag; use the script's own start time as the window.
    `/webhook/test` needs header `X-Test-Token: Bun.env.TEST_WEBHOOK_TOKEN`. To replay a WhatsApp
    message, sign it like Twilio: base64(HMAC-SHA1(authToken, url + sorted key+value pairs)) in
    `X-Twilio-Signature`, url = `PUBLIC_BASE_URL + "/whatsapp/webhook"`.
11. Railway `list-deployments` status can stay `BUILDING` after a deploy is actually live — recheck.
12. Two replies per message is expected (parallel run with Cue), not a bug.

## Backlog (priority order)
1. Confirm Gmail API send works live (send a test email via `/webhook/test`).
2. Pin the model: `ClaudeAgentOptions(model="claude-sonnet-5")` — recommended, awaiting user OK.
3. Proactive follow-ups (user-approved): `pa_reminders` table, `create/list/cancel_reminder`
   tools (per-user closure like notes), background asyncio loop in `app.py` polling due rows,
   send via the agent with a `[SYSTEM PROACTIVE TRIGGER]` message, mark sent/failed in DB
   (never rely on the model to mark it done).
4. Browser automation (user-approved) — Phase A: read-only browsing tool (Playwright, headless,
   no stored credentials). Phase B (logged-in actions, stored credentials, payments):
   **needs explicit user decisions on credential storage, allowed sites, and a confirm-before-act
   gate — do not build on assumptions.**
5. Set `TAVILY_API_KEY` (user must supply the key).
6. Document upload follow-ups: confirm from a real phone (also proves real Twilio signatures pass); auto-retrieve relevant chunks every turn (V1 is
   tool-based); scanned PDFs via OCR/vision; per-tier storage caps; staleness nudges; when Canon
   promotion is built, Canon facts must store a source-document id so deleting a doc flags them
   for the user; keep original files only if needed (then private Supabase Storage).
7. Cue feature parity: Canon/RAG (pgvector), reminders, personal log, personas, photo/PDF
   ingestion, per-user Google tokens, prompt parity.
8. Delete now-unused `GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD` on Railway; user should rotate that
   Gmail password (it was shared in plaintext in chat).
9. Merge PR #1 so `main` has the code; clean up leftover Railway test services (ask first).
10. Retire the n8n Cue path when the user decides (disable the n8n trigger, not just the Twilio sub).

## Decision log
- 2026-09-21 Switched LangGraph → Claude Agent SDK (native subagents).
- 2026-09-21 One shared Google account for all users (not per-user) — simpler; revisit for Cue parity.
- 2026-09-22 Parallel run with Cue on the same number (user choice).
- 2026-09-22 New OAuth client "cue" replaced the old "n8n Sellify" client.
- 2026-09-22 Gmail send moved from SMTP app-password to Gmail API (one Google credential).
- 2026-09-22 Roadmap: Instinct-style proactive follow-ups + browser automation (user choice).
- 2026-09-23 Documents V1 stores extracted text only (not the original file): less sensitive data at
  rest, one-step deletion. Embeddings = OpenAI text-embedding-3-small to match Cue's Canon.
- 2026-09-23 Sellify = Cue migration. DB moved to Cue's Supabase; Sellify writes only `sellify_*`
  tables until n8n Cue is switched off.

## Maintaining this file
At the end of any session that changes code, infra, credentials setup, or plans: update
"Current status", "Backlog", and "Decision log" in place (edit, don't append a diary).
Keep it under ~200 lines. Never paste secrets, tokens, passwords, or end-user phone numbers.
