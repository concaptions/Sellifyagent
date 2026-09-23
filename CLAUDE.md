# CLAUDE.md — Sellify Agent

Project state, infrastructure IDs, and known gotchas live in MEMORY.md (imported below).
Read it before exploring the codebase; it usually answers "where is X" without opening files.

@MEMORY.md

## Working efficiently (token budget)
- Start from MEMORY.md's file map. Open only the files the task touches; use `grep -n`
  and `sed -n 'A,Bp'` for targeted reads instead of reading whole files.
- Don't re-verify facts MEMORY.md already records unless the task depends on them changing.
- Prefer one validated change + one test over several speculative pushes (each push
  triggers a Railway redeploy).
- Don't poll in tight loops. When waiting on a Railway deploy (~1–2 min), use one
  background sleep, then check once.

## Security rules (non-negotiable)
- Never read, print, or commit `.env`, `credentials.json`, or `token.json`
  (`.claude/settings.json` denies reads of these).
- Never put secrets, API keys, passwords, OAuth client secrets, or end-user phone numbers
  in code, commits, PR text, MEMORY.md, or chat replies. Real values live in Railway env vars.
- Before every commit, scan the diff:
  `git diff --cached | grep -iE "GOCSPX|sk-ant|AC[0-9a-f]{32}|password=" || echo clean`
- The Postgres connection bypasses RLS: every query must be scoped by `user_id`.

## Git / deploy workflow
- Develop on `claude/jolly-ramanujan-l0q173` (Railway production deploys from it on push).
  PR #1 is the open draft PR for this branch.
- Commit messages: explain *why*, in the repo's existing style.
- After pushing, confirm the Railway deploy reached SUCCESS before testing live.

## Code conventions
- New tool: `@tool(name, description, JSON_SCHEMA)` with an explicit JSON Schema (`required`
  listed), blocking I/O inside `asyncio.to_thread`, return `{"content":[{"type":"text","text":...}]}`.
  Add its name to the relevant `*_TOOL_NAMES` list so it reaches `ALL_TOOL_NAMES` in
  `src/agents/assistant.py` (otherwise the subagent can't call it).
- Per-user data: bind `user_phone` via a closure factory, like `build_notes_tools(user_phone)`.
- Fail closed with a plain message ("X is not connected…"), never fabricate a result.
  Prompts keep the "truth about actions" rule: only claim done if a tool returned success.
- Prompts are short and principle-based; don't add long lists of examples.
- Match surrounding comment density: comments explain *why* (a past bug, a constraint).

## Testing
- Syntax: `python3 -m compileall -q app.py src`
- Route tests locally: `fastapi.testclient.TestClient(app)`, mocking Google/Twilio.
  DB init failing locally is expected (no Postgres).
- Live agent test: POST `/webhook/test` with form `phone`, `message`, which returns the reply
  synchronously. This sandbox can't reach Railway directly; see MEMORY.md gotcha #10.
- Print the response body in live-test scripts (not just the status code).

## Operational rules — ask the user first
- Changing Twilio routing (webhooks, Event Streams) — it affects the live Cue assistant.
- Deleting Railway services, volumes, or env vars; changing the Google OAuth client.
- Anything that sends real email or WhatsApp messages to people other than the user.
- Building browser automation that logs into sites or takes financial actions.

## Keeping memory current
Update MEMORY.md (status, backlog, decision log) in the same commit as any change that
alters state. Edit in place; keep it short.
