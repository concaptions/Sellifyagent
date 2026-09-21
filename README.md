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
   Claude Agent SDK   (drives the Claude Code CLI — billed to this account's
      │                own subscription, not a metered API key)
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

The SDK drives the same Claude Code CLI this development environment runs on, authenticated through the account's own login rather than a separate `ANTHROPIC_API_KEY`. That means usage is billed against the account's existing subscription/credits. It also gives us native multi-agent orchestration for free: `ClaudeAgentOptions.agents` defines named subagents with their own prompt and tool allow-list, and Claude delegates to them itself — no hand-rolled supervisor loop needed.

**Deployment requirement:** the host running this app needs an authenticated Claude Code CLI session (run `claude login` once, or provision the equivalent credentials the CLI expects). There is no API key to put in `.env`.

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

### 2. Claude Code CLI authentication

The Claude Agent SDK bundles and drives the Claude Code CLI. On the deployment host:

```bash
claude login
```

(or otherwise provision the credentials/config the CLI expects — see the Claude Agent SDK docs for headless/CI authentication options).

### 3. Google OAuth

1. Create a project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable Calendar API and Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download `credentials.json` to the project root
5. On first run, a browser window opens for auth — `token.json` is saved automatically

### 4. Twilio

1. Set up a [Twilio WhatsApp Sandbox](https://www.twilio.com/docs/whatsapp/sandbox)
2. Point the webhook URL to `https://your-server/whatsapp/webhook`
3. Add your Twilio credentials to `.env`

### 5. Install & Run

```bash
pip install -r requirements.txt
python app.py
```

For development, expose with ngrok:
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
├── app.py                    # FastAPI entry point (WhatsApp webhook)
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
│       ├── google_auth.py    # Google OAuth flow
│       └── message_splitter.py  # WhatsApp 1600-char limit handler
├── requirements.txt
└── .env.example
```
