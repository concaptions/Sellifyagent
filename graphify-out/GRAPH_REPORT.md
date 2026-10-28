# Graph Report - sellifyagent  (2026-10-28)

## Corpus Check
- 72 files · ~34,160 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 4, .example 1)

## Summary
- 566 nodes · 1355 edges · 28 communities (21 shown, 7 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 96 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `08476948`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- database.py
- google_auth.py
- manage_documents.py
- re
- media_ai.py
- manage_reminders.py
- admin_panel.py
- files.py
- json
- build_calendar_tools
- records.py
- booking.py
- assistant.py
- scope_not_granted
- search_canon
- ._build_options
- profile.py
- app.py
- build_notes_tools
- build_email_tools
- init_database
- build_workspace_tools
- finish_reminder
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
- `Cue's Supabase shared database` --references--> `get_db()`  [EXTRACTED]
  MEMORY.md → src/database.py
- `Document upload pipeline (text only)` --references--> `save_document()`  [EXTRACTED]
  MEMORY.md → src/database.py
- `Per-user Google OAuth` --references--> `get_google_tokens()`  [EXTRACTED]
  MEMORY.md → src/database.py
- `Per-user Google OAuth` --references--> `set_google_tokens()`  [EXTRACTED]
  MEMORY.md → src/database.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Per-user Google access flow** — memory_per_user_google, memory_scope_per_tool, memory_signed_connect_link, app_oauth_google_start, app_oauth_google_callback, src_utils_google_auth_get_google_credentials, src_utils_google_auth_scoped_service [INFERRED 0.85]
- **Reminder delivery flow** — memory_reminders_scheduler, memory_twilio_24h_window, app_reminder_loop, app_deliver_reminder, src_database_claim_due_reminders, src_database_finish_reminder [INFERRED 0.85]
- **Safety gates enforced in code** — memory_booking_gate, src_utils_approvals_bookinggate, app_prepare_message, claude_truth_about_actions, claude_operational_rules, claude_security_rules [INFERRED 0.85]

## Communities (28 total, 7 thin omitted)

### Community 0 - "database.py"
Cohesion: 0.12
Nodes (22): Security rules (non-negotiable), Owner numbers and business data, cancel_reminder(), claim_due_reminders(), describe_business_tables(), find_document_by_hash(), get_chat_history(), get_cue_persona() (+14 more)

### Community 1 - "google_auth.py"
Cohesion: 0.08
Nodes (30): oauth_google_start(), Per-user Google OAuth, Scope check per Google tool, Signed personal connect link, _digits(), _format(), _matches(), _pages() (+22 more)

### Community 2 - "manage_documents.py"
Cohesion: 0.17
Nodes (11): delete_document(), list_documents(), build_document_tools(), delete_document(), list_documents(), search_documents(), _canon_label(), _delete_document() (+3 more)

### Community 3 - "re"
Cohesion: 0.11
Nodes (24): Full email and attachment reading, create_calendar_event(), describe_event(), delete_calendar_event(), get_calendar_events(), update_calendar_event(), _label_id(), modify_email() (+16 more)

### Community 4 - "media_ai.py"
Cohesion: 0.14
Nodes (11): _chart(), _generate(), generate_image(), render_chart(), _text(), generate_image(), MediaError, prepare_image() (+3 more)

### Community 5 - "manage_reminders.py"
Cohesion: 0.19
Nodes (14): build_reminder_tools(), cancel_reminder(), create_reminder(), list_reminders(), stop_reminders(), _cancel(), _create(), describe_recurrence() (+6 more)

### Community 6 - "admin_panel.py"
Cohesion: 0.12
Nodes (11): admin_page(), admin_test_user(), _audience_url(), _build_message(), _client_ip(), _recent(), _render(), require_admin() (+3 more)

### Community 7 - "files.py"
Cohesion: 0.08
Nodes (29): _ingest_attachment(), Document upload pipeline (text only), Last-sent file kept 30 minutes, Twilio media 404 retry, _find_folder(), _q(), read_file(), save_last_file() (+21 more)

### Community 8 - "json"
Cohesion: 0.17
Nodes (8): Per-user SDK sessions, Personal memory profile, forget_fact(), get_profile(), get_session_id(), remember_facts(), set_google_tokens(), set_session_id()

### Community 9 - "build_calendar_tools"
Cohesion: 0.25
Nodes (10): New-tool convention, Per-user tool closures, Per-user isolation, build_calendar_tools(), create_calendar_event(), delete_calendar_event(), get_calendar_events(), google_connect_link() (+2 more)

### Community 10 - "records.py"
Cohesion: 0.14
Nodes (14): build_contacts_tools(), search_contacts(), _text(), build_data_tools(), describe_business_data(), my_health_log(), my_past_reminders(), my_personas() (+6 more)

### Community 11 - "booking.py"
Cohesion: 0.06
Nodes (23): Operational autonomy and stop conditions, Truth about actions rule, Booking approval gate, Claude Agent SDK gotchas, Sellify is Cue (n8n migration), Lessons carried over from n8n Cue, build_browser_tools(), click() (+15 more)

### Community 13 - "scope_not_granted"
Cohesion: 0.13
Nodes (23): add_task(), complete_task(), _due_text(), list_tasks(), _lists(), _resolve_list(), build_tasks_tools(), add_task() (+15 more)

### Community 14 - "search_canon"
Cohesion: 0.22
Nodes (6): Cue's earlier documents (pa_knowledge_chunks), list_canon_sources(), save_document(), search_canon(), search_document_chunks(), _vector_literal()

### Community 15 - "._build_options"
Cohesion: 0.19
Nodes (5): Manager agent and specialist subagents, Metered API key, not a claude.ai login, Why the Claude Agent SDK, PersonalAssistant, _user_turn_with_images()

### Community 16 - "profile.py"
Cohesion: 0.22
Nodes (8): build_memory_tools(), forget(), recall(), remember(), _forget(), format_profile(), _recall(), _remember()

### Community 17 - "app.py"
Cohesion: 0.06
Nodes (35): _allowed_sender(), _attach_media(), _deliver_reminder(), health(), _keep_typing(), lifespan(), _looks_like_filename(), media() (+27 more)

### Community 18 - "build_notes_tools"
Cohesion: 0.23
Nodes (7): _add_note(), build_notes_tools(), add_note(), get_notes(), search_notes(), _get_notes(), _search_notes()

### Community 19 - "build_email_tools"
Cohesion: 0.36
Nodes (8): build_email_tools(), modify_email(), read_email(), read_email_attachment(), read_emails(), save_email_attachment_to_drive(), send_email(), _text()

### Community 20 - "init_database"
Cohesion: 0.32
Nodes (6): Git and deploy workflow, Railway deployment, Cue's Supabase shared database, init_database(), init_document_tables(), _lock_tables()

### Community 21 - "build_workspace_tools"
Cohesion: 0.39
Nodes (7): build_workspace_tools(), append_sheet_rows(), append_to_google_doc(), create_google_doc(), create_google_sheet(), read_google_sheet(), _text()

## Knowledge Gaps
- **3 isolated node(s):** `Git and deploy workflow`, `Security rules (non-negotiable)`, `Metered API key, not a claude.ai login`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 153 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_browser_tools()` connect `booking.py` to `build_calendar_tools`, `assistant.py`, `._build_options`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **What connects `Git and deploy workflow`, `Security rules (non-negotiable)`, `Metered API key, not a claude.ai login` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `database.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11822660098522167 - nodes in this community are weakly interconnected._
- **Why does `build_data_tools()` connect `records.py` to `build_calendar_tools`, `assistant.py`, `._build_options`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Should `google_auth.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08408163265306122 - nodes in this community are weakly interconnected._
- **Why does `build_reminder_tools()` connect `manage_reminders.py` to `build_calendar_tools`, `assistant.py`, `app.py`, `._build_options`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Should `re` be split into smaller, more focused modules?**
  _Cohesion score 0.10815602836879433 - nodes in this community are weakly interconnected._