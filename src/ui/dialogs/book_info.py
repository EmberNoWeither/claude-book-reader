"""图书信息编辑对话框"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QComboBox,
    QTextEdit,
    QPushButton,
    QLabel,
    QDialogButtonBox,
    QCheckBox,
    QScrollArea,
    QWidget,
)

from core.library import Library
from core.book import Book


class BookInfoDialog(QDialog):
    def __init__(self, library: Library, book: Book, parent=None) -> None:
        super().__init__(parent)
        self._library = library
        self._book = book
        self.setWindowTitle(f"书籍信息 - {book.title}")
        self.setMinimumWidth(450)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._title = QLineEdit(self._book.title)
        form.addRow("书名:", self._title)

        self._author = QLineEdit(self._book.author)
        form.addRow("作者:", self._author)

        self._isbn = QLineEdit(self._book.isbn)
        form.addRow("ISBN:", self._isbn)

        self._publisher = QLineEdit(self._book.publisher)
        form.addRow("出版社:", self._publisher)

        self._year = QSpinBox()
        self._year.setRange(0, 2100)
        self._year.setValue(self._book.year)
        form.addRow("年份:", self._year)

        self._pages = QSpinBox()
        self._pages.setRange(0, 999999)
        self._pages.setValue(self._book.pages)
        self._pages.setReadOnly(True)
        form.addRow("页数:", self._pages)

        self._status = QComboBox()
        self._status.addItems(["unread", "reading", "completed"])
        self._status.setCurrentText(self._book.reading_status)
        form.addRow("状态:", self._status)

        self._rating = QComboBox()
        self._rating.addItems(["未评分", "⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"])
        self._rating.setCurrentIndex(self._book.rating)
        form.addRow("评分:", self._rating)

        # 分类选择
        self._cat_combo = QComboBox()
        self._cat_combo.addItem("(无)", "")
        for c, depth in self._library.get_category_flat():
            prefix = "  " * depth
            self._cat_combo.addItem(f"{prefix}{c.name}", c.id)
        idx = self._cat_combo.findData(self._book.category_id)
        if idx >= 0:
            self._cat_combo.setCurrentIndex(idx)
        form.addRow("分类:", self._cat_combo)

        # 标签多选
        self._tag_checks: list[tuple[QCheckBox, str]] = []
        tags = self._library.list_tags()
        if tags:
            tag_widget = QWidget()
            tag_layout = QHBoxLayout(tag_widget)
            tag_layout.setContentsMargins(0, 0, 0, 0)
            tag_layout.setSpacing(8)
            for tag in tags:
                cb = QCheckBox(tag.name)
                cb.setStyleSheet(f"QCheckBox {{ color: {tag.color}; }}")
                if tag.id in self._book.tags:
                    cb.setChecked(True)
                self._tag_checks.append((cb, tag.id))
                tag_layout.addWidget(cb)
            tag_layout.addStretch()
            form.addRow("标签:", tag_widget)

        form.addRow("备注:", QLabel(""))  # spacer
        self._note = QTextEdit()
        self._note.setMaximumHeight(100)
        self._note.setText(self._book.personal_note)
        form.addRow("个人备注:", self._note)

        layout.addLayout(form)

        # 文件路径（只读）
        path_label = QLabel(f"文件路径: {self._book.file_path}")
        path_label.setStyleSheet("color: #666; font-size: 11px;")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)

        layout.addSpacing(8)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _save(self) -> None:
        self._book.title = self._title.text().strip()
        self._book.author = self._author.text().strip()
        self._book.isbn = self._isbn.text().strip()
        self._book.publisher = self._publisher.text().strip()
        self._book.year = self._year.value()
        self._book.reading_status = self._status.currentText()
        self._book.rating = self._rating.currentIndex()
        self._book.category_id = self._cat_combo.currentData() or ""
        self._book.tags = [tid for cb, tid in self._tag_checks if cb.isChecked()]
        self._book.personal_note = self._note.toPlainText().strip()
        self._library.update_book(self._book)
        self.accept()
