"""PDF page → QPixmap rendering with LRU cache."""

from __future__ import annotations

from collections import OrderedDict

from PyQt6.QtGui import QImage, QPixmap

from .pdf_engine import PdfEngine


class PageRenderer:
    """Renders PDF pages to QPixmap with bounded LRU cache."""

    MAX_CACHE = 40

    def __init__(self, engine: PdfEngine) -> None:
        self._engine = engine
        self._cache: OrderedDict[tuple[int, float], QPixmap] = OrderedDict()

    def render(self, page_num: int, render_zoom: float = 1.0) -> QPixmap:
        """Render a page at the given render zoom (should include DPR)."""
        key = (page_num, render_zoom)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]

        pix = self._engine.render_pixmap(page_num, render_zoom)
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        qpixmap = QPixmap.fromImage(img.copy())

        self._cache[key] = qpixmap
        if len(self._cache) > self.MAX_CACHE:
            self._cache.popitem(last=False)

        return qpixmap

    def preload(self, pages: list[int], render_zoom: float) -> None:
        for p in pages:
            if 0 <= p < self._engine.page_count:
                self.render(p, render_zoom)

    def clear(self) -> None:
        self._cache.clear()
