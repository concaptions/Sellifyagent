"""Read-only Google Drive: find files and read their text. The token only
ever carries drive.readonly, so nothing here can change, share or delete a
file; file bytes are read for the duration of one call and not stored."""
from src.utils.documents import DocumentError, MAX_BYTES, SUPPORTED_TYPES, extract_text
from src.utils.google_auth import drive_not_connected, get_drive_service

MAX_TEXT_CHARS = 12_000
_FIELDS = "files(id,name,mimeType,modifiedTime,size,webViewLink,owners(emailAddress))"

# Google's own formats have no bytes to download; they are exported.
_EXPORTS = {
    "application/vnd.google-apps.document": ("text/plain", "text/plain"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", "text/csv"),
    "application/vnd.google-apps.presentation": ("text/plain", "text/plain"),
}


def _q(term: str) -> str:
    return term.replace("\\", "\\\\").replace("'", "\\'")


def search_files(phone: str, query: str, max_results: int) -> str:
    service = get_drive_service(phone)
    if not service:
        return drive_not_connected(phone)
    term = _q(query.strip())
    if not term:
        return "Give me a word or phrase to search for."
    q = f"(name contains '{term}' or fullText contains '{term}') and trashed = false"
    try:
        result = service.files().list(
            q=q, pageSize=max(1, min(int(max_results), 20)), fields=_FIELDS,
            corpora="allDrives", includeItemsFromAllDrives=True, supportsAllDrives=True,
        ).execute()
    except Exception as e:
        return f"Error searching Drive: {e}"
    files = result.get("files", [])
    if not files:
        return f"No Drive files match {query!r} (searched names and contents, shared files included)."
    lines = []
    for f in files:
        size = f"{int(f['size']):,} bytes" if f.get("size") else "Google format"
        lines.append(
            f"- {f['name']} ({f.get('mimeType', '?')}, {size}, modified {f.get('modifiedTime', '?')[:10]})\n"
            f"  link: {f.get('webViewLink', '')}\n  [id: {f['id']}]"
        )
    return f"Found {len(files)} file(s):\n\n" + "\n\n".join(lines)


def read_file(phone: str, file_id: str) -> str:
    service = get_drive_service(phone)
    if not service:
        return drive_not_connected(phone)
    try:
        meta = service.files().get(fileId=file_id, fields="id,name,mimeType,size", supportsAllDrives=True).execute()
        mime = (meta.get("mimeType") or "").split(";")[0].strip().lower()
        name = meta.get("name", file_id)
        if mime in _EXPORTS:
            export_mime, text_mime = _EXPORTS[mime]
            data = service.files().export(fileId=file_id, mimeType=export_mime).execute()
            text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)
        elif mime in SUPPORTED_TYPES:
            size = int(meta.get("size") or 0)
            if size > MAX_BYTES:
                return f"{name} is too large to read ({size // 1_000_000} MB; the limit is 10 MB)."
            data = service.files().get_media(fileId=file_id, supportsAllDrives=True).execute()
            text = extract_text(data, mime)
        elif mime.startswith("application/vnd.google-apps."):
            return f"{name} is a {mime.rsplit('.', 1)[-1]}; I can read Google Docs, Sheets and Slides, plus PDF, Word and text files."
        else:
            return f"{name} is {mime or 'an unknown type'}; I can read Google Docs, Sheets and Slides, plus PDF, Word and text files."
    except DocumentError as e:
        return str(e)
    except Exception as e:
        return f"Error reading Drive file: {e}"

    truncated = len(text) > MAX_TEXT_CHARS
    text = text[:MAX_TEXT_CHARS].strip()
    out = f"File: {name} ({mime})\n\n{text or '(no readable text)'}"
    if truncated:
        out += f"\n\n[Text truncated at {MAX_TEXT_CHARS:,} characters]"
    return out


SEARCH_FILES_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "A word or phrase; matched against file names and file contents."},
        "max_results": {"type": "integer", "description": "Maximum files to return (1-20). Default 10."},
    },
    "required": ["query"],
}

READ_FILE_SCHEMA = {
    "type": "object",
    "properties": {
        "file_id": {"type": "string", "description": "The [id: …] value from search_drive_files."},
    },
    "required": ["file_id"],
}
