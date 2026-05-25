"""笔记管理器 — CRUD + 过滤查询"""

from __future__ import annotations

from datetime import datetime

from core.storage import Storage

from .models import Note


class NoteManager:
    """管理所有书籍的笔记，存储在 books/{book_id}/notes.json"""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def list_notes(self, book_id: str) -> list[Note]:
        raw = self._storage.read_book_json(book_id, "notes.json")
        if not isinstance(raw, list):
            return []
        return [Note.from_dict(d) for d in raw]

    def get_note(self, book_id: str, note_id: str) -> Note | None:
        for note in self.list_notes(book_id):
            if note.id == note_id:
                return note
        return None

    def add_note(self, note: Note) -> None:
        notes = self.list_notes(note.book_id)
        notes.append(note)
        self._save(note.book_id, notes)

    def update_note(self, note: Note) -> None:
        notes = self.list_notes(note.book_id)
        note.modified_at = datetime.now().isoformat()
        for i, n in enumerate(notes):
            if n.id == note.id:
                notes[i] = note
                break
        self._save(note.book_id, notes)

    def delete_note(self, book_id: str, note_id: str) -> None:
        notes = [n for n in self.list_notes(book_id) if n.id != note_id]
        self._save(book_id, notes)

    def notes_for_page(self, book_id: str, page: int) -> list[Note]:
        return [n for n in self.list_notes(book_id)
                if n.page == page and n.note_type in ("page_anchor", "highlight")]

    def notes_for_chapter(self, book_id: str, chapter: str) -> list[Note]:
        return [n for n in self.list_notes(book_id)
                if n.chapter == chapter and n.note_type == "chapter"]

    def global_notes(self, book_id: str) -> list[Note]:
        return [n for n in self.list_notes(book_id) if n.note_type == "global"]

    def all_highlights(self, book_id: str) -> list[Note]:
        return [n for n in self.list_notes(book_id) if n.note_type == "highlight"]

    def _save(self, book_id: str, notes: list[Note]) -> None:
        self._storage.write_book_json(
            book_id, "notes.json", [n.to_dict() for n in notes]
        )
