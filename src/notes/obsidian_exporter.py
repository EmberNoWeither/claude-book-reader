"""Obsidian 仓库导出 — 将笔记和概念导出为 Obsidian vault"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from core.storage import Storage
from core.config import Config
from core.library import Library
from core.book import Book
from notes.note_manager import NoteManager
from knowledge.graph_engine import GraphEngine


@dataclass
class ExportResult:
    files_created: int = 0
    files_updated: int = 0
    files_unchanged: int = 0
    errors: list[str] = field(default_factory=list)


class ObsidianExporter:
    """将笔记和概念导出到 Obsidian vault"""

    def __init__(self, storage: Storage, config: Config, library: Library) -> None:
        self._storage = storage
        self._config = config
        self._library = library
        self._note_manager = NoteManager(storage)
        self._graph = GraphEngine(storage)

        templates_dir = Path(__file__).parent.parent.parent / "resources" / "templates" / "obsidian"
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            keep_trailing_newline=True,
        )

    @property
    def vault_path(self) -> Path:
        configured = self._config.get("obsidian", "vault_path", default="./obsidian-vault")
        p = Path(configured)
        if not p.is_absolute():
            p = Path.cwd() / p
        return p

    def export_all(self) -> ExportResult:
        result = ExportResult()
        self._ensure_vault_structure()
        for book in self._library.list_books():
            r = self._export_single_book(book)
            result.files_created += r.files_created
            result.files_updated += r.files_updated
            result.errors.extend(r.errors)
        self._export_concepts(result)
        self._export_moc(result)
        return result

    def export_book(self, book_id: str) -> ExportResult:
        result = ExportResult()
        self._ensure_vault_structure()
        book = self._library.get_book(book_id)
        if not book:
            result.errors.append(f"Book {book_id} not found")
            return result
        r = self._export_single_book(book)
        result.files_created += r.files_created
        result.files_updated += r.files_updated
        result.errors.extend(r.errors)
        self._export_concepts(result)
        self._export_moc(result)
        return result

    def _ensure_vault_structure(self) -> None:
        vault = self.vault_path
        vault.mkdir(parents=True, exist_ok=True)
        (vault / "Books").mkdir(exist_ok=True)
        (vault / "Concepts").mkdir(exist_ok=True)
        (vault / "_MOCs").mkdir(exist_ok=True)

    def _export_single_book(self, book: Book) -> ExportResult:
        result = ExportResult()
        vault = self.vault_path
        book_dir = vault / "Books" / self._safe_filename(book.title)
        book_dir.mkdir(parents=True, exist_ok=True)

        notes = self._note_manager.list_notes(book.id)
        concepts = self._graph.concepts_for_book(book.id)
        export_date = datetime.now().strftime("%Y-%m-%d")

        try:
            tmpl = self._env.get_template("book-note.md.j2")
            content = tmpl.render(
                book=book,
                notes=[n.__dict__ for n in notes],
                concepts=concepts,
                export_date=export_date,
            )
            target = book_dir / f"{self._safe_filename(book.title)}.md"
            self._write_file(target, content, result)
        except Exception as e:
            result.errors.append(f"Export book {book.title}: {e}")

        return result

    def _export_concepts(self, result: ExportResult) -> None:
        vault = self.vault_path
        export_date = datetime.now().strftime("%Y-%m-%d")

        for concept in self._graph.concepts:
            try:
                relations = []
                for link in self._graph.links:
                    if link.source_id == concept.id:
                        target = self._graph.get_concept(link.target_id)
                        if target:
                            relations.append({
                                "target_name": target.name,
                                "relation_type": link.relation_type,
                                "strength": link.strength,
                                "description": link.description,
                            })

                tmpl = self._env.get_template("concept.md.j2")
                content = tmpl.render(
                    concept=concept,
                    relations=relations,
                    export_date=export_date,
                )
                target_path = vault / "Concepts" / f"{self._safe_filename(concept.name)}.md"
                self._write_file(target_path, content, result)
            except Exception as e:
                result.errors.append(f"Export concept {concept.name}: {e}")

    def _export_moc(self, result: ExportResult) -> None:
        vault = self.vault_path
        export_date = datetime.now().strftime("%Y-%m-%d")
        books = self._library.list_books()
        concepts = self._graph.concepts

        try:
            tmpl = self._env.get_template("moc.md.j2")
            content = tmpl.render(
                books=books,
                concepts=concepts,
                export_date=export_date,
            )
            target_path = vault / "_MOCs" / "知识地图.md"
            self._write_file(target_path, content, result)
        except Exception as e:
            result.errors.append(f"Export MOC: {e}")

    def _write_file(self, path: Path, content: str, result: ExportResult) -> None:
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            if existing == content:
                result.files_unchanged += 1
                return
            result.files_updated += 1
        else:
            result.files_created += 1
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def _safe_filename(name: str) -> str:
        return "".join(c if c.isalnum() or c in " _-" else "_" for c in name).strip()
