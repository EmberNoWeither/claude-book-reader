"""知识图谱可视化 — QGraphicsView + NetworkX 布局"""

from __future__ import annotations

import math

from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsEllipseItem,
    QGraphicsTextItem,
    QGraphicsLineItem,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
)

from core.storage import Storage
from knowledge.graph_engine import GraphEngine


RELATION_COLORS = {
    "IS_A": "#89b4fa",
    "RELATED_TO": "#a6e3a1",
    "PART_OF": "#f9e2af",
    "LEADS_TO": "#cba6f7",
    "APPLIES_TO": "#fab387",
}

NODE_RADIUS = 30
SCALE_FACTOR = 300


class ConceptNode(QGraphicsEllipseItem):
    """可拖拽的概念节点"""

    def __init__(self, concept_id: str, name: str, x: float, y: float) -> None:
        super().__init__(-NODE_RADIUS, -NODE_RADIUS, NODE_RADIUS * 2, NODE_RADIUS * 2)
        self.concept_id = concept_id
        self.setPos(x, y)
        self.setBrush(QBrush(QColor("#45475a")))
        self.setPen(QPen(QColor("#89b4fa"), 2))
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._label = QGraphicsTextItem(name, self)
        self._label.setDefaultTextColor(QColor("#cdd6f4"))
        font = QFont("Microsoft YaHei", 9)
        self._label.setFont(font)
        br = self._label.boundingRect()
        self._label.setPos(-br.width() / 2, -br.height() / 2)


class GraphCanvas(QGraphicsView):
    """知识图谱画布"""

    concept_selected = pyqtSignal(str)
    concept_double_clicked = pyqtSignal(str)

    def __init__(self, graph_engine: GraphEngine, parent=None) -> None:
        super().__init__(parent)
        self._engine = graph_engine
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setStyleSheet("background: #1e1e2e; border: none;")

    def show_graph(self, book_id: str = "", depth: int = 2) -> None:
        self._scene.clear()
        if book_id:
            concepts = self._engine.concepts_for_book(book_id)
            ids = [c.id for c in concepts]
        else:
            ids = [c.id for c in self._engine.concepts]

        if not ids:
            text = self._scene.addText("暂无概念数据\n\n请先在笔记面板点击「概念」提取关键概念")
            text.setDefaultTextColor(QColor("#6c7086"))
            text.setFont(QFont("Microsoft YaHei", 12))
            return

        layout = self._engine.compute_layout(ids)
        nodes: dict[str, ConceptNode] = {}

        for cid, (x, y) in layout.items():
            concept = self._engine.get_concept(cid)
            if not concept:
                continue
            node = ConceptNode(cid, concept.name, x * SCALE_FACTOR, y * SCALE_FACTOR)
            self._scene.addItem(node)
            nodes[cid] = node

        for link in self._engine.links:
            if link.source_id in nodes and link.target_id in nodes:
                src = nodes[link.source_id]
                tgt = nodes[link.target_id]
                color = RELATION_COLORS.get(link.relation_type, "#6c7086")
                line = QGraphicsLineItem(
                    src.pos().x(), src.pos().y(),
                    tgt.pos().x(), tgt.pos().y(),
                )
                line.setPen(QPen(QColor(color), max(1, link.strength / 3)))
                self._scene.addItem(line)

        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def mouseDoubleClickEvent(self, event) -> None:
        item = self.itemAt(event.pos())
        if isinstance(item, ConceptNode):
            self.concept_double_clicked.emit(item.concept_id)
        super().mouseDoubleClickEvent(event)


class GraphDialog(QDialog):
    """知识图谱弹窗"""

    def __init__(self, storage: Storage, book_id: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("知识图谱")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 8, 8, 8)
        lbl = QLabel(f"概念图谱{' — ' + book_id[:8] if book_id else ''}")
        lbl.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        toolbar.addWidget(lbl)
        toolbar.addStretch()

        btn_refresh = QPushButton("刷新布局")
        btn_refresh.clicked.connect(lambda: self._canvas.show_graph(book_id))
        toolbar.addWidget(btn_refresh)

        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        toolbar.addWidget(btn_close)

        layout.addLayout(toolbar)

        engine = GraphEngine(storage)
        self._canvas = GraphCanvas(engine, self)
        layout.addWidget(self._canvas)

        self._canvas.show_graph(book_id)
