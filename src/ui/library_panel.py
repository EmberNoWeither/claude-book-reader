"""图书库面板 — 左侧边栏"""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.book import Book, Category
from core.library import Library


class LibraryPanel(QWidget):
    """左侧图书库面板：分类树 + 标签过滤 + 图书列表"""

    book_selected = pyqtSignal(str)  # book_id
    book_preview_requested = pyqtSignal(str)  # book_id
    book_preview_view_requested = pyqtSignal(str)  # book_id

    def __init__(self, library: Library, parent=None) -> None:
        super().__init__(parent)
        self._library = library
        self._all_books: list[Book] = []
        self._current_filter_tag: str = ""
        self._current_filter_cat: str = ""

        self.setMinimumWidth(220)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── 搜索框 ──
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 搜索书名/作者...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_search)
        layout.addWidget(self._search)

        # ── 分类树 ──
        cat_label = QLabel("📁 分类")
        cat_label.setObjectName("section_label")
        layout.addWidget(cat_label)

        self._cat_tree = QTreeWidget()
        self._cat_tree.setHeaderHidden(True)
        self._cat_tree.setRootIsDecorated(True)
        self._cat_tree.setIndentation(16)
        self._cat_tree.setMaximumHeight(180)
        self._cat_tree.itemClicked.connect(self._on_category_clicked)
        self._cat_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._cat_tree.customContextMenuRequested.connect(self._cat_context_menu)
        layout.addWidget(self._cat_tree)

        # ── 标签过滤 ──
        tag_label = QLabel("🏷️ 标签")
        tag_label.setObjectName("section_label")
        layout.addWidget(tag_label)

        self._tag_container = QWidget()
        self._tag_layout = QHBoxLayout(self._tag_container)
        self._tag_layout.setContentsMargins(0, 0, 0, 0)
        self._tag_layout.setSpacing(4)
        self._tag_layout.addStretch()
        layout.addWidget(self._tag_container)

        # ── 图书列表 ──
        list_label = QLabel("📚 图书")
        list_label.setObjectName("section_label")
        layout.addWidget(list_label)

        self._book_list = QListWidget()
        self._book_list.setIconSize(QSize(40, 54))
        self._book_list.itemDoubleClicked.connect(self._on_book_double_clicked)
        self._book_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._book_list.customContextMenuRequested.connect(self._book_context_menu)
        layout.addWidget(self._book_list, stretch=1)

        # ── 导入按钮 ──
        btn_import = QPushButton("📥 导入 PDF")
        btn_import.clicked.connect(self.import_book)
        layout.addWidget(btn_import)

    # ═══════════════════════════════════════════════════
    # 公共方法
    # ═══════════════════════════════════════════════════

    def refresh(self) -> None:
        self._all_books = self._library.list_books()
        self._refresh_categories()
        self._refresh_tags()
        self._refresh_book_list()

    def import_book(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入 PDF", "", "PDF 文件 (*.pdf);;所有文件 (*)"
        )
        if not file_path:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            book = self._library.import_pdf(file_path)
            self.refresh()
            self.book_selected.emit(book.id)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "导入失败", f"无法导入 PDF:\n{e}")
        finally:
            QApplication.restoreOverrideCursor()

    # ═══════════════════════════════════════════════════
    # 分类
    # ═══════════════════════════════════════════════════

    def _refresh_categories(self) -> None:
        self._cat_tree.clear()
        # "全部" 根节点
        all_item = QTreeWidgetItem(["📚 全部图书"])
        all_item.setData(0, Qt.ItemDataRole.UserRole, "")
        self._cat_tree.addTopLevelItem(all_item)

        cats = self._library.list_categories()

        def add_items(parent: QTreeWidgetItem, cat_list: list[Category]) -> None:
            for cat in cat_list:
                item = QTreeWidgetItem([f"📁 {cat.name}"])
                item.setData(0, Qt.ItemDataRole.UserRole, cat.id)
                parent.addChild(item)
                add_items(item, cat.children)

        for top_cat in cats:
            top_item = QTreeWidgetItem([f"📁 {top_cat.name}"])
            top_item.setData(0, Qt.ItemDataRole.UserRole, top_cat.id)
            self._cat_tree.addTopLevelItem(top_item)
            add_items(top_item, top_cat.children)

        self._cat_tree.expandAll()

    def _on_category_clicked(self, item: QTreeWidgetItem, col: int) -> None:
        cat_id = item.data(0, Qt.ItemDataRole.UserRole)
        self._current_filter_cat = cat_id
        self._refresh_book_list()

    def _cat_context_menu(self, pos) -> None:
        item = self._cat_tree.itemAt(pos)
        if item is None:
            return
        cat_id = item.data(0, Qt.ItemDataRole.UserRole)
        menu = QMenu(self)

        act_add = menu.addAction("➕ 新建子分类")
        act_del = menu.addAction("🗑️ 删除分类")

        action = menu.exec(self._cat_tree.mapToGlobal(pos))
        if action == act_add:
            from .dialogs.add_category import AddCategoryDialog
            dlg = AddCategoryDialog(self._library, parent_id=cat_id or "", parent=self)
            if dlg.exec():
                self.refresh()
        elif action == act_del:
            if cat_id:
                cats = self._library.list_categories()

                def remove_by_id(clist: list[Category], target: str) -> bool:
                    for i, c in enumerate(clist):
                        if c.id == target:
                            clist.pop(i)
                            return True
                        if remove_by_id(c.children, target):
                            return True
                    return False

                remove_by_id(cats, cat_id)
                self._library.save_categories(cats)
                self.refresh()

    # ═══════════════════════════════════════════════════
    # 标签
    # ═══════════════════════════════════════════════════

    def _refresh_tags(self) -> None:
        # 清空旧标签（保留 stretch）
        while self._tag_layout.count() > 1:
            item = self._tag_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tags = self._library.list_tags()
        for tag in tags:
            btn = QPushButton(f"#{tag.name}")
            btn.setCheckable(True)
            btn.setProperty("tag_id", tag.id)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: {tag.color}22;
                    color: {tag.color};
                    border: 1px solid {tag.color}44;
                    border-radius: 10px;
                    padding: 2px 10px;
                    font-size: 11px;
                }}
                QPushButton:checked {{
                    background: {tag.color}55;
                    border-color: {tag.color};
                }}
                QPushButton:hover {{
                    background: {tag.color}33;
                }}
                """
            )
            btn.clicked.connect(lambda checked, tid=tag.id: self._on_tag_clicked(tid, checked))
            self._tag_layout.insertWidget(self._tag_layout.count() - 1, btn)

        # "新建标签" 按钮
        btn_new = QPushButton("+")
        btn_new.setFixedSize(24, 24)
        btn_new.setProperty("variant", "icon")
        btn_new.clicked.connect(self._on_add_tag)
        self._tag_layout.insertWidget(self._tag_layout.count() - 1, btn_new)

    def _on_tag_clicked(self, tag_id: str, checked: bool) -> None:
        self._current_filter_tag = tag_id if checked else ""
        # Uncheck other tag buttons
        for i in range(self._tag_layout.count()):
            w = self._tag_layout.itemAt(i).widget()
            if isinstance(w, QPushButton) and w.isCheckable():
                if checked and w.property("tag_id") != tag_id:
                    w.setChecked(False)
        self._refresh_book_list()

    def _on_add_tag(self) -> None:
        from .dialogs.add_tag import AddTagDialog
        dlg = AddTagDialog(self._library, self)
        if dlg.exec():
            self.refresh()

    # ═══════════════════════════════════════════════════
    # 图书列表
    # ═══════════════════════════════════════════════════

    def _refresh_book_list(self) -> None:
        self._book_list.clear()
        books = self._all_books

        # 分类过滤（包含子分类）
        if self._current_filter_cat:
            cat_ids = self._collect_category_ids(self._current_filter_cat)
            books = [b for b in books if b.category_id in cat_ids]
        # 标签过滤
        if self._current_filter_tag:
            books = [b for b in books if self._current_filter_tag in b.tags]
        # 搜索过滤
        query = self._search.text().strip().lower()
        if query:
            books = [
                b
                for b in books
                if query in b.title.lower() or query in b.author.lower()
            ]

        for b in books:
            status_icon = {"unread": "○", "reading": "◉", "completed": "●"}
            icon = status_icon.get(b.reading_status, "○")
            pct = f"{b.progress_pct:.0f}%" if b.pages > 0 else ""
            item_text = f"{icon} {b.title}\n   {b.author}  {pct}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, b.id)
            item.setSizeHint(QSize(0, 48))
            self._book_list.addItem(item)

    def _collect_category_ids(self, cat_id: str) -> set[str]:
        """收集指定分类及其所有子分类的 ID"""
        ids = {cat_id}
        cats = self._library.list_categories()

        def walk(cat_list: list[Category]) -> None:
            for c in cat_list:
                if c.id in ids or c.parent_id in ids:
                    ids.add(c.id)
                walk(c.children)

        # 多次遍历确保深层子分类也被收集
        for _ in range(5):
            walk(cats)
        return ids

    def _on_search(self, text: str) -> None:
        self._refresh_book_list()

    def _on_book_double_clicked(self, item: QListWidgetItem) -> None:
        book_id = item.data(Qt.ItemDataRole.UserRole)
        if book_id:
            self.book_selected.emit(book_id)

    def _book_context_menu(self, pos) -> None:
        item = self._book_list.itemAt(pos)
        if item is None:
            return
        book_id = item.data(Qt.ItemDataRole.UserRole)
        book = self._library.get_book(book_id)
        if book is None:
            return

        menu = QMenu(self)
        act_open = menu.addAction("📖 打开阅读")
        act_info = menu.addAction("ℹ️ 书籍信息")

        # 标签子菜单
        tags = self._library.list_tags()
        if tags:
            tag_menu = menu.addMenu("🏷️ 标签")
            tag_actions = []
            for tag in tags:
                act = tag_menu.addAction(f"#{tag.name}")
                act.setCheckable(True)
                act.setChecked(tag.id in book.tags)
                act.setData(tag.id)
                tag_actions.append(act)
            tag_menu.triggered.connect(
                lambda a: self._toggle_book_tag(book_id, a.data(), a.isChecked())
            )

        # 分类子菜单
        cat_menu = menu.addMenu("📁 分类")
        act_no_cat = cat_menu.addAction("(无)")
        act_no_cat.setCheckable(True)
        act_no_cat.setChecked(not book.category_id)
        act_no_cat.setData("")
        for c, depth in self._library.get_category_flat():
            prefix = "  " * depth
            act_c = cat_menu.addAction(f"{prefix}{c.name}")
            act_c.setCheckable(True)
            act_c.setChecked(book.category_id == c.id)
            act_c.setData(c.id)
        cat_menu.triggered.connect(
            lambda a: self._set_book_category(book_id, a.data())
        )

        menu.addSeparator()
        act_preview = menu.addAction("🤖 AI 全书预览总结")
        act_view_preview = menu.addAction("📋 查看全书总结")
        menu.addSeparator()
        act_del = menu.addAction("🗑️ 移除")

        action = menu.exec(self._book_list.mapToGlobal(pos))
        if action == act_open and book_id:
            self.book_selected.emit(book_id)
        elif action == act_info:
            from .dialogs.book_info import BookInfoDialog
            BookInfoDialog(self._library, book, self).exec()
            self.refresh()
        elif action == act_preview:
            self.book_preview_requested.emit(book_id)
        elif action == act_view_preview:
            self.book_preview_view_requested.emit(book_id)
        elif action == act_del:
            from PyQt6.QtWidgets import QMessageBox
            r = QMessageBox.question(
                self, "确认移除", f"确定要移除《{book.title}》吗？\n（不会删除原始 PDF 文件）"
            )
            if r == QMessageBox.StandardButton.Yes:
                self._library.remove_book(book_id)
                self.refresh()

    def _toggle_book_tag(self, book_id: str, tag_id: str, checked: bool) -> None:
        book = self._library.get_book(book_id)
        if not book:
            return
        if checked and tag_id not in book.tags:
            book.tags.append(tag_id)
        elif not checked and tag_id in book.tags:
            book.tags.remove(tag_id)
        self._library.update_book(book)
        self._all_books = self._library.list_books()
        self._refresh_book_list()

    def _set_book_category(self, book_id: str, cat_id: str) -> None:
        book = self._library.get_book(book_id)
        if not book:
            return
        book.category_id = cat_id
        self._library.update_book(book)
        self._all_books = self._library.list_books()
        self._refresh_book_list()
