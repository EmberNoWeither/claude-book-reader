"""QGraphicsView-based page canvas with virtual rendering, DPR-aware crisp text,
and working text selection."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
)

from reader.page_renderer import PageRenderer
from reader.pdf_engine import PdfEngine

MODE_SINGLE_CONTINUOUS = "single_continuous"
MODE_DOUBLE_CONTINUOUS = "double_continuous"
MODE_SINGLE_FLIP = "single_flip"
MODE_DOUBLE_FLIP = "double_flip"


class PageCanvas(QGraphicsView):
    """Central PDF viewing area.

    Renders only visible pages (virtual scrolling), multiplies zoom by device
    pixel ratio for crisp text, and supports text selection via mouse drag.
    """

    BUFFER_PAGES = 3

    page_changed = pyqtSignal(int, int)  # current_page (0-based), total_pages
    zoom_changed = pyqtSignal(float)     # display zoom
    text_selected = pyqtSignal(str, int)  # selected_text, page_number
    selection_cleared = pyqtSignal()
    note_highlight_right_clicked = pyqtSignal(int, object)  # page, global_pos (QPoint)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._engine: PdfEngine | None = None
        self._renderer: PageRenderer | None = None
        self._mode: str = MODE_SINGLE_CONTINUOUS
        self._display_zoom: float = 1.0
        self._dpr: float = 1.0
        self._current_page: int = 0

        # Page geometry (calculated fast from PDF page sizes, no rendering)
        self._page_y: list[float] = []   # y position of each page in scene
        self._page_h: list[float] = []   # scene height of each page
        self._page_w: list[float] = []   # scene width of each page

        # Visible page items: {page_num: QGraphicsPixmapItem}
        self._page_items: dict[int, QGraphicsPixmapItem] = {}

        # Text selection (line-based, not rubber-band)
        self._selecting: bool = False
        self._sel_start_scene: tuple[float, float] | None = None
        self._sel_highlights: list[QGraphicsRectItem] = []
        self._sel_text: str = ""
        self._sel_page: int = -1
        self._sel_pdf_rects: list[list[float]] = []  # [[x0,y0,x1,y1], ...] in PDF coords

        # Persistent note highlights: {page_num: [(rects, color)]}
        self._note_highlights: dict[int, list[tuple[list[list[float]], str]]] = {}
        self._note_highlight_items: list[QGraphicsRectItem] = []

        # User-set zoom flag: once user changes zoom, don't auto-fit on resize
        self._user_set_zoom: bool = False

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setBackgroundBrush(QColor("#1e1e2e"))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMouseTracking(True)

        # Middle-click pan state
        self._panning: bool = False
        self._pan_start: tuple[float, float] | None = None

        # Scroll-based page tracking
        self._scroll_timer_id: int = 0

    # ═══════════════════════════════════════
    # Book management
    # ═══════════════════════════════════════

    def open_book(self, file_path: str) -> None:
        self._engine = PdfEngine(file_path)
        self._renderer = PageRenderer(self._engine)
        self._dpr = self.devicePixelRatioF() or self.devicePixelRatio() or 1.0
        self._current_page = 0
        self._mode = MODE_SINGLE_CONTINUOUS
        self._display_zoom = self._calc_fit_width_zoom()
        self._user_set_zoom = False
        self._clear_selection()
        self._rebuild_layout()
        self.verticalScrollBar().setValue(0)

    def close_book(self) -> None:
        self._clear_selection()
        self._page_items.clear()
        if self._engine:
            self._engine.close()
        self._engine = None
        self._renderer = None
        self._scene.clear()

    @property
    def has_book(self) -> bool:
        return self._engine is not None

    @property
    def current_page(self) -> int:
        return self._current_page

    @property
    def total_pages(self) -> int:
        return self._engine.page_count if self._engine else 0

    @property
    def display_zoom(self) -> float:
        return self._display_zoom

    def _render_zoom(self) -> float:
        return self._display_zoom * self._dpr

    # ═══════════════════════════════════════
    # Mode
    # ═══════════════════════════════════════

    def set_mode(self, mode: str) -> None:
        if mode == self._mode or not self._engine:
            return
        self._mode = mode
        if mode in (MODE_SINGLE_FLIP, MODE_DOUBLE_FLIP):
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        else:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._clear_selection()
        self._rebuild_layout()

    @property
    def mode(self) -> str:
        return self._mode

    # ═══════════════════════════════════════
    # Zoom
    # ═══════════════════════════════════════

    def set_zoom(self, zoom: float, user_initiated: bool = True) -> None:
        if not self._engine:
            return
        self._display_zoom = max(0.1, min(5.0, zoom))
        if user_initiated:
            self._user_set_zoom = True
        self._rebuild_layout()
        self.zoom_changed.emit(self._display_zoom)

    def zoom_in(self) -> None:
        self.set_zoom(self._display_zoom * 1.15)

    def zoom_out(self) -> None:
        self.set_zoom(self._display_zoom / 1.15)

    def fit_width(self) -> None:
        self._user_set_zoom = False
        self.set_zoom(self._calc_fit_width_zoom(), user_initiated=False)

    def fit_page(self) -> None:
        if not self._engine:
            return
        pw, ph = self._engine.page_size(self._current_page)
        vw = max(self.viewport().width(), 200) - 20
        vh = max(self.viewport().height(), 200) - 20
        self._user_set_zoom = False
        self.set_zoom(min(vw / pw, vh / ph), user_initiated=False)

    def zoom_original(self) -> None:
        self.set_zoom(1.0)

    def _calc_fit_width_zoom(self) -> float:
        if not self._engine:
            return 1.0
        pw, _ = self._engine.page_size(0)
        vw = max(self.viewport().width(), 200) - 20
        return max(0.1, vw / pw)

    def _viewport_w(self) -> int:
        return max(self.viewport().width(), 400)

    # ═══════════════════════════════════════
    # Navigation
    # ═══════════════════════════════════════

    def go_to_page(self, page_num: int) -> None:
        if not self._engine:
            return
        page_num = max(0, min(page_num, self._engine.page_count - 1))
        self._current_page = page_num
        self._clear_selection()

        if self._mode in (MODE_SINGLE_FLIP, MODE_DOUBLE_FLIP):
            self._rebuild_layout()
        else:
            self._scroll_to_page(page_num)

        self.page_changed.emit(self._current_page, self._engine.page_count)

    def next_page(self) -> None:
        if not self._engine:
            return
        step = 2 if self._mode == MODE_DOUBLE_FLIP else 1
        self.go_to_page(self._current_page + step)

    def prev_page(self) -> None:
        if not self._engine:
            return
        step = 2 if self._mode == MODE_DOUBLE_FLIP else 1
        self.go_to_page(self._current_page - step)

    def _scroll_to_page(self, page_num: int) -> None:
        if page_num < len(self._page_y):
            y = self._page_y[page_num]
            self.verticalScrollBar().setValue(int(y))

    # ═══════════════════════════════════════
    # Layout (virtual rendering)
    # ═══════════════════════════════════════

    def _rebuild_layout(self) -> None:
        """Recalculate page geometry and refresh visible items."""
        if not self._engine:
            return

        # Remove all items (they'll be recreated on demand)
        for item in self._page_items.values():
            self._scene.removeItem(item)
        self._page_items.clear()

        # Also remove selection highlights (they reference old items)
        for h in self._sel_highlights:
            self._scene.removeItem(h)
        self._sel_highlights.clear()

        if self._mode == MODE_SINGLE_CONTINUOUS:
            self._layout_single_continuous()
        elif self._mode == MODE_DOUBLE_CONTINUOUS:
            self._layout_double_continuous()
        elif self._mode == MODE_SINGLE_FLIP:
            self._layout_single_flip()
        elif self._mode == MODE_DOUBLE_FLIP:
            self._layout_double_flip()

    def _layout_single_continuous(self) -> None:
        spacing = 8
        self._page_y = []
        self._page_h = []
        self._page_w = []

        y = spacing
        for p in range(self._engine.page_count):
            pw, ph = self._engine.page_size(p)
            w_px = pw * self._display_zoom
            h_px = ph * self._display_zoom
            self._page_y.append(y)
            self._page_h.append(h_px)
            self._page_w.append(w_px)
            y += h_px + spacing

        total_h = y + spacing
        self._scene.setSceneRect(0, 0, self._viewport_w(), total_h)
        self._update_visible_items()

    def _layout_double_continuous(self) -> None:
        spacing = 8
        self._page_y = []
        self._page_h = []
        self._page_w = []
        n = self._engine.page_count

        y = spacing
        p = 0
        while p < n:
            if p == 0:
                pw, ph = self._engine.page_size(0)
                h_px = ph * self._display_zoom
                self._page_y.append(y)
                self._page_h.append(h_px)
                self._page_w.append(pw * self._display_zoom)
                y += h_px + spacing
                p += 1
            else:
                pw0, ph0 = self._engine.page_size(p)
                h0 = ph0 * self._display_zoom
                row_h = h0
                p1 = p + 1
                if p1 < n:
                    pw1, ph1 = self._engine.page_size(p1)
                    h1 = ph1 * self._display_zoom
                    row_h = max(h0, h1)
                self._page_y.append(y)
                self._page_h.append(row_h)
                self._page_w.append(pw0 * self._display_zoom)
                if p1 < n:
                    self._page_y.append(y)
                    self._page_h.append(row_h)
                    self._page_w.append(pw1 * self._display_zoom)
                    p += 2
                else:
                    p += 1
                y += row_h + spacing

        total_h = y + spacing
        self._scene.setSceneRect(0, 0, self._viewport_w(), total_h)
        self._update_visible_items()

    def _layout_single_flip(self) -> None:
        self._page_y = [0]
        self._page_h = [self.viewport().height()]
        self._page_w = [self._viewport_w()]
        self._scene.setSceneRect(0, 0, self._viewport_w(), self.viewport().height())
        self._page_items.clear()
        self._scene.clear()
        self._add_page_item(self._current_page)
        # Fit page in view
        item = self._page_items.get(self._current_page)
        if item:
            self.fitInView(item, Qt.AspectRatioMode.KeepAspectRatio)

    def _layout_double_flip(self) -> None:
        self._page_y = []
        self._page_h = []
        self._page_w = []
        n = self._engine.page_count

        if self._current_page == 0:
            pw, ph = self._engine.page_size(0)
            self._page_y = [0]
            self._page_h = [self.viewport().height()]
            self._page_w = [pw * self._display_zoom]
        else:
            p0 = self._current_page if self._current_page % 2 == 1 else self._current_page
            p0 = max(1, p0)
            p1 = min(p0 + 1, n - 1)
            self._page_y = [0, 0]
            self._page_h = [self.viewport().height(), self.viewport().height()]
            self._page_w = [
                self._engine.page_size(p0)[0] * self._display_zoom,
                self._engine.page_size(p1)[0] * self._display_zoom if p1 != p0 else 0,
            ]

        self._scene.setSceneRect(0, 0, self._viewport_w(), self.viewport().height())
        self._page_items.clear()
        self._scene.clear()

        if self._current_page == 0:
            self._add_page_item(0)
        else:
            p0 = self._current_page if self._current_page % 2 == 1 else self._current_page
            p0 = max(1, p0)
            p1 = min(p0 + 1, n - 1)
            self._add_page_item(p0)
            if p1 != p0:
                self._add_page_item(p1)

        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    # ── Virtual rendering helpers ───────────────

    def _update_visible_items(self) -> None:
        """Create/destroy page items so only visible+buffer pages exist."""
        if not self._engine or not self._page_y:
            return

        if self._mode in (MODE_SINGLE_FLIP, MODE_DOUBLE_FLIP):
            return  # handled by _layout_*_flip directly

        viewport_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        first = self._page_at_y(viewport_rect.top())
        last = self._page_at_y(viewport_rect.bottom())

        needed = set(range(
            max(0, first - self.BUFFER_PAGES),
            min(self._engine.page_count, last + self.BUFFER_PAGES + 1)
        ))

        existing = set(self._page_items.keys())

        # Remove far pages
        for p in existing - needed:
            self._scene.removeItem(self._page_items[p])
            del self._page_items[p]

        # Add new pages
        for p in needed - existing:
            self._add_page_item(p)

        # Redraw note highlights on newly visible pages
        if self._note_highlights:
            self._redraw_note_highlights()

    def _add_page_item(self, page_num: int) -> None:
        if page_num in self._page_items:
            return
        rzoom = self._render_zoom()
        try:
            pixmap = self._renderer.render(page_num, rzoom)
        except Exception:
            from utils.logger import get_logger
            get_logger(__name__).exception("Render failed for page %d", page_num)
            # 占位：用空 pixmap 防止后续 KeyError
            from PyQt6.QtGui import QPixmap
            pixmap = QPixmap(int(self._page_w[page_num] * self._dpr) if page_num < len(self._page_w) else 600,
                             int(self._page_h[page_num] * self._dpr) if page_num < len(self._page_h) else 800)
            pixmap.fill(QColor("#3b1f1f"))
        item = QGraphicsPixmapItem(pixmap)
        item.setScale(1.0 / self._dpr)
        item.setData(Qt.ItemDataRole.UserRole, page_num)

        if self._mode == MODE_SINGLE_CONTINUOUS:
            x = max(0, (self._viewport_w() - self._page_w[page_num]) / 2)
            item.setPos(x, self._page_y[page_num])
        elif self._mode == MODE_DOUBLE_CONTINUOUS:
            self._position_double_item(item, page_num)
        else:
            self._position_flip_item(item, page_num)

        self._scene.addItem(item)
        self._page_items[page_num] = item

    def _position_double_item(self, item: QGraphicsPixmapItem, page_num: int) -> None:
        spacing = 8
        n = self._engine.page_count
        vw = self._viewport_w()

        if page_num == 0:
            # Cover centered
            x = max(0, (vw - self._page_w[0]) / 2)
            item.setPos(x, self._page_y[0])
        else:
            # Even pages on the left, odd on the right
            if page_num % 2 == 1:
                # Left page of a pair
                total_w = self._page_w[page_num]
                if page_num + 1 < n:
                    total_w += spacing + self._page_w[page_num + 1]
                start_x = max(0, (vw - total_w) / 2)
                item.setPos(start_x, self._page_y[page_num])
            else:
                # Right page of a pair
                pw_left = self._page_w[page_num - 1]
                total_w = pw_left + spacing + self._page_w[page_num]
                start_x = max(0, (vw - total_w) / 2)
                item.setPos(start_x + pw_left + spacing, self._page_y[page_num])

    def _position_flip_item(self, item: QGraphicsPixmapItem, page_num: int) -> None:
        spacing = 8
        n = self._engine.page_count
        vw = self._viewport_w()

        if self._mode == MODE_SINGLE_FLIP:
            x = max(0, (vw - self._page_w[page_num]) / 2)
            item.setPos(x, 0)
        else:  # double flip
            if page_num == 0:
                x = max(0, (vw - self._page_w[0]) / 2)
                item.setPos(x, 0)
            else:
                p_left = page_num if page_num % 2 == 1 else page_num - 1
                p_left = max(1, p_left)
                if p_left == page_num:
                    # This is the left page
                    total_w = self._page_w[p_left]
                    p_right = p_left + 1
                    if p_right < n:
                        total_w += spacing + self._page_w[p_right]
                    start_x = max(0, (vw - total_w) / 2)
                    item.setPos(start_x, 0)
                else:
                    # This is the right page
                    pw_left = self._page_w[p_left]
                    total_w = pw_left + spacing + self._page_w[page_num]
                    start_x = max(0, (vw - total_w) / 2)
                    item.setPos(start_x + pw_left + spacing, 0)

    def _page_at_y(self, scene_y: float) -> int:
        """Find the page number at a given scene y coordinate."""
        for p in range(len(self._page_y) - 1, -1, -1):
            if self._page_y[p] <= scene_y:
                return p
        return 0

    # ═══════════════════════════════════════
    # Events
    # ═══════════════════════════════════════

    def wheelEvent(self, event) -> None:
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            return

        if self._mode in (MODE_SINGLE_FLIP, MODE_DOUBLE_FLIP):
            delta = event.angleDelta().y()
            if delta > 0:
                self.prev_page()
            else:
                self.next_page()
            return

        super().wheelEvent(event)
        self._update_visible_page()

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key.Key_Right or key == Qt.Key.Key_Down:
            self.next_page()
        elif key == Qt.Key.Key_Left or key == Qt.Key.Key_Up:
            self.prev_page()
        elif key == Qt.Key.Key_Home:
            self.go_to_page(0)
        elif key == Qt.Key.Key_End:
            self.go_to_page(self._engine.page_count - 1)
        elif key == Qt.Key.Key_Escape:
            self._clear_selection()
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._engine:
            if self._mode in (MODE_SINGLE_FLIP, MODE_DOUBLE_FLIP):
                self._clear_selection()
                self._rebuild_layout()
            elif not self._user_set_zoom:
                # Auto fit-width only when user hasn't manually set zoom
                self._display_zoom = self._calc_fit_width_zoom()
                self._rebuild_layout()
                self.zoom_changed.emit(self._display_zoom)
            else:
                # User set zoom — keep zoom, just re-center pages
                self._rebuild_layout()

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        super().scrollContentsBy(dx, dy)
        if self._mode in (MODE_SINGLE_CONTINUOUS, MODE_DOUBLE_CONTINUOUS):
            self._update_visible_items()
            self._update_visible_page()

    def _recalc_geometry(self) -> None:
        """Recalculate page Y positions and scene rect without clearing items."""
        if not self._engine or self._mode not in (MODE_SINGLE_CONTINUOUS, MODE_DOUBLE_CONTINUOUS):
            return
        spacing = 8
        y = spacing
        self._page_y = []
        self._page_h = []
        self._page_w = []
        for p in range(self._engine.page_count):
            pw, ph = self._engine.page_size(p)
            w_px = pw * self._display_zoom
            h_px = ph * self._display_zoom
            self._page_y.append(y)
            self._page_h.append(h_px)
            self._page_w.append(w_px)
            y += h_px + spacing
        self._scene.setSceneRect(0, 0, self._viewport_w(), y + spacing)

    # ── Mouse events ──────────────────────────

    def mousePressEvent(self, event) -> None:
        # Middle-click: pan
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = (event.pos().x(), event.pos().y())
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            # Clear previous selection on click
            self._clear_selection()

            item = self._item_at(event.pos())
            if item is not None:
                self._start_selection(event.pos())
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning and self._pan_start:
            dx = event.pos().x() - self._pan_start[0]
            dy = event.pos().y() - self._pan_start[1]
            self._pan_start = (event.pos().x(), event.pos().y())
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - dx)
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)
            return

        if self._selecting:
            self._update_selection(event.pos())
            return

        # Show I-beam cursor when hovering over a page item (text area)
        item = self._item_at(event.pos())
        if item is not None:
            self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        else:
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self._pan_start = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        if self._selecting:
            self._finish_selection(event.pos())
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            item = self._item_at(event.pos())
            if item is not None:
                page_num = item.data(Qt.ItemDataRole.UserRole)
                self._select_word_at(event.pos(), item, page_num)
                return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event) -> None:
        """Right-click: check if over a note highlight and emit signal."""
        if self._note_highlight_items:
            scene_pos = self.mapToScene(event.pos())
            for rect_item in self._note_highlight_items:
                if rect_item.sceneBoundingRect().contains(scene_pos):
                    for page_num, page_item in self._page_items.items():
                        if page_item.sceneBoundingRect().contains(scene_pos):
                            self.note_highlight_right_clicked.emit(
                                page_num, event.globalPos()
                            )
                            event.accept()
                            return
        super().contextMenuEvent(event)

    # ═══════════════════════════════════════
    # Text selection
    # ═══════════════════════════════════════

    def _item_at(self, view_pos) -> QGraphicsPixmapItem | None:
        """Find the page item under a viewport position."""
        scene_pos = self.mapToScene(view_pos)
        for item in self._page_items.values():
            if item.sceneBoundingRect().contains(scene_pos):
                return item
        return None

    def _start_selection(self, view_pos) -> None:
        self._selecting = True
        scene_pos = self.mapToScene(view_pos)
        self._sel_start_scene = (scene_pos.x(), scene_pos.y())

    def _update_selection(self, view_pos) -> None:
        if not self._sel_start_scene:
            return
        scene_pos = self.mapToScene(view_pos)
        end = (scene_pos.x(), scene_pos.y())

        # Clear previous highlights
        for h in self._sel_highlights:
            self._scene.removeItem(h)
        self._sel_highlights.clear()

        # Find the page and highlight words between start and end
        for item in self._page_items.values():
            if item.sceneBoundingRect().contains(*self._sel_start_scene):
                page_num = item.data(Qt.ItemDataRole.UserRole)
                text, word_rects, pdf_rects = self._extract_text_between_points(
                    item, self._sel_start_scene, end, page_num
                )
                if word_rects:
                    self._draw_selection_highlights(item, word_rects)
                break

    def _finish_selection(self, view_pos) -> None:
        self._selecting = False

        if not self._sel_start_scene:
            return

        scene_pos = self.mapToScene(view_pos)
        x0, y0 = self._sel_start_scene
        x1, y1 = scene_pos.x(), scene_pos.y()

        # Minimum drag threshold
        if abs(x1 - x0) < 5 and abs(y1 - y0) < 5:
            self._sel_start_scene = None
            return

        end = (x1, y1)

        # Find the page and extract text between start and end points
        for item in self._page_items.values():
            if item.sceneBoundingRect().contains(x0, y0):
                page_num = item.data(Qt.ItemDataRole.UserRole)
                text, word_rects, pdf_rects = self._extract_text_between_points(
                    item, self._sel_start_scene, end, page_num
                )
                if text.strip():
                    self._sel_text = text.strip()
                    self._sel_page = page_num
                    self._sel_pdf_rects = pdf_rects
                    self.text_selected.emit(self._sel_text, page_num)
                    break

        self._sel_start_scene = None

    def _extract_text_from_rect(
        self, item: QGraphicsPixmapItem, scene_rect: QRectF, page_num: int
    ) -> tuple[str, list[tuple[float, float, float, float]]]:
        """Extract text from a page item within a scene-coordinate rectangle.

        Returns (selected_text, list of word bboxes in scene coords).
        """
        words = self._engine.get_page_words(page_num)
        if not words:
            return "", []

        item_pos = item.pos()
        pdf_x0 = (scene_rect.x() - item_pos.x()) / self._display_zoom
        pdf_y0 = (scene_rect.y() - item_pos.y()) / self._display_zoom
        pdf_x1 = pdf_x0 + scene_rect.width() / self._display_zoom
        pdf_y1 = pdf_y0 + scene_rect.height() / self._display_zoom

        selected_words: list[str] = []
        word_rects: list[tuple[float, float, float, float]] = []

        for w in words:
            wx0, wy0, wx1, wy1 = w[0], w[1], w[2], w[3]
            if wx1 >= pdf_x0 and wx0 <= pdf_x1 and wy1 >= pdf_y0 and wy0 <= pdf_y1:
                selected_words.append(w[4])
                sx0 = item_pos.x() + wx0 * self._display_zoom
                sy0 = item_pos.y() + wy0 * self._display_zoom
                sx1 = item_pos.x() + wx1 * self._display_zoom
                sy1 = item_pos.y() + wy1 * self._display_zoom
                word_rects.append((sx0, sy0, sx1, sy1))

        return " ".join(selected_words), word_rects

    def _extract_text_between_points(
        self,
        item: QGraphicsPixmapItem,
        start: tuple[float, float],
        end: tuple[float, float],
        page_num: int,
    ) -> tuple[str, list[tuple[float, float, float, float]], list[list[float]]]:
        """Select words between two scene-coordinate points in reading order.
        Returns (text, scene_rects, pdf_rects)."""
        words = self._engine.get_page_words(page_num)
        if not words:
            return "", [], []

        item_pos = item.pos()
        pdf_sx = (start[0] - item_pos.x()) / self._display_zoom
        pdf_sy = (start[1] - item_pos.y()) / self._display_zoom
        pdf_ex = (end[0] - item_pos.x()) / self._display_zoom
        pdf_ey = (end[1] - item_pos.y()) / self._display_zoom

        if pdf_sy > pdf_ey or (abs(pdf_sy - pdf_ey) < 5 and pdf_sx > pdf_ex):
            pdf_sx, pdf_sy, pdf_ex, pdf_ey = pdf_ex, pdf_ey, pdf_sx, pdf_sy

        selected_words: list[str] = []
        word_rects: list[tuple[float, float, float, float]] = []
        pdf_rects: list[list[float]] = []

        for w in words:
            wx0, wy0, wx1, wy1 = w[0], w[1], w[2], w[3]
            wmid_x = (wx0 + wx1) / 2
            wmid_y = (wy0 + wy1) / 2

            in_range = False
            if abs(pdf_sy - pdf_ey) < (wy1 - wy0):
                in_range = (wmid_x >= pdf_sx and wmid_x <= pdf_ex
                            and wmid_y >= min(pdf_sy, pdf_ey) - 5
                            and wmid_y <= max(pdf_sy, pdf_ey) + 5)
            else:
                line_h = wy1 - wy0
                if wmid_y < pdf_sy - line_h / 2:
                    in_range = False
                elif wmid_y > pdf_ey + line_h / 2:
                    in_range = False
                elif wmid_y < pdf_sy + line_h / 2:
                    in_range = wmid_x >= pdf_sx
                elif wmid_y > pdf_ey - line_h / 2:
                    in_range = wmid_x <= pdf_ex
                else:
                    in_range = True

            if in_range:
                selected_words.append(w[4])
                pdf_rects.append([wx0, wy0, wx1, wy1])
                sx0 = item_pos.x() + wx0 * self._display_zoom
                sy0 = item_pos.y() + wy0 * self._display_zoom
                sx1 = item_pos.x() + wx1 * self._display_zoom
                sy1 = item_pos.y() + wy1 * self._display_zoom
                word_rects.append((sx0, sy0, sx1, sy1))

        return " ".join(selected_words), word_rects, pdf_rects

    def _draw_selection_highlights(
        self, item: QGraphicsPixmapItem, word_rects: list[tuple[float, float, float, float]]
    ) -> None:
        """Create persistent highlight rectangles for selected text."""
        for sx0, sy0, sx1, sy1 in word_rects:
            rect = QGraphicsRectItem(sx0, sy0, sx1 - sx0, sy1 - sy0)
            rect.setPen(QPen(QColor("#89b4fa88"), 0.5))
            rect.setBrush(QBrush(QColor("#89b4fa44")))
            rect.setZValue(1000)
            self._scene.addItem(rect)
            self._sel_highlights.append(rect)

    def _select_word_at(self, view_pos, item: QGraphicsPixmapItem, page_num: int) -> None:
        scene_pos = self.mapToScene(view_pos)
        item_pos = item.pos()

        pdf_x = (scene_pos.x() - item_pos.x()) / self._display_zoom
        pdf_y = (scene_pos.y() - item_pos.y()) / self._display_zoom

        words = self._engine.get_page_words(page_num)
        for w in words:
            wx0, wy0, wx1, wy1 = w[0], w[1], w[2], w[3]
            if wx0 <= pdf_x <= wx1 and wy0 <= pdf_y <= wy1:
                self._sel_text = w[4].strip()
                self._sel_page = page_num
                self._sel_pdf_rects = [[wx0, wy0, wx1, wy1]]
                sx0 = item_pos.x() + wx0 * self._display_zoom
                sy0 = item_pos.y() + wy0 * self._display_zoom
                sx1 = item_pos.x() + wx1 * self._display_zoom
                sy1 = item_pos.y() + wy1 * self._display_zoom
                self._draw_selection_highlights(item, [(sx0, sy0, sx1, sy1)])
                self.text_selected.emit(self._sel_text, page_num)
                return

    def _clear_selection(self) -> None:
        self._sel_text = ""
        self._sel_page = -1
        self._sel_pdf_rects = []
        for h in self._sel_highlights:
            self._scene.removeItem(h)
        self._sel_highlights.clear()
        self._sel_start_scene = None
        if self._sel_text or self._sel_page >= 0:
            self.selection_cleared.emit()

    @property
    def selected_text(self) -> str:
        return self._sel_text

    @property
    def selected_page(self) -> int:
        return self._sel_page

    @property
    def selected_pdf_rects(self) -> list[list[float]]:
        return self._sel_pdf_rects

    # ═══════════════════════════════════════
    # Note highlights (persistent)
    # ═══════════════════════════════════════

    def set_note_highlights(self, highlights: dict[int, list[tuple[list[list[float]], str]]]) -> None:
        """Set persistent note highlights. {page: [( [[x0,y0,x1,y1],...], color ), ...]}"""
        self._note_highlights = highlights
        self._redraw_note_highlights()

    def add_note_highlight(self, page: int, rects: list[list[float]], color: str = "#a6e3a1") -> None:
        if page not in self._note_highlights:
            self._note_highlights[page] = []
        self._note_highlights[page].append((rects, color))
        self._redraw_note_highlights()

    def clear_note_highlights(self) -> None:
        self._note_highlights.clear()
        for item in self._note_highlight_items:
            self._scene.removeItem(item)
        self._note_highlight_items.clear()

    def _redraw_note_highlights(self) -> None:
        for item in self._note_highlight_items:
            self._scene.removeItem(item)
        self._note_highlight_items.clear()

        if not self._engine:
            return

        for page_num, page_item in self._page_items.items():
            entries = self._note_highlights.get(page_num, [])
            if not entries:
                continue
            item_pos = page_item.pos()
            for rects, color in entries:
                for r in rects:
                    x0, y0, x1, y1 = r[0], r[1], r[2], r[3]
                    sx0 = item_pos.x() + x0 * self._display_zoom
                    sy0 = item_pos.y() + y0 * self._display_zoom
                    sx1 = item_pos.x() + x1 * self._display_zoom
                    sy1 = item_pos.y() + y1 * self._display_zoom
                    rect = QGraphicsRectItem(sx0, sy0, sx1 - sx0, sy1 - sy0)
                    rect.setPen(QPen(QColor(color + "88"), 0.5))
                    rect.setBrush(QBrush(QColor(color + "33")))
                    rect.setZValue(500)
                    self._scene.addItem(rect)
                    self._note_highlight_items.append(rect)

    def _update_visible_page(self) -> None:
        if not self._page_items:
            return
        viewport_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        best_page = self._current_page
        best_area = 0.0
        for p, item in self._page_items.items():
            overlap = viewport_rect.intersected(item.sceneBoundingRect())
            area = overlap.width() * overlap.height()
            if area > best_area:
                best_area = area
                best_page = p
        if best_page != self._current_page:
            self._current_page = best_page
            self.page_changed.emit(self._current_page, self._engine.page_count if self._engine else 0)
