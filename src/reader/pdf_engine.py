"""PyMuPDF document wrapper — open, read, extract text, render pages."""

from __future__ import annotations

from pathlib import Path

import fitz


class PdfEngine:
    """Wraps a fitz.Document for all PDF operations."""

    def __init__(self, file_path: str | Path) -> None:
        self._path = Path(file_path)
        self._doc: fitz.Document | None = None

    @property
    def doc(self) -> fitz.Document:
        if self._doc is None:
            self._doc = fitz.open(self._path)
        return self._doc

    @property
    def page_count(self) -> int:
        return self.doc.page_count

    @property
    def toc(self) -> list:
        return self.doc.get_toc()

    @property
    def metadata(self) -> dict:
        return self.doc.metadata or {}

    def get_page(self, page_num: int) -> fitz.Page:
        return self.doc[page_num]

    def get_page_text(self, page_num: int) -> str:
        return self.get_page(page_num).get_text()

    def get_page_words(self, page_num: int) -> list:
        """Return words with bbox: [(x0,y0,x1,y1, word, block_no, line_no, word_no), ...]."""
        return self.get_page(page_num).get_text("words")

    def page_size(self, page_num: int) -> tuple[float, float]:
        """Return (width, height) in PDF points."""
        rect = self.get_page(page_num).rect
        return rect.width, rect.height

    def render_pixmap(self, page_num: int, zoom: float = 1.0) -> fitz.Pixmap:
        page = self.get_page(page_num)
        matrix = fitz.Matrix(zoom, zoom)
        return page.get_pixmap(matrix=matrix)

    def search_page(self, page_num: int, text: str) -> list:
        """Search for text on a page, returns list of fitz.Rect."""
        return self.get_page(page_num).search_for(text)

    def resolve_toc_page(self, heading: str) -> int:
        """Find the page number for a TOC heading by searching for the title text."""
        for page_num in range(self.page_count):
            if heading in self.get_page_text(page_num):
                return page_num
        return -1

    def close(self) -> None:
        if self._doc:
            self._doc.close()
            self._doc = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
