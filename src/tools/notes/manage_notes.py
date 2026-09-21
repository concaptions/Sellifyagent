from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src import database as db


class AddNoteInput(BaseModel):
    title: str = Field(description="Note title. String.")
    content: str = Field(description="Note content. String.")
    tags: Optional[str] = Field(
        default=None,
        description="Comma-separated tags for the note. String, e.g. 'work,ideas'.",
    )


class GetNotesInput(BaseModel):
    limit: int = Field(default=10, description="Maximum number of notes to return. Integer.")


class SearchNotesInput(BaseModel):
    query: str = Field(description="Search query to find notes by title or content. String.")


@tool(args_schema=AddNoteInput)
def add_note(title: str, content: str, tags: str | None = None, **kwargs) -> str:
    """Save a new note for the user. Call the moment you have the title and content."""
    user_id = kwargs.get("user_phone", "default")
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    try:
        note_id = db.save_note(user_id, title, content, tag_list)
        return f"Note saved: '{title}' [id: {note_id}]"
    except Exception as e:
        return f"Error saving note: {e}"


@tool(args_schema=GetNotesInput)
def get_notes(limit: int = 10, **kwargs) -> str:
    """List the user's recent notes."""
    user_id = kwargs.get("user_phone", "default")

    try:
        notes = db.get_notes(user_id, limit)
        if not notes:
            return "No notes found."

        lines = []
        for n in notes:
            tags_str = f" [{', '.join(n['tags'])}]" if n.get("tags") else ""
            lines.append(f"- {n['title']}{tags_str}: {n['content'][:100]}... [id: {n['id']}]")

        return f"Found {len(notes)} note(s):\n" + "\n".join(lines)
    except Exception as e:
        return f"Error fetching notes: {e}"


@tool(args_schema=SearchNotesInput)
def search_notes(query: str, **kwargs) -> str:
    """Search notes by title or content."""
    user_id = kwargs.get("user_phone", "default")

    try:
        notes = db.search_notes(user_id, query)
        if not notes:
            return f"No notes found matching '{query}'."

        lines = []
        for n in notes:
            lines.append(f"- {n['title']}: {n['content'][:150]}... [id: {n['id']}]")

        return f"Found {len(notes)} note(s):\n" + "\n".join(lines)
    except Exception as e:
        return f"Error searching notes: {e}"
