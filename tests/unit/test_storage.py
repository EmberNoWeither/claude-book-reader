"""Storage 测试 — 原子写入、读缓存、子目录"""

from __future__ import annotations

from core.storage import Storage


def test_init_creates_dirs(tmp_data_dir):
    Storage(tmp_data_dir)
    assert (tmp_data_dir / "books").is_dir()


def test_read_json_returns_default_when_missing(tmp_storage):
    assert tmp_storage.read_json("library.json") == []
    assert tmp_storage.read_json("bookmarks.json") == {}
    assert tmp_storage.read_json("unknown.json") == {}


def test_write_then_read_json(tmp_storage):
    data = [{"id": "abc", "title": "Test"}]
    tmp_storage.write_json("library.json", data)
    assert tmp_storage.read_json("library.json") == data


def test_write_json_is_atomic(tmp_storage, tmp_data_dir):
    """tmp 文件应该被 rename，不应残留"""
    tmp_storage.write_json("library.json", [{"id": "1"}])
    assert (tmp_data_dir / "library.json").exists()
    assert not (tmp_data_dir / "library.tmp").exists()


def test_read_uses_cache(tmp_storage, tmp_data_dir):
    tmp_storage.write_json("library.json", [{"id": "1"}])
    # 直接修改文件，缓存还是旧值
    (tmp_data_dir / "library.json").write_text('[{"id": "X"}]', encoding="utf-8")
    assert tmp_storage.read_json("library.json") == [{"id": "1"}]
    # invalidate 后读取新值
    tmp_storage.invalidate("library.json")
    assert tmp_storage.read_json("library.json") == [{"id": "X"}]


def test_book_dir_creates_subdirectory(tmp_storage):
    book_dir = tmp_storage.book_dir("abc123")
    assert book_dir.is_dir()
    assert book_dir.name == "abc123"


def test_book_json_roundtrip(tmp_storage):
    tmp_storage.write_book_json("bk1", "metadata.json", {"toc": [["1", "Chapter", 1]]})
    assert tmp_storage.read_book_json("bk1", "metadata.json") == {"toc": [["1", "Chapter", 1]]}


def test_book_json_default_when_missing(tmp_storage):
    assert tmp_storage.read_book_json("nonexistent", "metadata.json") == {}
    assert tmp_storage.read_book_json("nonexistent", "notes.json") == []


def test_text_cache_roundtrip(tmp_storage):
    tmp_storage.write_text_cache("bk1", 5, "page 5 content")
    assert tmp_storage.read_text_cache("bk1", 5) == "page 5 content"
    assert tmp_storage.read_text_cache("bk1", 99) is None


def test_yaml_roundtrip(tmp_storage):
    tmp_storage.write_yaml("config.yaml", {"app": {"theme": "dark"}})
    assert tmp_storage.read_yaml("config.yaml") == {"app": {"theme": "dark"}}


def test_yaml_default_empty_when_missing(tmp_storage):
    assert tmp_storage.read_yaml("missing.yaml") == {}


def test_unicode_preserved(tmp_storage):
    tmp_storage.write_json("library.json", [{"title": "中文标题", "author": "作者"}])
    raw = (tmp_storage.data_dir / "library.json").read_text(encoding="utf-8")
    assert "中文标题" in raw  # ensure_ascii=False 应直接写入中文
    assert tmp_storage.read_json("library.json")[0]["title"] == "中文标题"
