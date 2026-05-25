"""JSON/YAML 文件存储层 — 原子写入、读缓存、线程安全"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import yaml


class Storage:
    """统一的 JSON/YAML 文件读写封装"""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self._cache: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "books").mkdir(exist_ok=True)

    # ── JSON ──────────────────────────────────────────

    def read_json(self, filename: str) -> Any:
        if filename not in self._cache:
            path = self.data_dir / filename
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    self._cache[filename] = json.load(f)
            else:
                self._cache[filename] = self._default_for(filename)
        return self._cache[filename]

    def write_json(self, filename: str, data: Any) -> None:
        with self._lock:
            path = self.data_dir / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tmp.replace(path)
            self._cache[filename] = data

    def invalidate(self, filename: str) -> None:
        self._cache.pop(filename, None)

    # ── YAML ──────────────────────────────────────────

    def read_yaml(self, filename: str) -> dict:
        path = self.data_dir / filename
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def write_yaml(self, filename: str, data: dict) -> None:
        with self._lock:
            path = self.data_dir / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            tmp.replace(path)

    # ── 书籍子目录 ────────────────────────────────────

    def book_dir(self, book_id: str) -> Path:
        p = self.data_dir / "books" / book_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def read_book_json(self, book_id: str, filename: str) -> Any:
        path = self.book_dir(book_id) / filename
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return self._default_for(filename)

    def write_book_json(self, book_id: str, filename: str, data: Any) -> None:
        with self._lock:
            path = self.book_dir(book_id) / filename
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tmp.replace(path)

    def write_text_cache(self, book_id: str, page: int, text: str) -> None:
        cache_dir = self.book_dir(book_id) / "text_cache"
        cache_dir.mkdir(exist_ok=True)
        path = cache_dir / f"page_{page:04d}.txt"
        with self._lock:
            path.write_text(text, encoding="utf-8")

    def read_text_cache(self, book_id: str, page: int) -> str | None:
        path = self.book_dir(book_id) / "text_cache" / f"page_{page:04d}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    # ── 辅助 ──────────────────────────────────────────

    @staticmethod
    def _default_for(filename: str) -> Any:
        defaults: dict[str, Any] = {
            "library.json": [],
            "categories.json": [],
            "tags.json": [],
            "bookmarks.json": {},
            "reading_sessions.json": [],
            "concepts.json": [],
            "concept_links.json": [],
            "notes.json": [],
            "metadata.json": {},
        }
        return defaults.get(filename, {})
