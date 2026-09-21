# Sellify Personal Assistant

A WhatsApp-based personal AI assistant built with LangGraph and Claude. Users interact via WhatsApp to manage their calendar, email, notes, and search the web.

## Architecture

```
User's WhatsApp
      │
   Twilio          (WhatsApp message bridge)
      │
   FastAPI         (webhook server)
      │
   LangGraph       (multi-agent orchestrator)
      │
   Claude          (Anthropic - powers all agents)
      │
   ┌─────────────────────────────────────┐
   │  Manager Agent (supervisor)         │
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
3. The **Manager Agent** (Claude) analyzes the request and delegates to specialist agents
4. Specialist agents use their tools (Gmail API, Calendar API, Tavily, Postgres) to fulfill the request
5. The response flows back through Twilio to the user's WhatsApp

### Multi-agent pattern

Uses LangGraph's ReAct agent pattern with a supervisor architecture:
- **Manager**: Routes requests to the right specialist, handles multi-part requests
- **Sub-agents**: Each owns a domain (email, calendar, notes, research) with dedicated tools
- Communication flows through a `SendMessage` tool — sub-agents cannot talk to each other

### Per-user isolation

All data is keyed by phone number:
- Conversation memory uses phone as thread ID (separate LangGraph checkpoints per user)
- Notes are stored per user in Postgres
- Chat history is per user

## Setup

### 1. Environment

```bash
cp .env.example .env
# Fill in your API keys
```

### 2. Google OAuth

1. Create a project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable Calendar API and Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download `credentials.json` to the project root
5. On first run, a browser window opens for auth — `token.json` is saved automatically

### 3. Twilio

1. Set up a [Twilio WhatsApp Sandbox](https://www.twilio.com/docs/whatsapp/sandbox)
2. Point the webhook URL to `https://your-server/whatsapp/webhook`
3. Add your Twilio credentials to `.env`

### 4. Install & Run

```bash
pip install -r requirements.txt
python app.py
```

For development, expose with ngrok:
```bash
ngrok http 5000
```

### 5. Database (optional)

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

## Project Structure

```
├── app.py                    # FastAPI entry point (WhatsApp webhook)
├── src/
│   ├── config.py             # Environment config
│   ├── database.py           # Postgres operations
│   ├── agents/
│   │   ├── assistant.py      # PersonalAssistant - main class
│   │   ├── orchestrator.py   # Multi-agent wiring + SendMessage tool
│   │   └── base.py           # Base Agent class (LangGraph wrapper)
│   ├── channels/
│   │   └── whatsapp.py       # Twilio WhatsApp sender + message splitting
│   ├── prompts/
│   │   ├── manager.py        # Supervisor prompt
│   │   ├── email_agent.py    # Email agent prompt
│   │   ├── calendar_agent.py # Calendar agent prompt
│   │   ├── notes_agent.py    # Notes agent prompt
│   │   └── research_agent.py # Research agent prompt
│   ├── tools/
│   │   ├── calendar/         # get_events, create_event, delete_event
│   │   ├── email/            # read_emails, send_email
│   │   ├── notes/            # add_note, get_notes, search_notes
│   │   └── research/         # search_web (Tavily)
│   └── utils/
│       ├── google_auth.py    # Google OAuth flow
│       └── message_splitter.py  # WhatsApp 1600-char limit handler
├── requirements.txt
└── .env.example
```
