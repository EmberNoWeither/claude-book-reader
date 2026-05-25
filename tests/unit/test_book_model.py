"""Book/Category/Tag/Bookmark 数据模型测试"""

from __future__ import annotations

from core.book import Book, Bookmark, Category, Tag


def test_book_default_id_unique():
    b1 = Book()
    b2 = Book()
    assert b1.id != b2.id
    assert len(b1.id) == 12


def test_book_to_dict_roundtrip():
    b = Book(title="Deep Learning", author="Goodfellow", pages=800)
    d = b.to_dict()
    b2 = Book.from_dict(d)
    assert b2.title == "Deep Learning"
    assert b2.author == "Goodfellow"
    assert b2.pages == 800
    assert b2.id == b.id


def test_book_progress_pct():
    b = Book(pages=200, current_page=50)
    assert b.progress_pct == 25.0
    b2 = Book(pages=0)
    assert b2.progress_pct == 0.0
    b3 = Book(pages=100, current_page=200)  # over-clamped
    assert b3.progress_pct == 100.0


def test_book_from_dict_ignores_unknown_keys():
    b = Book.from_dict({"title": "X", "unknown_field": "Y"})
    assert b.title == "X"
    assert not hasattr(b, "unknown_field")


def test_category_nested_roundtrip():
    child = Category(id="c2", name="ML", parent_id="c1")
    parent = Category(id="c1", name="CS", children=[child])
    d = parent.to_dict()
    p2 = Category.from_dict(d)
    assert p2.name == "CS"
    assert len(p2.children) == 1
    assert p2.children[0].name == "ML"
    assert p2.children[0].parent_id == "c1"


def test_tag_roundtrip():
    t = Tag(name="favorite", color="#e74c3c")
    t2 = Tag.from_dict(t.to_dict())
    assert t2.name == "favorite"
    assert t2.color == "#e74c3c"
    assert t2.id == t.id


def test_tag_default_color():
    t = Tag(name="x")
    assert t.color == "#3498db"


def test_bookmark_roundtrip():
    bm = Bookmark(book_id="b1", page_number=42, title="key formula", note="重点")
    bm2 = Bookmark.from_dict(bm.to_dict())
    assert bm2.book_id == "b1"
    assert bm2.page_number == 42
    assert bm2.title == "key formula"
    assert bm2.note == "重点"
