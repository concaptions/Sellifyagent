# Graph Report - sellifyagent  (2026-10-28)

## Corpus Check
- 72 files · ~33,850 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 4, .example 1)

## Summary
- 561 nodes · 1344 edges · 30 communities (24 shown, 6 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 95 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4e9daae7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- database.py
- google_auth.py
- documents.py
- re
- media_ai.py
- manage_reminders.py
- admin_panel.py
- files.py
- Per-user Google OAuth
- build_calendar_tools
- records.py
- booking.py
- assistant.py
- scope_not_granted
- BookingGate
- ._build_options
- profile.py
- asyncio
- build_notes_tools
- whatsapp_webhook
- app.py
- _attach_media
- time
- claude_agent_sdk
- Sellify is Cue (n8n migration)
- CLAUDE.md

## God Nodes (most connected - your core abstractions)
1. `get_db()` - 38 edges
2. `not_connected()` - 23 edges
3. `scope_not_granted()` - 23 edges
4. `get_google_credentials()` - 18 edges
5. `build_browser_tools()` - 14 edges
6. `build_data_tools()` - 14 edges
7. `Per-user tool closures` - 14 edges
8. `build_reminder_tools()` - 13 edges
9. `get_gmail_service()` - 12 edges
10. `_scoped_service()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `Voice notes, photos, generated images` --references--> `_user_turn_with_images()`  [EXTRACTED]
  MEMORY.md → src/agents/assistant.py
- `Document upload pipeline (text only)` --references--> `save_document()`  [EXTRACTED]
  MEMORY.md → src/database.py
- `Per-user Google OAuth` --references--> `get_google_tokens()`  [EXTRACTED]
  MEMORY.md → src/database.py
- `Per-user Google OAuth` --references--> `set_google_tokens()`  [EXTRACTED]
  MEMORY.md → src/database.py
- `Cue's earlier documents (pa_knowledge_chunks)` --references--> `search_canon()`  [EXTRACTED]
  MEMORY.md → src/database.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Per-user Google access flow** — memory_per_user_google, memory_scope_per_tool, memory_signed_connect_link, app_oauth_google_start, app_oauth_google_callback, src_utils_google_auth_get_google_credentials, src_utils_google_auth_scoped_service [INFERRED 0.85]
- **Reminder delivery flow** — memory_reminders_scheduler, memory_twilio_24h_window, app_reminder_loop, app_deliver_reminder, src_database_claim_due_reminders, src_database_finish_reminder [INFERRED 0.85]
- **Safety gates enforced in code** — memory_booking_gate, src_utils_approvals_bookinggate, app_prepare_message, claude_truth_about_actions, claude_operational_rules, claude_security_rules [INFERRED 0.85]

## Communities (30 total, 6 thin omitted)

### Community 0 - "database.py"
Cohesion: 0.06
Nodes (46): Git and deploy workflow, Security rules (non-negotiable), Owner numbers and business data, Per-user SDK sessions, Personal memory profile, Railway deployment, Cue's Supabase shared database, cancel_reminder() (+38 more)

### Community 1 - "google_auth.py"
Cohesion: 0.11
Nodes (24): Scope check per Google tool, create_calendar_event(), describe_event(), delete_calendar_event(), get_calendar_events(), update_calendar_event(), _digits(), _format() (+16 more)

### Community 2 - "documents.py"
Cohesion: 0.09
Nodes (23): _ingest_attachment(), Cue's earlier documents (pa_knowledge_chunks), Document upload pipeline (text only), Twilio media 404 retry, list_canon_sources(), build_document_tools(), delete_document(), list_documents() (+15 more)

### Community 3 - "re"
Cohesion: 0.10
Nodes (25): Full email and attachment reading, build_email_tools(), modify_email(), read_email(), read_email_attachment(), read_emails(), save_email_attachment_to_drive(), send_email() (+17 more)

### Community 4 - "media_ai.py"
Cohesion: 0.08
Nodes (15): Model pinned to claude-sonnet-5, WhatsApp typing indicator, WhatsAppChannel, _chart(), _generate(), generate_image(), render_chart(), _text() (+7 more)

### Community 5 - "manage_reminders.py"
Cohesion: 0.19
Nodes (14): build_reminder_tools(), cancel_reminder(), create_reminder(), list_reminders(), stop_reminders(), _cancel(), _create(), describe_recurrence() (+6 more)

### Community 6 - "admin_panel.py"
Cohesion: 0.15
Nodes (8): admin_page(), admin_test_user(), _audience_url(), _client_ip(), _recent(), _render(), require_admin(), _send_notification()

### Community 7 - "files.py"
Cohesion: 0.13
Nodes (17): Last-sent file kept 30 minutes, _find_folder(), _q(), read_file(), save_last_file(), search_files(), upload_to_drive(), build_drive_tools() (+9 more)

### Community 8 - "Per-user Google OAuth"
Cohesion: 0.18
Nodes (10): oauth_google_start(), Per-user Google OAuth, Signed personal connect link, _client_config(), exchange_code_for_token(), get_authorization_url(), make_link_token(), _pop_pkce() (+2 more)

### Community 9 - "build_calendar_tools"
Cohesion: 0.39
Nodes (7): build_calendar_tools(), create_calendar_event(), delete_calendar_event(), get_calendar_events(), google_connect_link(), update_calendar_event(), _text()

### Community 10 - "records.py"
Cohesion: 0.20
Nodes (11): build_data_tools(), describe_business_data(), my_health_log(), my_past_reminders(), my_personas(), query_business_data(), read_persona(), search_past_chats() (+3 more)

### Community 11 - "booking.py"
Cohesion: 0.09
Nodes (17): Claude Agent SDK gotchas, build_browser_tools(), click(), open_page(), read_page(), request_booking_approval(), screenshot(), select_option() (+9 more)

### Community 13 - "scope_not_granted"
Cohesion: 0.10
Nodes (30): add_task(), complete_task(), _due_text(), list_tasks(), _lists(), _resolve_list(), build_tasks_tools(), add_task() (+22 more)

### Community 14 - "BookingGate"
Cohesion: 0.20
Nodes (3): media(), Booking approval gate, BookingGate

### Community 15 - "._build_options"
Cohesion: 0.19
Nodes (5): Manager agent and specialist subagents, Metered API key, not a claude.ai login, Why the Claude Agent SDK, PersonalAssistant, _user_turn_with_images()

### Community 16 - "profile.py"
Cohesion: 0.22
Nodes (8): build_memory_tools(), forget(), recall(), remember(), _forget(), format_profile(), _recall(), _remember()

### Community 17 - "asyncio"
Cohesion: 0.20
Nodes (9): _deliver_reminder(), _keep_typing(), _prepare_message(), _process_message(), _reminder_loop(), Reminder scheduler and follow-ups, Plan for ~20 testers, Transcript length drives cost (+1 more)

### Community 18 - "build_notes_tools"
Cohesion: 0.25
Nodes (7): _add_note(), build_notes_tools(), add_note(), get_notes(), search_notes(), _get_notes(), _search_notes()

### Community 19 - "whatsapp_webhook"
Cohesion: 0.24
Nodes (8): _allowed_sender(), _notify_private_once(), test_webhook(), _twilio_signature_valid(), whatsapp_webhook(), Testing approach, WhatsApp request flow, Webhook security

### Community 20 - "app.py"
Cohesion: 0.26
Nodes (5): health(), lifespan(), oauth_google_callback(), oauth_google_status(), _oauth_redirect_uri()

### Community 21 - "_attach_media"
Cohesion: 0.24
Nodes (6): _attach_media(), _looks_like_filename(), _own_media_urls(), _prepare_photo(), _transcribe_attachment(), Voice notes, photos, generated images

### Community 23 - "time"
Cohesion: 0.52
Nodes (3): get(), put(), _sweep()

### Community 24 - "claude_agent_sdk"
Cohesion: 0.22
Nodes (6): New-tool convention, Per-user tool closures, Per-user isolation, build_contacts_tools(), search_contacts(), _text()

### Community 33 - "Sellify is Cue (n8n migration)"
Cohesion: 0.40
Nodes (4): Operational autonomy and stop conditions, Truth about actions rule, Sellify is Cue (n8n migration), Lessons carried over from n8n Cue

## Knowledge Gaps
- **3 isolated node(s):** `Git and deploy workflow`, `Security rules (non-negotiable)`, `Metered API key, not a claude.ai login`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 152 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_browser_tools()` connect `booking.py` to `claude_agent_sdk`, `assistant.py`, `._build_options`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **What connects `Git and deploy workflow`, `Security rules (non-negotiable)`, `Metered API key, not a claude.ai login` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `database.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05687645687645688 - nodes in this community are weakly interconnected._
- **Why does `build_data_tools()` connect `records.py` to `claude_agent_sdk`, `assistant.py`, `._build_options`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Should `google_auth.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11295681063122924 - nodes in this community are weakly interconnected._
- **Why does `build_reminder_tools()` connect `manage_reminders.py` to `claude_agent_sdk`, `asyncio`, `assistant.py`, `._build_options`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Should `documents.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09176788124156546 - nodes in this community are weakly interconnected._