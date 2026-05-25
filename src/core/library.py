"""图书库管理器 — 图书/分类/标签的 CRUD"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF

from utils.logger import get_logger

from .book import Book, Bookmark, Category, Tag
from .config import Config
from .storage import Storage

_log = get_logger(__name__)


class Library:
    """图书库 — 管理所有图书、分类、标签"""

    def __init__(self) -> None:
        self._cfg = Config()
        self._storage = Storage(self._cfg.data_dir)

    @property
    def storage(self) -> Storage:
        return self._storage

    # ═══════════════════════════════════════════════════
    # 图书 CRUD
    # ═══════════════════════════════════════════════════

    def list_books(self) -> list[Book]:
        data = self._storage.read_json("library.json")
        return [Book.from_dict(d) for d in data]

    def get_book(self, book_id: str) -> Book | None:
        for b in self.list_books():
            if b.id == book_id:
                return b
        return None

    def add_book(self, book: Book) -> None:
        books = self._storage.read_json("library.json")
        books.append(book.to_dict())
        self._storage.write_json("library.json", books)

    def update_book(self, book: Book) -> None:
        books = self._storage.read_json("library.json")
        for i, d in enumerate(books):
            if d["id"] == book.id:
                books[i] = book.to_dict()
                break
        self._storage.write_json("library.json", books)

    def remove_book(self, book_id: str) -> None:
        books = self._storage.read_json("library.json")
        books = [d for d in books if d["id"] != book_id]
        self._storage.write_json("library.json", books)
        # 清理书签
        bms = self._storage.read_json("bookmarks.json")
        bms.pop(book_id, None)
        self._storage.write_json("bookmarks.json", bms)

    def import_pdf(self, file_path: str | Path) -> Book:
        """导入 PDF：提取元数据 → 创建 Book → 入库"""
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        try:
            doc = fitz.open(file_path)
        except Exception as e:
            _log.exception("Failed to open PDF: %s", file_path)
            raise ValueError(f"无法打开 PDF: {e}") from e

        try:
            meta = doc.metadata or {}
            toc = doc.get_toc()
            pages = doc.page_count
        finally:
            doc.close()

        title = meta.get("title", "") or file_path.stem
        author = meta.get("author", "") or ""
        isbn = meta.get("isbn", "") or ""

        book = Book(
            title=title,
            author=author,
            isbn=isbn,
            publisher=meta.get("publisher", "") or "",
            year=int(meta.get("year", 0)) if meta.get("year") else 0,
            pages=pages,
            file_path=str(file_path),
        )

        self.add_book(book)

        # 保存 TOC 到单书元数据
        self._storage.write_book_json(book.id, "metadata.json", {
            "toc": toc,
            "claude_session_id": "",
            "last_sync_to_obsidian": "",
        })

        _log.info("Imported PDF: %s (%d pages, id=%s)", title, pages, book.id)
        return book

    # ═══════════════════════════════════════════════════
    # 分类 CRUD
    # ═══════════════════════════════════════════════════

    def list_categories(self) -> list[Category]:
        data = self._storage.read_json("categories.json")
        return [Category.from_dict(d) for d in data]

    def save_categories(self, categories: list[Category]) -> None:
        self._storage.write_json("categories.json", [c.to_dict() for c in categories])

    def get_category_flat(self) -> list[tuple[Category, int]]:
        """将树形分类展平为 (category, depth) 列表"""
        result: list[tuple[Category, int]] = []

        def walk(cat_list: list[Category], depth: int = 0) -> None:
            for cat in cat_list:
                result.append((cat, depth))
                walk(cat.children, depth + 1)

        walk(self.list_categories())
        return result

    def add_category(self, name: str, parent_id: str = "") -> Category:
        cat = Category(name=name, parent_id=parent_id)
        if not parent_id:
            cats = self.list_categories()
            cats.append(cat)
            self.save_categories(cats)
        else:
            cats = self.list_categories()

            def add_child(cat_list: list[Category]) -> bool:
                for c in cat_list:
                    if c.id == parent_id:
                        c.children.append(cat)
                        return True
                    if add_child(c.children):
                        return True
                return False

            add_child(cats)
            self.save_categories(cats)
        return cat

    # ═══════════════════════════════════════════════════
    # 标签 CRUD
    # ═══════════════════════════════════════════════════

    def list_tags(self) -> list[Tag]:
        data = self._storage.read_json("tags.json")
        return [Tag.from_dict(d) for d in data]

    def save_tags(self, tags: list[Tag]) -> None:
        self._storage.write_json("tags.json", [t.to_dict() for t in tags])

    def add_tag(self, name: str, color: str = "#3498db") -> Tag:
        tags = self.list_tags()
        tag = Tag(name=name, color=color)
        tags.append(tag)
        self.save_tags(tags)
        return tag

    def remove_tag(self, tag_id: str) -> None:
        tags = self.list_tags()
        self.save_tags([t for t in tags if t.id != tag_id])
        # 从所有书中移除该标签
        books = self.list_books()
        for b in books:
            if tag_id in b.tags:
                b.tags.remove(tag_id)
                self.update_book(b)

    # ═══════════════════════════════════════════════════
    # 书签 CRUD
    # ═══════════════════════════════════════════════════

    def list_bookmarks(self, book_id: str) -> list[Bookmark]:
        all_bms = self._storage.read_json("bookmarks.json")
        bms_data = all_bms.get(book_id, [])
        return [Bookmark.from_dict(d) for d in bms_data]

    def add_bookmark(self, bookmark: Bookmark) -> None:
        all_bms = self._storage.read_json("bookmarks.json")
        if bookmark.book_id not in all_bms:
            all_bms[bookmark.book_id] = []
        all_bms[bookmark.book_id].append(bookmark.to_dict())
        self._storage.write_json("bookmarks.json", all_bms)

    def remove_bookmark(self, book_id: str, bm_id: str) -> None:
        all_bms = self._storage.read_json("bookmarks.json")
        if book_id in all_bms:
            all_bms[book_id] = [d for d in all_bms[book_id] if d["id"] != bm_id]
            self._storage.write_json("bookmarks.json", all_bms)

    # ═══════════════════════════════════════════════════
    # 阅读状态
    # ═══════════════════════════════════════════════════

    def update_reading_progress(self, book_id: str, page: int) -> None:
        book = self.get_book(book_id)
        if book is None:
            return
        book.current_page = page
        book.last_read_date = datetime.now().isoformat()
        if book.reading_status == "unread":
            book.reading_status = "reading"
        if page >= book.pages > 0:
            book.reading_status = "completed"
        self.update_book(book)

    # ═══════════════════════════════════════════════════
    # 搜索
    # ═══════════════════════════════════════════════════

    def search_books(self, query: str) -> list[Book]:
        q = query.lower()
        results: list[Book] = []
        for b in self.list_books():
            if (
                q in b.title.lower()
                or q in b.author.lower()
                or q in b.publisher.lower()
            ):
                results.append(b)
        return results

    def books_by_category(self, category_id: str) -> list[Book]:
        return [b for b in self.list_books() if b.category_id == category_id]

    def books_by_tag(self, tag_id: str) -> list[Book]:
        return [b for b in self.list_books() if tag_id in b.tags]
