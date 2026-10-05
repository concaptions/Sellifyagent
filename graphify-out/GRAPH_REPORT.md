# Graph Report - Sellifyagent  (2026-10-05)

## Corpus Check
- 80 files · ~43,898 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 5, .example 1)

## Summary
- 604 nodes · 1283 edges · 38 communities (30 shown, 8 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 95 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c0f09ac9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- database.py
- google_auth.py
- documents.py
- email/__init__.py
- media_ai.py
- manage_reminders.py
- Per-user tool closures
- files.py
- browser.py
- build_calendar_tools
- records.py
- build_browser_tools
- assistant.py
- google_tasks.py
- BookingGate
- ._build_options
- profile.py
- What You Must Do When Invoked
- build_notes_tools
- graphify reference: extra exports and benchmark
- app.py
- BrowserPool
- graphify reference: query, path, explain
- media_store.py
- asyncio
- booking.py
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- Sellify is Cue (n8n migration)
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- CLAUDE.md
- extraction-spec.md

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
- `Reminder scheduler and follow-ups` --references--> `_prepare_message()`  [EXTRACTED]
  MEMORY.md → app.py
- `WhatsApp typing indicator` --references--> `_keep_typing()`  [EXTRACTED]
  MEMORY.md → app.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Per-user Google access flow** — memory_per_user_google, memory_scope_per_tool, memory_signed_connect_link, app_oauth_google_start, app_oauth_google_callback, src_utils_google_auth_get_google_credentials, src_utils_google_auth_scoped_service [INFERRED 0.85]
- **Reminder delivery flow** — memory_reminders_scheduler, memory_twilio_24h_window, app_reminder_loop, app_deliver_reminder, src_database_claim_due_reminders, src_database_finish_reminder [INFERRED 0.85]
- **Safety gates enforced in code** — memory_booking_gate, src_utils_approvals_bookinggate, app_prepare_message, claude_truth_about_actions, claude_operational_rules, claude_security_rules [INFERRED 0.85]

## Communities (38 total, 8 thin omitted)

### Community 0 - "database.py"
Cohesion: 0.06
Nodes (57): Git and deploy workflow, Security rules (non-negotiable), Owner numbers and business data, Per-user SDK sessions, Personal memory profile, Railway deployment, Reminder scheduler and follow-ups, Cue's Supabase shared database (+49 more)

### Community 1 - "google_auth.py"
Cohesion: 0.06
Nodes (69): oauth_google_callback(), oauth_google_start(), Connect a WhatsApp user's own Google account (Calendar + Gmail). Needs the…, Credentials, google_auth_oauthlib_flow, google_auth_transport_requests, google_oauth2_credentials, googleapiclient_discovery (+61 more)

### Community 2 - "documents.py"
Cohesion: 0.07
Nodes (50): _ingest_attachment(), Download and store one attachment; return the system line the agent sees,…, dataclasses, Cue's earlier documents (pa_knowledge_chunks), Document upload pipeline (text only), Twilio media 404 retry, list_canon_sources(), Store a document and its chunks in one transaction. A re-upload under the same… (+42 more)

### Community 3 - "email/__init__.py"
Cohesion: 0.12
Nodes (26): base64, email_mime_text, html, Full email and attachment reading, build_email_tools(), modify_email(), read_email(), read_email_attachment() (+18 more)

### Community 4 - "media_ai.py"
Cohesion: 0.08
Nodes (30): dotenv, httpx, io, logging, WhatsApp typing indicator, os, Show the typing indicator (and read receipt) on the user's chat for the message…, WhatsAppChannel (+22 more)

### Community 5 - "manage_reminders.py"
Cohesion: 0.17
Nodes (23): _deliver_reminder(), Run the agent on the due reminder and send its reply to the user. The outcome…, calendar, build_reminder_tools(), cancel_reminder(), create_reminder(), list_reminders(), stop_reminders() (+15 more)

### Community 6 - "Per-user tool closures"
Cohesion: 0.25
Nodes (11): New-tool convention, Per-user tool closures, Per-user isolation, build_workspace_tools(), append_sheet_rows(), append_to_google_doc(), create_google_doc(), create_google_sheet() (+3 more)

### Community 7 - "files.py"
Cohesion: 0.11
Nodes (26): Drive, Docs and Sheets tools, Last-sent file kept 30 minutes, _find_folder(), _q(), Read-only Google Drive: find files and read their text. The token only ever…, Create one file in the user's Drive (drive.file: Cue can only ever touch files…, Folder id by name, via the read scope (drive.file alone only sees files Cue…, read_file() (+18 more)

### Community 8 - "browser.py"
Cohesion: 0.21
Nodes (9): BrowserContext, Page, playwright_async_api, BrowserSession, element(), locator(), Headless browser sessions for the booking worker (Playwright, async API). One…, Page title, URL, visible text and numbered interactive elements. (+1 more)

### Community 9 - "build_calendar_tools"
Cohesion: 0.39
Nodes (8): build_calendar_tools(), create_calendar_event(), delete_calendar_event(), get_calendar_events(), google_connect_link(), update_calendar_event(), SdkMcpTool, _text()

### Community 10 - "records.py"
Cohesion: 0.19
Nodes (17): datetime, decimal, json, build_data_tools(), describe_business_data(), my_health_log(), my_past_reminders(), my_personas() (+9 more)

### Community 11 - "build_browser_tools"
Cohesion: 0.23
Nodes (13): build_browser_tools(), click(), open_page(), read_page(), request_booking_approval(), screenshot(), select_option(), type_text() (+5 more)

### Community 12 - "assistant.py"
Cohesion: 0.15
Nodes (3): collections_abc, Google Tasks and Contacts tools, uuid

### Community 13 - "google_tasks.py"
Cohesion: 0.24
Nodes (15): add_task(), complete_task(), _due_text(), list_tasks(), _lists(), Google Tasks: the user's own task lists (the ones in Gmail's side panel and the…, _resolve_list(), build_tasks_tools() (+7 more)

### Community 14 - "BookingGate"
Cohesion: 0.24
Nodes (4): Operational autonomy and stop conditions, Booking approval gate, BookingGate, Called on every inbound user message. Returns a system line for the agent when…

### Community 15 - "._build_options"
Cohesion: 0.17
Nodes (11): ClaudeAgentOptions, Manager agent and specialist subagents, Model pinned to claude-sonnet-5, Metered API key, not a claude.ai login, Why the Claude Agent SDK, PersonalAssistant, images: (media_type, base64) photos the user attached; they go to the model as…, Sync convenience wrapper. Do not call from inside a running event loop. (+3 more)

### Community 16 - "profile.py"
Cohesion: 0.22
Nodes (11): build_memory_tools(), forget(), recall(), remember(), _forget(), format_profile(), SdkMcpTool, What the assistant remembers about its user: name, age, weight, family,… (+3 more)

### Community 17 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 18 - "build_notes_tools"
Cohesion: 0.25
Nodes (9): _add_note(), build_notes_tools(), add_note(), get_notes(), search_notes(), _get_notes(), SdkMcpTool, Build fresh notes tools bound to a specific user's phone number. Each incoming… (+1 more)

### Community 19 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 20 - "app.py"
Cohesion: 0.08
Nodes (43): _allowed_sender(), _attach_media(), health(), _keep_typing(), lifespan(), _looks_like_filename(), media(), _notify_private_once() (+35 more)

### Community 21 - "BrowserPool"
Cohesion: 0.36
Nodes (3): Browser, Claude Agent SDK gotchas, BrowserPool

### Community 22 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 23 - "media_store.py"
Cohesion: 0.50
Nodes (4): secrets, put(), Short-lived in-memory store for images the app itself generates (booking…, _sweep()

### Community 24 - "asyncio"
Cohesion: 0.29
Nodes (7): asyncio, claude_agent_sdk, build_contacts_tools(), search_contacts(), SdkMcpTool, Google Contacts (read-only), built per user (closure over the phone)., _text()

### Community 25 - "booking.py"
Cohesion: 0.33
Nodes (4): re, Browser tools for guest bookings: browse public sites, fill forms, and complete…, Confirm-before-act gate for bookings. The final step of a booking (the "Confirm…, urllib_parse

### Community 30 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 31 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 32 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 33 - "Sellify is Cue (n8n migration)"
Cohesion: 0.50
Nodes (3): Truth about actions rule, Sellify is Cue (n8n migration), Lessons carried over from n8n Cue

## Knowledge Gaps
- **45 isolated node(s):** `graphify`, `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)`, `Step 1 - Ensure graphify is installed` (+40 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 201 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_browser_tools()` connect `build_browser_tools` to `booking.py`, `assistant.py`, `Per-user tool closures`, `._build_options`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `build_data_tools()` connect `records.py` to `assistant.py`, `Per-user tool closures`, `._build_options`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `build_reminder_tools()` connect `manage_reminders.py` to `database.py`, `assistant.py`, `Per-user tool closures`, `._build_options`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `build_browser_tools()` (e.g. with `click()` and `open_page()`) actually correct?**
  _`build_browser_tools()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `graphify`, `Usage`, `What graphify is for` to the rest of the system?**
  _45 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `database.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06170598911070781 - nodes in this community are weakly interconnected._
- **Should `google_auth.py` be split into smaller, more focused modules?**
  _Cohesion score 0.061938061938061936 - nodes in this community are weakly interconnected._