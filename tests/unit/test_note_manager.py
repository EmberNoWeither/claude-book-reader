"""NoteManager 测试"""

from __future__ import annotations

import pytest

from notes.models import Note
from notes.note_manager import NoteManager


@pytest.fixture
def nm(tmp_storage):
    return NoteManager(tmp_storage)


def test_empty_notes(nm):
    assert nm.list_notes("book1") == []


def test_add_and_list_notes(nm):
    note = Note(book_id="book1", page=5, content="hello")
    nm.add_note(note)
    notes = nm.list_notes("book1")
    assert len(notes) == 1
    assert notes[0].content == "hello"


def test_get_note(nm):
    note = Note(book_id="book1", content="x")
    nm.add_note(note)
    assert nm.get_note("book1", note.id).content == "x"
    assert nm.get_note("book1", "missing") is None


def test_update_note(nm):
    note = Note(book_id="book1", content="old")
    nm.add_note(note)
    note.content = "new"
    note.title = "Updated"
    nm.update_note(note)
    fresh = nm.get_note("book1", note.id)
    assert fresh.content == "new"
    assert fresh.title == "Updated"
    # modified_at 已更新
    assert fresh.modified_at >= fresh.created_at


def test_delete_note(nm):
    note = Note(book_id="book1", content="x")
    nm.add_note(note)
    nm.delete_note("book1", note.id)
    assert nm.list_notes("book1") == []


def test_filter_by_page(nm):
    nm.add_note(Note(book_id="b1", note_type="page_anchor", page=5, content="A"))
    nm.add_note(Note(book_id="b1", note_type="page_anchor", page=10, content="B"))
    nm.add_note(Note(book_id="b1", note_type="highlight", page=5, content="C"))
    nm.add_note(Note(book_id="b1", note_type="global", page=-1, content="G"))
    page5 = nm.notes_for_page("b1", 5)
    assert len(page5) == 2  # page_anchor + highlight
    assert {n.content for n in page5} == {"A", "C"}


def test_filter_by_chapter(nm):
    nm.add_note(Note(book_id="b1", note_type="chapter", chapter="Ch1", content="A"))
    nm.add_note(Note(book_id="b1", note_type="chapter", chapter="Ch2", content="B"))
    assert len(nm.notes_for_chapter("b1", "Ch1")) == 1


def test_global_notes(nm):
    nm.add_note(Note(book_id="b1", note_type="global", content="global note"))
    nm.add_note(Note(book_id="b1", note_type="page_anchor", page=1, content="local"))
    assert len(nm.global_notes("b1")) == 1


def test_all_highlights(nm):
    nm.add_note(Note(book_id="b1", note_type="highlight", page=1, content="H1"))
    nm.add_note(Note(book_id="b1", note_type="page_anchor", page=2, content="N1"))
    assert len(nm.all_highlights("b1")) == 1


def test_books_isolated(nm):
    nm.add_note(Note(book_id="b1", content="A"))
    nm.add_note(Note(book_id="b2", content="B"))
    assert len(nm.list_notes("b1")) == 1
    assert len(nm.list_notes("b2")) == 1


def test_highlight_rects_persisted(nm):
    note = Note(
        book_id="b1",
        note_type="highlight",
        page=3,
        highlight_rects=[[10.0, 20.0, 30.0, 40.0]],
        highlighted_text="selected text",
    )
    nm.add_note(note)
    fresh = nm.get_note("b1", note.id)
    assert fresh.highlight_rects == [[10.0, 20.0, 30.0, 40.0]]
    assert fresh.highlighted_text == "selected text"
