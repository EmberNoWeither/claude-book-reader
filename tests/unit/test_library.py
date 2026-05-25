"""Library CRUD + import_pdf 测试"""

from __future__ import annotations

import pytest

from core.book import Book, Bookmark


def test_empty_library(tmp_library):
    assert tmp_library.list_books() == []
    assert tmp_library.list_categories() == []
    assert tmp_library.list_tags() == []


def test_add_and_list_book(tmp_library):
    book = Book(title="Test", author="X", pages=100)
    tmp_library.add_book(book)
    books = tmp_library.list_books()
    assert len(books) == 1
    assert books[0].title == "Test"


def test_get_book_by_id(tmp_library):
    book = Book(title="A", pages=50)
    tmp_library.add_book(book)
    assert tmp_library.get_book(book.id).title == "A"
    assert tmp_library.get_book("missing") is None


def test_update_book(tmp_library):
    book = Book(title="Old", current_page=0)
    tmp_library.add_book(book)
    book.title = "New"
    book.current_page = 99
    tmp_library.update_book(book)
    fresh = tmp_library.get_book(book.id)
    assert fresh.title == "New"
    assert fresh.current_page == 99


def test_remove_book_clears_bookmarks(tmp_library):
    book = Book(title="A")
    tmp_library.add_book(book)
    tmp_library.add_bookmark(Bookmark(book_id=book.id, page_number=5))
    assert len(tmp_library.list_bookmarks(book.id)) == 1
    tmp_library.remove_book(book.id)
    assert tmp_library.get_book(book.id) is None
    assert tmp_library.list_bookmarks(book.id) == []


def test_update_reading_progress_state_transitions(tmp_library):
    book = Book(title="A", pages=100, reading_status="unread")
    tmp_library.add_book(book)
    tmp_library.update_reading_progress(book.id, 5)
    assert tmp_library.get_book(book.id).reading_status == "reading"
    tmp_library.update_reading_progress(book.id, 100)
    assert tmp_library.get_book(book.id).reading_status == "completed"


def test_search_books(tmp_library):
    tmp_library.add_book(Book(title="Deep Learning", author="Goodfellow"))
    tmp_library.add_book(Book(title="Pattern Recognition", author="Bishop"))
    tmp_library.add_book(Book(title="Linear Algebra", author="Strang"))
    assert len(tmp_library.search_books("learning")) == 1
    assert len(tmp_library.search_books("BISHOP")) == 1  # case insensitive
    assert len(tmp_library.search_books("xxx")) == 0


def test_categories_tree_flat(tmp_library):
    tmp_library.add_category("CS")
    cs = tmp_library.list_categories()[0]
    tmp_library.add_category("ML", parent_id=cs.id)
    flat = tmp_library.get_category_flat()
    names = [c.name for c, _ in flat]
    depths = [d for _, d in flat]
    assert names == ["CS", "ML"]
    assert depths == [0, 1]


def test_tag_crud_propagates_to_books(tmp_library):
    tag = tmp_library.add_tag("important", "#ff0000")
    book = Book(title="A", tags=[tag.id])
    tmp_library.add_book(book)
    assert tag.id in tmp_library.get_book(book.id).tags
    tmp_library.remove_tag(tag.id)
    assert tmp_library.list_tags() == []
    assert tag.id not in tmp_library.get_book(book.id).tags


def test_books_filtered_by_category(tmp_library):
    tmp_library.add_category("CS")
    cs = tmp_library.list_categories()[0]
    tmp_library.add_book(Book(title="A", category_id=cs.id))
    tmp_library.add_book(Book(title="B", category_id=""))
    assert len(tmp_library.books_by_category(cs.id)) == 1


def test_books_filtered_by_tag(tmp_library):
    tag = tmp_library.add_tag("fav")
    tmp_library.add_book(Book(title="A", tags=[tag.id]))
    tmp_library.add_book(Book(title="B"))
    assert len(tmp_library.books_by_tag(tag.id)) == 1


def test_import_pdf(tmp_library, sample_pdf_path):
    book = tmp_library.import_pdf(sample_pdf_path)
    assert book.pages == 5
    assert book.title  # reportlab sets title metadata
    assert book.file_path == str(sample_pdf_path)
    # TOC + metadata 已写入
    md = tmp_library.storage.read_book_json(book.id, "metadata.json")
    assert "toc" in md


def test_import_pdf_missing_file(tmp_library, tmp_path):
    with pytest.raises(FileNotFoundError):
        tmp_library.import_pdf(tmp_path / "nonexistent.pdf")
