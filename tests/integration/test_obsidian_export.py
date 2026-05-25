"""Obsidian 导出端到端集成测试"""

from __future__ import annotations

import pytest

from core.book import Book
from core.config import Config
from core.library import Library
from knowledge.graph_engine import GraphEngine
from knowledge.models import Concept, ConceptLink
from notes.models import Note
from notes.note_manager import NoteManager
from notes.obsidian_exporter import ObsidianExporter


@pytest.fixture
def export_fixture(tmp_path, monkeypatch):
    """完整环境：library + 1 本书 + 笔记 + 概念 + 配置好 vault path"""
    monkeypatch.setattr(Config, "_instance", None)
    cfg = Config()
    monkeypatch.setattr(type(cfg), "data_dir",
                        property(lambda self: tmp_path / "data"))
    cfg.load()
    vault = tmp_path / "vault"
    cfg.set("obsidian", "vault_path", value=str(vault))

    lib = Library()
    storage = lib.storage

    book = Book(title="Test Book", author="Author X", pages=100)
    lib.add_book(book)

    NoteManager(storage).add_note(Note(
        book_id=book.id,
        note_type="page_anchor",
        page=5,
        title="A note",
        content="some content",
    ))

    graph = GraphEngine(storage)
    a = graph.add_concept(Concept(
        name="Backprop", description="back propagation",
        source_books=[{"book_id": book.id}],
    ))
    b = graph.add_concept(Concept(
        name="Gradient", description="gradient",
        source_books=[{"book_id": book.id}],
    ))
    graph.add_link(ConceptLink(
        source_id=a.id, target_id=b.id,
        relation_type="RELATED_TO", strength=8,
    ))
    graph.save()

    exporter = ObsidianExporter(storage, cfg, lib)
    return exporter, book, vault


@pytest.mark.integration
def test_export_creates_vault_structure(export_fixture):
    exporter, book, vault = export_fixture
    result = exporter.export_book(book.id)
    assert result.errors == []
    assert (vault / "Books").is_dir()
    assert (vault / "Concepts").is_dir()
    assert (vault / "_MOCs").is_dir()


@pytest.mark.integration
def test_export_writes_book_note(export_fixture):
    exporter, book, vault = export_fixture
    exporter.export_book(book.id)
    book_md = vault / "Books" / "Test Book" / "Test Book.md"
    assert book_md.exists()
    text = book_md.read_text(encoding="utf-8")
    assert "Test Book" in text


@pytest.mark.integration
def test_export_writes_concept_pages(export_fixture):
    exporter, book, vault = export_fixture
    exporter.export_book(book.id)
    assert (vault / "Concepts" / "Backprop.md").exists()
    assert (vault / "Concepts" / "Gradient.md").exists()


@pytest.mark.integration
def test_export_writes_moc(export_fixture):
    exporter, book, vault = export_fixture
    exporter.export_book(book.id)
    assert (vault / "_MOCs" / "知识地图.md").exists()


@pytest.mark.integration
def test_incremental_export_unchanged(export_fixture):
    exporter, book, vault = export_fixture
    exporter.export_book(book.id)
    r2 = exporter.export_book(book.id)
    # 第二次：内容相同，应全部 unchanged
    assert r2.files_created == 0
    assert r2.files_updated == 0
    assert r2.files_unchanged > 0


@pytest.mark.integration
def test_safe_filename_strips_special_chars():
    assert ObsidianExporter._safe_filename("Hello/World") == "Hello_World"
    assert ObsidianExporter._safe_filename("中文 标题") == "中文 标题"
    assert ObsidianExporter._safe_filename("a:b*c?d") == "a_b_c_d"


@pytest.mark.integration
def test_export_all_handles_empty_library(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "_instance", None)
    cfg = Config()
    monkeypatch.setattr(type(cfg), "data_dir",
                        property(lambda self: tmp_path / "data"))
    cfg.load()
    cfg.set("obsidian", "vault_path", value=str(tmp_path / "vault"))
    lib = Library()
    exporter = ObsidianExporter(lib.storage, cfg, lib)
    result = exporter.export_all()
    assert result.errors == []
