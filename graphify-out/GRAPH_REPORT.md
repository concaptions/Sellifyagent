# Graph Report - Sellifyagent  (2026-09-28)

## Corpus Check
- Corpus is ~31,848 words - fits in a single context window. You may not need a graph.

## Summary
- 540 nodes · 1226 edges · 30 communities (26 shown, 4 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 94 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- App Core & Project Knowledge
- Google OAuth & Calendar
- Document Ingestion
- Gmail Tools
- Config, Images & WhatsApp Channel
- Reminders
- Docs & Sheets Tools
- Drive Tools
- Browser Pool (Playwright)
- Per-user Tool Builders
- Data Agent Records
- Booking Tools
- Agent Prompts
- Google Tasks Tools
- Safety Gates & Principles
- PersonalAssistant (Agent SDK)
- Memory Profile Tools
- Media Attachments
- Notes Tools
- Google OAuth Routes
- Webhooks & Testing
- App Lifespan & Scheduler
- Typing Indicator
- Media Store
- Contacts Tools
- Approvals & Recent Files

## God Nodes (most connected - your core abstractions)
1. `get_db()` - 38 edges
2. `not_connected()` - 23 edges
3. `scope_not_granted()` - 23 edges
4. `get_google_credentials()` - 17 edges
5. `build_browser_tools()` - 14 edges
6. `build_data_tools()` - 14 edges
7. `Per-user tool closures` - 14 edges
8. `build_reminder_tools()` - 13 edges
9. `get_gmail_service()` - 12 edges
10. `_scoped_service()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `Per-user isolation` --semantically_similar_to--> `Per-user SDK sessions`  [INFERRED] [semantically similar]
  README.md → MEMORY.md
- `Per-user isolation` --semantically_similar_to--> `Per-user tool closures`  [INFERRED] [semantically similar]
  README.md → MEMORY.md
- `Booking approval gate` --references--> `_prepare_message()`  [EXTRACTED]
  MEMORY.md → app.py
- `WhatsApp request flow` --references--> `_process_message()`  [EXTRACTED]
  MEMORY.md → app.py
- `Booking approval gate` --references--> `media()`  [EXTRACTED]
  MEMORY.md → app.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Per-user Google access flow** — memory_per_user_google, memory_scope_per_tool, memory_signed_connect_link, app_oauth_google_start, app_oauth_google_callback, src_utils_google_auth_get_google_credentials, src_utils_google_auth_scoped_service [INFERRED 0.85]
- **Reminder delivery flow** — memory_reminders_scheduler, memory_twilio_24h_window, app_reminder_loop, app_deliver_reminder, src_database_claim_due_reminders, src_database_finish_reminder [INFERRED 0.85]
- **Safety gates enforced in code** — memory_booking_gate, src_utils_approvals_bookinggate, app_prepare_message, claude_truth_about_actions, claude_operational_rules, claude_security_rules [INFERRED 0.85]

## Communities (30 total, 4 thin omitted)

### Community 0 - "App Core & Project Knowledge"
Cohesion: 0.05
Nodes (70): _prepare_message(), _process_message(), Settle, in code, the two things a user can say that must take effect whether or…, Git and deploy workflow, Security rules (non-negotiable), Cue's earlier documents (pa_knowledge_chunks), Owner numbers and business data, Per-user SDK sessions (+62 more)

### Community 1 - "Google OAuth & Calendar"
Cohesion: 0.08
Nodes (48): Credentials, google_auth_oauthlib_flow, google_auth_transport_requests, google_oauth2_credentials, googleapiclient_discovery, hmac, Per-user Google OAuth, Scope check per Google tool (+40 more)

### Community 2 - "Document Ingestion"
Cohesion: 0.10
Nodes (33): _ingest_attachment(), Download and store one attachment; return the system line the agent sees,…, dataclasses, hashlib, Document upload pipeline (text only), Twilio media 404 retry, build_document_tools(), delete_document() (+25 more)

### Community 3 - "Gmail Tools"
Cohesion: 0.14
Nodes (28): base64, email_mime_text, html, Full email and attachment reading, Gmail tools, built per user so each turn uses that user's own Google account…, _label_id(), modify_email(), Inbox housekeeping: archive, read/unread, star, label, trash. Deletion is… (+20 more)

### Community 4 - "Config, Images & WhatsApp Channel"
Cohesion: 0.09
Nodes (28): asyncio, dotenv, httpx, io, logging, Model pinned to claude-sonnet-5, _chart(), _generate() (+20 more)

### Community 5 - "Reminders"
Cohesion: 0.17
Nodes (23): _deliver_reminder(), Run the agent on the due reminder and send its reply to the user. The outcome…, calendar, build_reminder_tools(), cancel_reminder(), create_reminder(), list_reminders(), stop_reminders() (+15 more)

### Community 6 - "Docs & Sheets Tools"
Cohesion: 0.17
Nodes (23): append_sheet_rows(), append_to_google_doc(), create_google_doc(), create_google_sheet(), _doc_url(), file_id(), Google Docs and Sheets: create a document or spreadsheet, append to one, read a…, Accept a bare id or a Docs/Sheets URL. (+15 more)

### Community 7 - "Drive Tools"
Cohesion: 0.16
Nodes (21): Last-sent file kept 30 minutes, _find_folder(), _q(), Read-only Google Drive: find files and read their text. The token only ever…, Create one file in the user's Drive (drive.file: Cue can only ever touch files…, Folder id by name, via the read scope (drive.file alone only sees files Cue…, read_file(), save_last_file() (+13 more)

### Community 8 - "Browser Pool (Playwright)"
Cohesion: 0.13
Nodes (13): Browser, BrowserContext, Claude Agent SDK gotchas, os, Page, playwright_async_api, BrowserPool, BrowserSession (+5 more)

### Community 9 - "Per-user Tool Builders"
Cohesion: 0.15
Nodes (20): New-tool convention, Per-user tool closures, Per-user isolation, build_calendar_tools(), create_calendar_event(), delete_calendar_event(), get_calendar_events(), google_connect_link() (+12 more)

### Community 10 - "Data Agent Records"
Cohesion: 0.19
Nodes (17): datetime, decimal, json, build_data_tools(), describe_business_data(), my_health_log(), my_past_reminders(), my_personas() (+9 more)

### Community 11 - "Booking Tools"
Cohesion: 0.19
Nodes (15): build_browser_tools(), click(), open_page(), read_page(), request_booking_approval(), screenshot(), select_option(), type_text() (+7 more)

### Community 12 - "Agent Prompts"
Cohesion: 0.13
Nodes (4): collections_abc, Drive, Docs and Sheets tools, Google Tasks and Contacts tools, uuid

### Community 13 - "Google Tasks Tools"
Cohesion: 0.24
Nodes (15): add_task(), complete_task(), _due_text(), list_tasks(), _lists(), Google Tasks: the user's own task lists (the ones in Gmail's side panel and the…, _resolve_list(), build_tasks_tools() (+7 more)

### Community 14 - "Safety Gates & Principles"
Cohesion: 0.16
Nodes (7): Operational autonomy and stop conditions, Truth about actions rule, Booking approval gate, Sellify is Cue (n8n migration), Lessons carried over from n8n Cue, BookingGate, Called on every inbound user message. Returns a system line for the agent when…

### Community 15 - "PersonalAssistant (Agent SDK)"
Cohesion: 0.19
Nodes (10): ClaudeAgentOptions, Manager agent and specialist subagents, Metered API key, not a claude.ai login, Why the Claude Agent SDK, PersonalAssistant, images: (media_type, base64) photos the user attached; they go to the model as…, Sync convenience wrapper. Do not call from inside a running event loop., The SDK's streaming-input form of a single user message, which is the only way… (+2 more)

### Community 16 - "Memory Profile Tools"
Cohesion: 0.21
Nodes (10): build_memory_tools(), forget(), recall(), remember(), _forget(), format_profile(), SdkMcpTool, What the assistant remembers about its user: name, age, weight, family,… (+2 more)

### Community 17 - "Media Attachments"
Cohesion: 0.22
Nodes (11): _attach_media(), _looks_like_filename(), _own_media_urls(), _prepare_photo(), A voice note becomes text the agent reads as the user's words., A photo is shown to the model as an image block; the note tells it one is…, Turn attachments into what the agent sees: a system line per file, voice notes…, Screenshots the browser tools produced, so they go out as images. (+3 more)

### Community 18 - "Notes Tools"
Cohesion: 0.25
Nodes (9): _add_note(), build_notes_tools(), add_note(), get_notes(), search_notes(), _get_notes(), SdkMcpTool, Build fresh notes tools bound to a specific user's phone number. Each incoming… (+1 more)

### Community 19 - "Google OAuth Routes"
Cohesion: 0.24
Nodes (10): health(), oauth_google_callback(), oauth_google_start(), oauth_google_status(), _oauth_redirect_uri(), Connect a WhatsApp user's own Google account (Calendar + Gmail). Needs the…, Report whether a usable Google token exists, so "is Calendar connected?" can be…, get (+2 more)

### Community 20 - "Webhooks & Testing"
Cohesion: 0.27
Nodes (9): Runs the agent as `phone` and returns the reply without WhatsApp. Requires the…, test_webhook(), _twilio_signature_valid(), whatsapp_webhook(), Testing approach, WhatsApp request flow, Webhook security, post (+1 more)

### Community 21 - "App Lifespan & Scheduler"
Cohesion: 0.28
Nodes (8): lifespan(), Poll for due reminders once a minute and deliver each in its own task, so one…, _reminder_loop(), contextlib, FastAPI, fastapi_responses, twilio_request_validator, uvicorn

### Community 22 - "Typing Indicator"
Cohesion: 0.29
Nodes (5): _keep_typing(), Keep the "typing…" indicator on the user's screen until the reply is sent (the…, WhatsApp typing indicator, Show the typing indicator (and read receipt) on the user's chat for the message…, WhatsAppChannel

### Community 23 - "Media Store"
Cohesion: 0.33
Nodes (6): media(), secrets, get(), put(), Short-lived in-memory store for images the app itself generates (booking…, _sweep()

### Community 24 - "Contacts Tools"
Cohesion: 0.33
Nodes (6): claude_agent_sdk, build_contacts_tools(), search_contacts(), SdkMcpTool, Google Contacts (read-only), built per user (closure over the phone)., _text()

### Community 25 - "Approvals & Recent Files"
Cohesion: 0.29
Nodes (5): re, Confirm-before-act gate for bookings. The final step of a booking (the "Confirm…, The last file each user sent over WhatsApp, kept in memory for a short while so…, threading, time

## Knowledge Gaps
- **3 isolated node(s):** `Security rules (non-negotiable)`, `Git and deploy workflow`, `Metered API key, not a claude.ai login`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 149 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_browser_tools()` connect `Booking Tools` to `Per-user Tool Builders`, `Agent Prompts`, `PersonalAssistant (Agent SDK)`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `build_data_tools()` connect `Data Agent Records` to `Per-user Tool Builders`, `Agent Prompts`, `PersonalAssistant (Agent SDK)`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Why does `build_reminder_tools()` connect `Reminders` to `App Core & Project Knowledge`, `Per-user Tool Builders`, `Agent Prompts`, `PersonalAssistant (Agent SDK)`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `build_browser_tools()` (e.g. with `click()` and `open_page()`) actually correct?**
  _`build_browser_tools()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Security rules (non-negotiable)`, `Git and deploy workflow`, `Metered API key, not a claude.ai login` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `App Core & Project Knowledge` be split into smaller, more focused modules?**
  _Cohesion score 0.051106639839034206 - nodes in this community are weakly interconnected._
- **Should `Google OAuth & Calendar` be split into smaller, more focused modules?**
  _Cohesion score 0.07878787878787878 - nodes in this community are weakly interconnected._