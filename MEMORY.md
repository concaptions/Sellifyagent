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
| Google Calendar (read/create/update/delete) | ✅ Live, verified. Invitees + Google Meet: `create_calendar_event(attendees, add_meet_link)` sends Google invitations (`sendUpdates=all`, `conferenceDataVersion=1`); `update_calendar_event` reschedules/re-invites with notifications. Live-verified 2026-09-23: asks for an unknown invitee's email once, invites + Meet link, reschedule keeps Meet link and notifies, listing shows invitees, contact email remembered |
| Conversation memory across redeploys | ✅ Session id in `sellify_users.profile._session_id`; transcripts under `/data/claude` (confirmed in logs after deploy 51cd70f) |
| Gmail read | ✅ Live, verified. `read_emails` = search + ~200-char snippet; `read_email(id)` = full body (plain or HTML→text with comments stripped, ≤12k chars, attachment names); `read_email_attachment(id, filename)` = text of a PDF/DOCX/text attachment via `extract_text` (nothing stored). Added 2026-09-24 after the client hit a cut-off date; Both live-verified 2026-09-24 via the probe (5.5k-char HTML mail in full; an email with two PDF attachments: names, sizes and text of each) |
| Gmail send | ⚠️ Rewired SMTP → Gmail API (commit c97345a), deployed; **live send not yet confirmed** |
| Notes | ✅ Per-user isolated; on Cue's Supabase (`sellify_notes`), live-verified 2026-09-23 |
| Document upload (PDF/DOCX/text) | ✅ Live-verified 2026-09-23 from a real phone (4 MB PDF → 252 chunks embedded, ~1 min) and via signed replay (Q&A + delete). Stores extracted text only |
| Webhook security | ✅ Real Twilio signatures pass (real phone); forged → 403; unsigned `/webhook/test` → 404 |
| Web search | ✅ Claude Code built-in `WebSearch`/`WebFetch` (no Tavily key); live-verified 2026-09-23 (same-day headline with source URL; page fetch) |
| Reminders + proactive follow-ups | ✅ `sellify_reminders` + `reminders_agent` + 60 s scheduler; live-verified 2026-09-23 via `/webhook/test`. Repeating reminders: min every 10 min, created only after the user OKs the schedule, every message carries "Reply *stop*", and "stop" is handled in `app.py` code. **Not yet fired to a real phone** |
| Booking worker (browser) | ✅ `browser_agent` + Playwright (Dockerfile on Playwright image). Guest bookings only; login/password/card fields blocked in code; final click locked until the user's own "yes" (`src/utils/approvals.py`); screenshot proof via `/media/<token>.png`. Live-verified 2026-09-23 on httpbin's form: fill → approval question + screenshot → "no" declines → "yes" submits → result screenshot served |
| Typing indicator | ✅ `_keep_typing` in `app.py` calls Twilio's typing-indicator API (public beta) every 20 s during a turn; 200 OK on real messages 2026-09-23 |
| Database Q&A (`data_agent`) | ✅ Per-user Cue records (`pa_logs`, `pa_personas`, `pa_reminders`, `n8n_chat_histories` keyed `pa-<phone>`) for everyone; business tables (`leads`, `products`, `documents`) **only for phones in `BUSINESS_DATA_PHONES`** (Railway env var), read-only via Postgres role `sellify_reader` (SELECT grant + RLS policy, READ ONLY txn). Live-verified 2026-09-23 (lead funnel, September count, catalogue, KB; writes and outsiders refused). **`BUSINESS_DATA_PHONES` currently holds only a synthetic test number — user must put the real owner numbers in** |
| Name | ✅ Assistant introduces itself as **Cue** (manager prompt) |
| Personal memory | ✅ `memory_agent` saves facts to `sellify_users.profile`; profile (+ Cue's `pa_users` name/timezone/core_prompt) injected into every turn; per-user timezone drives reminders. Live-verified 2026-09-23 (save without asking, recall, correction, reminder in user's tz) |
| Cue's earlier documents | ⚠️ `documents_agent` lists/searches `pa_knowledge_chunks` (read-only) via `match_cue_knowledge`, keyed by `pa_users.id`. Live: no-history path verified; **real-user listing/search to be confirmed from the user's phone** (test scripts must not carry real numbers) |
| Voice notes | ✅ `audio/*` media → Whisper (`OPENAI_TRANSCRIBE_MODEL`, default `whisper-1`) → `[Voice note, transcribed] …` in the message. Live-verified 2026-09-23 (flac sample; transcript recalled next turn) |
| Photos (vision) | ✅ `image/*` media → PIL downscale ≤1568 px JPEG → base64 image block via SDK streaming input (`_user_turn_with_images`). Live-verified 2026-09-23 (described a public test photo). Twilio media 404 right after the webhook is retried (gotcha 13) |
| Image generation + charts | ✅ `images_agent`: `generate_image` (OpenAI `OPENAI_IMAGE_MODEL`, default `gpt-image-1`) and `render_chart` (matplotlib) → `/media/<token>.png` → attached as WhatsApp image. Live-verified 2026-09-23 (BP line chart 47 KB; generated poster 2.2 MB, both served) |
| Google per user | ⚠️ Each WhatsApp number connects its **own** Google (Calendar + Gmail): tokens in `sellify_users.profile._google_tokens`; personal 30-min link `/oauth/google/start?t=<nonce.exp.sig>` (nonce→phone map in memory, HMAC with `TEST_WEBHOOK_TOKEN`; phone never in the URL); `/start` without a valid token → 403. Owner numbers (`BUSINESS_DATA_PHONES`) fall back to the shared `/data/token.json` (the client's account). Calendar/email tools are per-user closures; `google_connect_link` tool reports status + link. Live-verified 2026-09-23 (stranger → personal link → 307 to accounts.google.com; tampered/bare → 403; owner → shared account). Real consent round-trips confirmed 2026-09-24 (the client and one more user connected via their links; callbacks 200, tokens used the same turn). **Google Drive: not connected at all** (no scope) — the client asked for Drive files; adding `drive.readonly` + a `drive_agent` awaits the user's OK (access-scope change; everyone reconnects once). Google consent screen is in Testing mode: each new user's Gmail must be added as a test user (or publish the app) |
| Code on `main` | ❌ Only README — all code is on branch `claude/jolly-ramanujan-l0q173`, draft PR #1 |

## Request flow
```
WhatsApp → Twilio → POST /whatsapp/webhook (FastAPI, returns empty TwiML at once)
  → asyncio.create_task → PersonalAssistant.ainvoke(msg, user_phone)
  → claude_agent_sdk.query(): manager prompt + 7 AgentDefinitions
  → tools run in-process via create_sdk_mcp_server
  → reply → WhatsAppChannel (Twilio REST, split at 1600 chars)
```
`POST /webhook/test` (form: phone, message) runs the same agent **synchronously**
and returns `{"phone","reply"}` — no Twilio involved. Best way to test.

Reminders: `_reminder_loop` in `app.py` (started by the FastAPI lifespan, only if DB init
succeeded) polls every 60 s → `db.claim_due_reminders` (atomic pending→sending, SKIP LOCKED,
retries stuck rows after 15 min, max 3 attempts) → `_deliver_reminder` runs the agent with a
`[REMINDER TRIGGER] …` prompt → sends via WhatsApp → `db.finish_reminder` marks sent/failed/
next occurrence **from code, never from the model**. Kinds: `reminder` (nudge; falls back to
the raw text if the agent errors) and `followup` (agent does work first, e.g. checks Gmail).
Business-initiated WhatsApp messages >24 h after the user's last message need a Twilio
content template or Twilio rejects them (error 63016) — same limit Cue has.

Bookings: `browser_agent` → `src/tools/browser/booking.py` (open/read/click/type/select/
screenshot + `request_booking_approval`) over `src/utils/browser.py` (one Chromium, one context
per user, 15 min idle close, nothing persisted). Commit-looking buttons (book/confirm/reserve/
submit/pay…) are refused until `booking_gate.is_approved(user)`; the only thing that sets that is
`app.py` matching the user's *own* next message against a yes/no regex (`resolve_from_message`),
one commit per approval, 10 min TTL. Password/card-like fields and login pages/buttons are refused
outright. After a commit the tool screenshots the page → `media_store` → `/media/<token>.png`;
`app.py` attaches our own media URLs found in the reply as WhatsApp images.

## File map
- `app.py` — FastAPI routes: `/whatsapp/webhook`, `/webhook/test`, `/health`,
  `/oauth/google/start`, `/oauth/google/callback`, `/oauth/google/status`
- `src/agents/assistant.py` — builds `ClaudeAgentOptions`, per-user session ids
- `src/prompts/*.py` — manager + 4 subagent prompts (small, principle-based)
- `src/tools/{calendar,email,notes,documents,reminders,browser,memory,data}/` — SDK `@tool` functions.
  `data/records.py`: per-user Cue records for all; `describe_business_data`/`query_business_data`
  built only when `user_phone in BUSINESS_DATA_PHONES` (`db.run_business_query`: one SELECT,
  `SET LOCAL ROLE sellify_reader`, READ ONLY, 10 s timeout, 50 rows).
  `memory/profile.py`: `remember/forget/recall` + `format_profile` (the "What you know about the
  user" block in the manager prompt). `db.get_profile(phone)` merges `sellify_users` with Cue's
  `pa_users` (read-only); facts the user stated win over Cue's values. Web research
  has no tool module: `research_agent` uses the CLI's built-in `WebSearch`/`WebFetch`
  (`RESEARCH_TOOL_NAMES` in `assistant.py`)
- `src/utils/documents.py` — media download (Twilio auth only to *.twilio.com), extract, chunk, embed, ingest
- `src/utils/google_auth.py` — web OAuth flow, PKCE verifier store, token refresh
- `src/utils/browser.py`, `src/utils/approvals.py`, `src/utils/media_store.py` — booking worker
- `src/utils/media_ai.py` — transcribe (Whisper), prepare_image (PIL), generate_image (OpenAI), render_chart
  (matplotlib), publish → `/media/`. `src/tools/images/` — `images_agent` tools.
- `app.py` routes media by type: `audio/*` → `_transcribe_attachment`, `image/*` → `_prepare_photo`
  (image blocks into `ainvoke(images=…)`), everything else → `_ingest_attachment` (documents).
- `Dockerfile` (Playwright python image; Railway builds from it, Procfile unused) + `.dockerignore`
  (excludes `.env`, `token.json`, `credentials.json`)
- `src/database.py` — Sellify's own tables `sellify_users`, `sellify_notes`, `sellify_chat_history`,
  `sellify_reminders`, `sellify_documents`, `sellify_document_chunks` (pgvector 1536)
- `src/channels/whatsapp.py`, `src/utils/message_splitter.py`
- `Procfile` — legacy (Railpack); the Dockerfile CMD is what runs now

## Infrastructure (IDs are not secrets)
**Railway** — workspace Buildberg, project `tender-energy`
- project `0c7eae52-1d94-48dd-9c39-b52478345c78`, env production `d42c52fe-fb47-4fbc-b5c2-feb509ecd8d4`
- service `Sellifyagent` `b4181c17-8822-45de-8a49-80b7d7c72110` — deploys from branch
  `claude/jolly-ramanujan-l0q173` on push; domain `https://sellifyagent-production.up.railway.app`
- volume `sellifyagent-data` mounted at `/data` (Google token at `/data/token.json`; Claude session
  transcripts under `/data/claude` via `CLAUDE_CONFIG_DIR`)
- `DATABASE_URL` → **Cue's Supabase** (project ref `nnktgpjvtmkqongeubat`, transaction pooler
  :6543, superuser — bypasses RLS). Railway `Postgres` `efca358d-a4c2-4900-aa37-286c6f44e9de` is
  no longer used (holds only old test data); don't delete without asking.
- Railway Function `delivery-status-check` `bc20f51f-b26e-4c0d-93ef-16f0ebbba3b3` — used as a
  network probe (Bun/TS script; Twilio creds via `${{Sellifyagent.*}}` refs). Leftover test
  services still exist: `twilio-webhook-config`, `agent-smoke-test`, `agent-test-suite`,
  `webhook-oauth-diag` — user has not approved deleting them.
- Env vars on Sellifyagent: ANTHROPIC_API_KEY, TWILIO_*, FROM_WHATSAPP_NUMBER, GOOGLE_CLIENT_ID/SECRET,
  GOOGLE_TOKEN_FILE, PUBLIC_BASE_URL, DATABASE_URL, OPENAI_API_KEY, TEST_WEBHOOK_TOKEN,
  BUSINESS_DATA_PHONES, CLAUDE_CONFIG_DIR=/data/claude,
  GMAIL_ADDRESS/GMAIL_APP_PASSWORD (now unused). No TAVILY_API_KEY needed. The probe function has `TEST_WEBHOOK_TOKEN` and
  `PUBLIC_BASE_URL` as `${{Sellifyagent.*}}` refs.

**Twilio** — WhatsApp number `+65 8415 1532`
- Messaging Service `MG5c93d431fb48a69979d4390d353e0b65` ("Alluora_WA_Agent"):
  `inbound_request_url` → Sellify `/whatsapp/webhook`
- WhatsApp Sender `XE4e11e1b1329072d9db0df649b8dc7ebf`: webhook → Sellify `/whatsapp/webhook`.
  **The Sender-level webhook overrides the Messaging Service URL.**
- **n8n Cue is cut off (2026-09-23, user-approved):** Event Streams subscription
  `DF21bd8006e280b0ad56063e6c60e01d39` (created by n8n's Twilio Trigger node; sink
  `DG2ed2453a79e56fe0979f0432ab54c006`; event `com.twilio.messaging.inbound-message.received`)
  was deleted; the account now has no subscriptions. Only Sellify replies. The n8n workflows
  themselves (`Zt6HfEJE9W4cb5yz` main, `hZ3ILef5sJkBjxvV` reminder scheduler) are still active
  on `primary-production-302c.up.railway.app` — the n8n MCP here points at a different
  instance, so the user must deactivate them in the n8n UI (re-activating the main workflow
  would recreate the subscription). The n8n reminder scheduler still fires `pa_reminders`.

**Google OAuth** — client "cue" in GCP project `cue-rich-sng`, Web application type
- Redirect URI: `https://sellifyagent-production.up.railway.app/oauth/google/callback`
- Consent screen in **Testing** mode; test user `concaptions@gmail.com` (the connected account)
- Scopes: calendar, gmail.readonly, gmail.send. Per-user tokens since 2026-09-23; the shared
  `/data/token.json` (client's account) is the fallback for owner numbers only.
- Connect: the user asks Cue ("connect my Google") and opens the personal link. Admin check of
  the shared token: `GET /oauth/google/status`.

**Cue's Supabase (shared DB)** — Cue n8n owns and still writes:
- `pa_users` (phone, name, timezone, persona_name, profile jsonb: core_prompt, active_persona,
  google_tokens — must stay a JSON *object*), `pa_personas`, `pa_reminders`, `n8n_chat_histories`
- `pa_knowledge_chunks` (`id uuid, user_id uuid = pa_users.id`, `source` = `canon` |
  `upload:<name or MM… media sid>`, `section`, `chunk_index`, `content`, `embedding vector(1536)`
  OpenAI `text-embedding-3-small`, `metadata`, `created_at`) +
  `match_cue_knowledge(query_embedding vector, match_count int = 6, filter jsonb)` →
  `TABLE(id uuid, content, metadata, similarity)`; fails closed without `filter.user_id` (the uuid).
  Sellify reads these via `db.list_canon_sources` / `db.search_canon` using
  `profile["cue_user_id"]` from `db.get_profile`.
- `pa_reminders` cols: `id,user_id,title,notes,due_at,status,fired_at,recurrence,created_at,updated_at,repeat_until`;
  `pa_logs`: `id,user_id,kind,logged_at,value_num,data,note,source,sheet_synced_at,created_at`;
  `pa_personas`: `id,user_id,name,slug,description,content,…`.
- All `sellify_*` tables have RLS enabled with no policies (set at startup) so Supabase's public
  REST API/anon key can't read them; the app connects as table owner and bypasses RLS. Any new
  table must be added to `_lock_tables` in `src/database.py`. The DB also holds unrelated
  non-Cue tables (`documents`, `leads`, `products`) — the client's Alluora WhatsApp sales bot
  (leads = customer conversations with status/interest/purchase; products = catalogue with
  `price` text + `metadata.url`; documents = product Q&A KB). Read-only for owner numbers via
  `data_agent`; never write to them.
- **Rule (still in force):** Sellify reads `pa_*` but writes only `sellify_*` — the n8n reminder
  scheduler still runs, so writing `pa_reminders` would double-fire.
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
   Conversation memory = the SDK session transcript (whole chat up to the model's context window,
   auto-compacted when full). It survives redeploys only because (a) `CLAUDE_CONFIG_DIR=/data/claude`
   puts transcripts on the volume and (b) the session id is persisted in
   `sellify_users.profile._session_id` (`db.get/set_session_id`; underscore keys are never facts).
   A resume that fails is retried once as a fresh session. `sellify_chat_history` is a log only;
   it is not fed back to the model.
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
    `X-Twilio-Signature`, url = `PUBLIC_BASE_URL + "/whatsapp/webhook"`. The Railway MCP
    `get-logs`/`list-deployments` tools sometimes fail with "does not match output schema";
    the `railway-agent` tool can still return the same logs verbatim (ask for raw lines).
11. Railway `list-deployments` status can stay `BUILDING` after a deploy is actually live — recheck.
12. (Historical) During the parallel run every message got two replies. Since 2026-09-23 only
    Sellify replies; if two replies reappear, the n8n workflow was re-activated.
13. WhatsApp sends a document's filename as the message Body (and Twilio media often has no
    Content-Disposition), so `app.py` uses the Body as the filename when it looks like one.
    Twilio also fires the webhook before the media has always landed: the first GET can 404
    (seen live with photos, ~200 ms after the webhook). `download_media` retries 404/5xx from
    Twilio hosts with pauses 1/2/3/5 s before giving up.
14. `PersonalAssistant.ainvoke` holds a per-user `asyncio.Lock`: a reminder turn and a user
    turn resuming the same SDK session at once would corrupt it.
15. Documents are retrieved only when the user asks (tool-based). User explicitly rejected
    auto-retrieval on every message.
17. Timezones are per user: `profile["timezone"]` (fact > Cue's `pa_users.timezone` > column
    default Asia/Singapore). `USER_TIMEZONE` in assistant.py is only the last-resort default.
    The dev is in Pakistan, the client in Singapore — never assume one timezone.
20. Image blocks can only reach `query()` through the streaming-input form (an async iterable of
    `{"type":"user","message":{"role":"user","content":[…]},"parent_tool_use_id":None,"session_id":"default"}`).
    `/oauth/google/start` is gated by a signed token because whoever completes it becomes the
    shared Google account — never hand out the bare URL. For live media tests use fixtures the
    open internet serves to non-browsers: `raw.githubusercontent.com/openai/whisper/main/tests/jfk.flac`
    (speech), `httpbin.org/image/jpeg` (photo); Wikimedia 403s and the UIC sound files are gone.
    Generated images are large PNGs (~2 MB); WhatsApp's image cap is 5 MB.
19. Supabase's `postgres` login is not a superuser: `SET ROLE` needs `GRANT role TO CURRENT_USER`,
    and RLS applies to every non-owner role (zero rows, no error) — hence the reader policy.
    Never bind parameters around model-written SQL (psycopg2 reads its `%` as placeholders).
18. A tool-builder signature mismatch (`build_reminder_tools`) once broke every turn after
    deploy with a 500. Before pushing agent/tool changes, run the full-options smoke check:
    `PersonalAssistant()._build_options(phone, profile)` for `{}` and a populated profile.
16. Playwright's sync API can't be used from the asyncio loop; the browser tools use the async
    API in-process (SDK tools run in the app's loop). Chromium as root needs `--no-sandbox`. In
    this sandbox set `PLAYWRIGHT_CHROMIUM_PATH=/opt/pw-browsers/chromium` to test locally.

## Backlog (priority order)
1. User to set `BUSINESS_DATA_PHONES` on Railway (their own + the client's number) and
   deactivate the n8n Cue workflows in the n8n UI. Confirm from a real phone: Gmail API send;
   a reminder arriving; earlier-documents listing; business-data questions; a real invite.
2. Cue prompt parity: port the voice/rules from the handover `system-prompt.md`, personas,
   core_prompt from `pa_users.profile`. Reminders outside Twilio's 24 h window: register a WhatsApp content template and send
   reminders via it (else they fail with 63016).
3. Pin the model: `ClaudeAgentOptions(model="claude-sonnet-5")` — recommended, awaiting user OK.
4. Booking worker follow-ups: live-verify on real booking sites; sites with captchas/JS-heavy
   widgets may need per-site handling; browser sessions and approvals are in-memory (lost on
   redeploy). Logged-in / payment bookings **still need explicit user decisions on credential
   storage, allowed sites — do not build on assumptions.**
5. Media follow-ups: PDF form filling (user asked live, not built); voice replies (TTS) if
   wanted; convert generated PNGs to JPEG to shrink delivery. Document upload follow-ups: scanned PDFs via OCR/vision; per-tier storage caps; staleness
   nudges; when Canon promotion is built, Canon facts must store a source-document id so
   deleting a doc flags them; keep original files only if needed (private Supabase Storage).
6. Cue feature parity: personal log writes, personas switching, prompt parity. (Canon read,
   photo ingestion and per-user Google tokens are done.)
7. Delete now-unused `GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD` on Railway; user should rotate that
   Gmail password (it was shared in plaintext in chat).
8. Merge PR #1 so `main` has the code; clean up leftover Railway test services (ask first).
9. Retire the n8n Cue path when the user decides (disable the n8n trigger, not just the Twilio sub).

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
- 2026-09-23 Web search via Claude's built-in WebSearch/WebFetch, not Tavily (one API bill, no
  extra key). Reminders live in `sellify_reminders` (not `pa_reminders`: Cue's scheduler would
  double-fire). Document retrieval stays on-demand only (user decision).
- 2026-09-23 Personal memory in `sellify_users.profile` (not `pa_users.profile`, which n8n still
  writes); Cue's earlier documents read in place from `pa_knowledge_chunks`, not migrated.
- 2026-09-23 Calls with other people = calendar events with attendees (Google sends the
  invites); contacts' emails are remembered as `<name>_email` facts.
- 2026-09-23 Google went per user (supersedes the 09-21 shared-account decision): a shared
  account can't serve several people, and a reconnect link would have let anyone replace it.
  Owner numbers keep the shared token as fallback so the client isn't interrupted.
- 2026-09-23 Voice/photo/image features use the existing OpenAI key (Whisper, gpt-image-1) and
  Claude vision; no new vendor. Generated media is served from the app's own `/media/` store.
- 2026-09-23 Business tables opened to owner numbers only (user request); enforcement is a
  Postgres role with SELECT on exactly three tables, not SQL parsing.
- 2026-09-23 n8n Cue path switched off (Twilio subscription deleted, user decision); assistant
  renamed Cue; typing indicator added (Twilio beta endpoint, best effort).
- 2026-09-23 Booking worker (user-approved): guest bookings only, in the app process (Dockerfile
  on the Playwright image) rather than a separate service; approval and no-login/no-payment rules
  enforced in code, not prompts. Repeating reminders: ≥10 min, user-confirmed, "stop" in code.

## Maintaining this file
At the end of any session that changes code, infra, credentials setup, or plans: update
"Current status", "Backlog", and "Decision log" in place (edit, don't append a diary).
Keep it under ~200 lines. Never paste secrets, tokens, passwords, or end-user phone numbers.
