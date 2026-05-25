"""Whoosh-based full-text search engine for PDF content."""

from __future__ import annotations

from pathlib import Path

from whoosh import index
from whoosh.fields import Schema, TEXT, ID, NUMERIC, STORED
from whoosh.qparser import MultifieldParser, FuzzyTermPlugin


class SearchEngine:
    """Full-text search across indexed PDF books using Whoosh."""

    def __init__(self, index_dir: str | Path) -> None:
        self._index_dir = Path(index_dir)
        self._index_dir.mkdir(parents=True, exist_ok=True)

        self._schema = Schema(
            book_id=ID(stored=True),
            page_number=NUMERIC(stored=True, sortable=True),
            content=TEXT(stored=True),
            title=STORED(),
        )

        self._ix: index.Index | None = None

    @property
    def ix(self) -> index.Index:
        if self._ix is None:
            if index.exists_in(str(self._index_dir)):
                self._ix = index.open_dir(str(self._index_dir))
            else:
                self._ix = index.create_in(str(self._index_dir), self._schema)
        return self._ix

    def index_page(self, book_id: str, page_number: int, content: str, title: str = "") -> None:
        """Add or update a single page's text in the index."""
        writer = self.ix.writer()
        # Remove existing entry for this book+page
        writer.delete_by_term("book_id", book_id)
        writer.add_document(
            book_id=book_id,
            page_number=page_number,
            content=content,
            title=title,
        )
        writer.commit()

    def index_book_pages(self, book_id: str, pages: dict[int, str], title: str = "") -> None:
        """Index multiple pages at once. `pages` maps page_number → text."""
        writer = self.ix.writer()
        writer.delete_by_term("book_id", book_id)
        for page_num, text in pages.items():
            writer.add_document(
                book_id=book_id,
                page_number=page_num,
                content=text,
                title=title,
            )
        writer.commit()

    def remove_book(self, book_id: str) -> None:
        writer = self.ix.writer()
        writer.delete_by_term("book_id", book_id)
        writer.commit()

    def search(self, query: str, book_id: str = "", limit: int = 50) -> list[dict]:
        """
        Search indexed content. Optionally restrict to a single book.
        Returns list of {book_id, page_number, content, title, highlights}.
        """
        with self.ix.searcher() as searcher:
            parser = MultifieldParser(["content"], schema=self._schema)
            parser.add_plugin(FuzzyTermPlugin())
            q = parser.parse(query)

            results = searcher.search(q, limit=limit)
            hits = []
            for r in results:
                if book_id and r["book_id"] != book_id:
                    continue
                hits.append({
                    "book_id": r["book_id"],
                    "page_number": r["page_number"],
                    "content": r.get("content", ""),
                    "title": r.get("title", ""),
                    "highlights": r.highlights("content"),
                })
            return hits

    def get_indexed_page_count(self, book_id: str) -> int:
        """Return how many pages are indexed for a book."""
        with self.ix.searcher() as searcher:
            from whoosh.query import Term
            results = searcher.search(Term("book_id", book_id), limit=0)
            return results.estimated_length()
