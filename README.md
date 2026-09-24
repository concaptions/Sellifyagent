# Sellify Personal Assistant

A WhatsApp-based personal AI assistant built with the **Claude Agent SDK**. Users interact via WhatsApp to manage their calendar, email, notes, and search the web.

## Architecture

```
User's WhatsApp
      │
   Twilio          (WhatsApp message bridge)
      │
   FastAPI         (webhook server)
      │
   Claude Agent SDK   (drives Claude Code as a library; authenticated with a
      │                real ANTHROPIC_API_KEY — see note below)
      │
   ┌─────────────────────────────────────┐
   │  Manager Agent (top-level, per turn) │
   │  ├── Email Agent (Gmail)            │
   │  ├── Calendar Agent (Google Cal)    │
   │  ├── Notes Agent (Postgres)         │
   │  └── Research Agent (Tavily)        │
   └─────────────────────────────────────┘
      │
   Supabase/Postgres  (user data, notes, chat history)
```

### How it works

1. User sends a WhatsApp message
2. Twilio forwards it to the FastAPI webhook
3. `PersonalAssistant` calls `claude_agent_sdk.query()` with a manager system prompt and four named subagents (`AgentDefinition`)
4. Claude decides which subagent(s) to delegate to (via the SDK's built-in `Agent`/Task mechanism) and which tools to call
5. Tools run in-process (registered via `create_sdk_mcp_server`) against Gmail, Google Calendar, Postgres, and Tavily
6. The response flows back through Twilio to the user's WhatsApp

### Why the Claude Agent SDK instead of a raw API client

The SDK is Claude Code packaged as a library, giving us native multi-agent orchestration for free: `ClaudeAgentOptions.agents` defines named subagents with their own prompt and tool allow-list, and Claude delegates to them itself via the built-in `Agent`/Task mechanism — no hand-rolled supervisor loop needed.

**Authentication:** this is a deployed third-party product, so it authenticates with a real `ANTHROPIC_API_KEY` from [platform.claude.com](https://platform.claude.com), set as a normal environment variable. (An earlier version of this doc assumed the SDK could ride on a developer's own claude.ai/Claude Code subscription login — that's explicitly against Anthropic's terms for a deployed product: *"Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK."* A metered API key is the only correct option here, and the SDK picks it up from the environment automatically — no other config needed.)

### Per-user isolation

All data is keyed by phone number, and this is enforced at two levels:

- **Conversation/session**: each phone number gets its own explicit Claude Agent SDK `session_id`, generated the first time we see that number and passed back via `resume` on every later turn. We never rely on the SDK/CLI's default session-selection behavior, since that can silently attach to an ambient session (this bit us during testing — see "Lessons" below).
- **Notes data**: the notes tools are rebuilt fresh for every incoming message via `build_notes_tools(user_phone)`, a factory that closes over the calling user's phone number. This avoids depending on the LLM correctly passing back an internal user-id argument, or a contextvar surviving the SDK's subprocess/transport boundary.

### Lessons applied from the existing Cue/Sellify PA project

This design deliberately carries over hard-won lessons documented in the existing n8n-based Cue assistant:

- **Truth about actions**: the manager prompt states a claim of "done" is only valid if a subagent actually returned a tool result this turn — the single biggest recurring bug in the reference project was Claude confidently claiming to have created calendar events/reminders it never actually called a tool for.
- **Principles, not lists**: prompts avoid enumerating accepted words/formats (Cue's prompt shrank from 12KB to under 5KB after removing lists, because models both miss edge cases lists don't cover and sometimes recite the list back to the user as advice).
- **Fails closed on missing identity**: notes tools require an explicit `user_id`; there is no "return everything" fallback path.
- **Ambient session state is not identity**: never assume the SDK/runtime's default session selection matches "this WhatsApp user" — always assign session ids explicitly (see above).

## Setup

### 1. Environment

```bash
cp .env.example .env
# Fill in your API keys (Twilio, Google, Tavily, Postgres). No LLM API key needed.
```

### 2. Anthropic API key

Get a real API key from [platform.claude.com](https://platform.claude.com) and set it as `ANTHROPIC_API_KEY`. The Claude Agent SDK reads it from the environment automatically — no other setup needed (see the auth note above for why this is required rather than riding on a personal Claude login).

### 3. Google OAuth

This app connects **one shared Google account** (Calendar + Gmail) for the whole assistant — not a separate account per WhatsApp user. Because the server is headless (no browser), it uses a web OAuth callback flow instead of the interactive `run_local_server()` flow, and reads the OAuth client config from environment variables rather than a `credentials.json` file (that file is never committed since it holds the client secret, so a deployed host wouldn't have it anyway):

1. Create a project in [Google Cloud Console](https://console.cloud.google.com), enable the Calendar API and Gmail API
2. Create an OAuth 2.0 client of type **Web application** (not Desktop — Desktop-type clients only accept loopback/oob redirects, which won't work here)
3. Add `https://<your-deployed-domain>/oauth/google/callback` to that client's **Authorized redirect URIs**
4. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from that OAuth client
5. Set `PUBLIC_BASE_URL` in `.env`/your host's env vars to your deployed app's own public HTTPS URL (no trailing slash) — this is used to build the exact redirect URI, since guessing it from proxy headers is unreliable
6. Once deployed, visit `https://<your-deployed-domain>/oauth/google/start` **once** in a real browser, sign in with the Google account you want connected, and approve. Tokens are saved to `token.json` (path configurable via `GOOGLE_TOKEN_FILE`); the token refresher logic in `google_auth.py` keeps them alive after that.

**Filesystem persistence:** `token.json` is written to local disk by default. On most PaaS hosts the filesystem is ephemeral across redeploys unless you attach a persistent volume — without one, a redeploy means re-visiting `/oauth/google/start` again. Mount a volume and point `GOOGLE_TOKEN_FILE` at a path inside it (e.g. `/data/token.json`), or move token storage into Postgres (matching the pattern the existing Cue project uses in `pa_users.profile`), if you want it to survive redeploys.

*(If you have a machine with a browser and want to generate `token.json` locally first using a Desktop-type OAuth client instead: download that client's JSON as `credentials.json`, then run `python -c "from src.utils.google_auth import run_local_console_auth; run_local_console_auth()"` and copy the resulting `token.json` to the server.)*

### 4. Twilio

1. Get a WhatsApp-enabled Twilio number (sandbox for testing, or a real approved sender for production)
2. Point that number's webhook URL to `https://<your-deployed-domain>/whatsapp/webhook`
3. Add your Twilio Account SID, Auth Token, and the WhatsApp number (as `whatsapp:+<number>`) to `.env`

### 5. Deploy (e.g. Railway)

```bash
pip install -r requirements.txt   # or let Railway install from requirements.txt automatically
```

This repo includes a `Procfile` (`web: uvicorn app:app --host 0.0.0.0 --port $PORT`) that Railway (or any Procfile-aware host) picks up automatically. Steps on Railway specifically:

1. Connect this GitHub repo as a new Railway project
2. Add a PostgreSQL database service to the same project (Railway wires up its `DATABASE_URL` automatically; reference it on the web service as `${{Postgres.DATABASE_URL}}`)
3. Set environment variables on the web service from `.env` (`ANTHROPIC_API_KEY`, Twilio, Gmail, `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`, Tavily, `DATABASE_URL`)
4. Generate a public domain for the web service, set it as `PUBLIC_BASE_URL` (redeploy so the env var takes effect)
5. Visit `/oauth/google/start` once (see step 3 above)
6. Point Twilio's webhook at `https://<that-domain>/whatsapp/webhook`

For local development instead, run `python app.py` (auto-reloads) and expose it with ngrok:
```bash
ngrok http 5000
```

### 6. Database (optional)

Notes and chat history persist in Postgres. Without `DATABASE_URL`, the app still works — notes tools will return errors, but calendar/email/research work fine.

```bash
# If using Supabase or any Postgres instance
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

## Testing

Test without WhatsApp:

```bash
curl -X POST http://localhost:5000/webhook/test \
  -d "phone=+1234567890" \
  -d "message=What's on my calendar this week?"
```

This was verified end-to-end during development, including:
- Per-user note isolation (two different phone numbers saving/listing notes never cross-contaminate)
- Multi-turn conversation memory (asking a follow-up question about something just said)
- Graceful degradation when Google/Tavily credentials aren't configured (the assistant says so plainly rather than fabricating an answer)

## Project Structure

```
├── app.py                    # FastAPI entry point (WhatsApp webhook + Google OAuth routes)
├── Procfile                  # Railway/Heroku-style start command
├── src/
│   ├── config.py             # Environment config
│   ├── database.py           # Postgres operations
│   ├── agents/
│   │   └── assistant.py      # PersonalAssistant - builds ClaudeAgentOptions, runs query()
│   ├── channels/
│   │   └── whatsapp.py       # Twilio WhatsApp sender + message splitting
│   ├── prompts/
│   │   ├── manager.py        # Top-level manager system prompt
│   │   ├── email_agent.py    # Email subagent prompt
│   │   ├── calendar_agent.py # Calendar subagent prompt
│   │   ├── notes_agent.py    # Notes subagent prompt
│   │   └── research_agent.py # Research subagent prompt
│   ├── tools/
│   │   ├── calendar/         # get_events, create_event, delete_event (SDK @tool)
│   │   ├── email/            # read_emails, send_email (SDK @tool)
│   │   ├── notes/            # build_notes_tools(user_phone) factory (SDK @tool)
│   │   └── research/         # search_web (Tavily, SDK @tool)
│   └── utils/
│       ├── google_auth.py    # Google OAuth: web callback flow + token refresh
│       └── message_splitter.py  # WhatsApp 1600-char limit handler
├── requirements.txt
└── .env.example
```
