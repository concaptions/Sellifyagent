# Graph Report - sellifyagent  (2026-10-29)

## Corpus Check
- 72 files · ~34,975 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 4, .example 1)

## Summary
- 578 nodes · 1398 edges · 25 communities (19 shown, 6 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 96 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `dcd14f1c`
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
- claude_agent_sdk
- build_calendar_tools
- records.py
- booking.py
- assistant.py
- Per-user tool closures
- ._build_options
- profile.py
- app.py
- build_notes_tools
- build_email_tools
- build_workspace_tools
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
- `Per-user Google OAuth` --references--> `get_google_tokens()`  [EXTRACTED]
  MEMORY.md → src/database.py
- `Per-user Google OAuth` --references--> `set_google_tokens()`  [EXTRACTED]
  MEMORY.md → src/database.py
- `Cue's earlier documents (pa_knowledge_chunks)` --references--> `search_canon()`  [EXTRACTED]
  MEMORY.md → src/database.py
- `Owner numbers and business data` --references--> `run_business_query()`  [EXTRACTED]
  MEMORY.md → src/database.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Per-user Google access flow** — memory_per_user_google, memory_scope_per_tool, memory_signed_connect_link, app_oauth_google_start, app_oauth_google_callback, src_utils_google_auth_get_google_credentials, src_utils_google_auth_scoped_service [INFERRED 0.85]
- **Reminder delivery flow** — memory_reminders_scheduler, memory_twilio_24h_window, app_reminder_loop, app_deliver_reminder, src_database_claim_due_reminders, src_database_finish_reminder [INFERRED 0.85]
- **Safety gates enforced in code** — memory_booking_gate, src_utils_approvals_bookinggate, app_prepare_message, claude_truth_about_actions, claude_operational_rules, claude_security_rules [INFERRED 0.85]

## Communities (25 total, 6 thin omitted)

### Community 0 - "database.py"
Cohesion: 0.06
Nodes (43): Git and deploy workflow, Security rules (non-negotiable), Owner numbers and business data, Per-user SDK sessions, Personal memory profile, Railway deployment, Cue's Supabase shared database, cancel_reminder() (+35 more)

### Community 1 - "google_auth.py"
Cohesion: 0.07
Nodes (40): Scope check per Google tool, _digits(), _format(), _matches(), _pages(), search_contacts(), _label_id(), modify_email() (+32 more)

### Community 2 - "documents.py"
Cohesion: 0.08
Nodes (24): _ingest_attachment(), Cue's earlier documents (pa_knowledge_chunks), Document upload pipeline (text only), Twilio media 404 retry, list_canon_sources(), save_document(), build_document_tools(), delete_document() (+16 more)

### Community 3 - "re"
Cohesion: 0.12
Nodes (21): Full email and attachment reading, create_calendar_event(), describe_event(), delete_calendar_event(), get_calendar_events(), update_calendar_event(), _attachments(), download_attachment() (+13 more)

### Community 4 - "media_ai.py"
Cohesion: 0.08
Nodes (15): Model pinned to claude-sonnet-5, WhatsApp typing indicator, WhatsAppChannel, _chart(), _generate(), generate_image(), render_chart(), _text() (+7 more)

### Community 5 - "manage_reminders.py"
Cohesion: 0.19
Nodes (14): build_reminder_tools(), cancel_reminder(), create_reminder(), list_reminders(), stop_reminders(), _cancel(), _create(), describe_recurrence() (+6 more)

### Community 6 - "admin_panel.py"
Cohesion: 0.13
Nodes (23): admin_login(), admin_login_page(), admin_logout(), admin_page(), admin_test_user(), _audience_url(), _build_message(), _clean() (+15 more)

### Community 7 - "files.py"
Cohesion: 0.12
Nodes (18): Drive, Docs and Sheets tools, Last-sent file kept 30 minutes, _find_folder(), _q(), read_file(), save_last_file(), search_files(), upload_to_drive() (+10 more)

### Community 8 - "claude_agent_sdk"
Cohesion: 0.33
Nodes (3): build_contacts_tools(), search_contacts(), _text()

### Community 9 - "build_calendar_tools"
Cohesion: 0.39
Nodes (7): build_calendar_tools(), create_calendar_event(), delete_calendar_event(), get_calendar_events(), google_connect_link(), update_calendar_event(), _text()

### Community 10 - "records.py"
Cohesion: 0.20
Nodes (11): build_data_tools(), describe_business_data(), my_health_log(), my_past_reminders(), my_personas(), query_business_data(), read_persona(), search_past_chats() (+3 more)

### Community 11 - "booking.py"
Cohesion: 0.06
Nodes (23): Operational autonomy and stop conditions, Truth about actions rule, Booking approval gate, Claude Agent SDK gotchas, Sellify is Cue (n8n migration), Lessons carried over from n8n Cue, build_browser_tools(), click() (+15 more)

### Community 13 - "Per-user tool closures"
Cohesion: 0.28
Nodes (8): New-tool convention, Per-user tool closures, Per-user isolation, build_tasks_tools(), add_task(), complete_task(), list_tasks(), _text()

### Community 15 - "._build_options"
Cohesion: 0.19
Nodes (5): Manager agent and specialist subagents, Metered API key, not a claude.ai login, Why the Claude Agent SDK, PersonalAssistant, _user_turn_with_images()

### Community 16 - "profile.py"
Cohesion: 0.22
Nodes (8): build_memory_tools(), forget(), recall(), remember(), _forget(), format_profile(), _recall(), _remember()

### Community 17 - "app.py"
Cohesion: 0.06
Nodes (42): _allowed_sender(), _attach_media(), _deliver_reminder(), health(), _keep_typing(), lifespan(), _looks_like_filename(), media() (+34 more)

### Community 18 - "build_notes_tools"
Cohesion: 0.25
Nodes (7): _add_note(), build_notes_tools(), add_note(), get_notes(), search_notes(), _get_notes(), _search_notes()

### Community 19 - "build_email_tools"
Cohesion: 0.36
Nodes (8): build_email_tools(), modify_email(), read_email(), read_email_attachment(), read_emails(), save_email_attachment_to_drive(), send_email(), _text()

### Community 21 - "build_workspace_tools"
Cohesion: 0.39
Nodes (7): build_workspace_tools(), append_sheet_rows(), append_to_google_doc(), create_google_doc(), create_google_sheet(), read_google_sheet(), _text()

## Knowledge Gaps
- **3 isolated node(s):** `Security rules (non-negotiable)`, `Metered API key, not a claude.ai login`, `Git and deploy workflow`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 150 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_browser_tools()` connect `booking.py` to `assistant.py`, `Per-user tool closures`, `._build_options`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **What connects `Security rules (non-negotiable)`, `Metered API key, not a claude.ai login`, `Git and deploy workflow` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `database.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06120218579234973 - nodes in this community are weakly interconnected._
- **Why does `build_data_tools()` connect `records.py` to `assistant.py`, `Per-user tool closures`, `._build_options`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Should `google_auth.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07179487179487179 - nodes in this community are weakly interconnected._
- **Why does `build_reminder_tools()` connect `manage_reminders.py` to `app.py`, `assistant.py`, `Per-user tool closures`, `._build_options`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Should `documents.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08416389811738649 - nodes in this community are weakly interconnected._