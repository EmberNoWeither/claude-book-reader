"""应用配置管理 — 读写 config.yaml"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = {
    "app": {
        "language": "zh-CN",
        "theme": "dark",
        "default_reading_mode": "single_continuous",
        "default_zoom": "fit_width",
    },
    "data": {
        "dir": "",  # 空 = 使用默认 ~/.claude-book-reader/
    },
    "obsidian": {
        "vault_path": "./obsidian-vault",
        "auto_sync": False,
        "sync_on_close": True,
    },
    "claude": {
        "max_concurrent_agents": 3,
        "agent_timeout_minutes": 60,
        "skill_name": "book-reader",
        "model": "",
        "available_models": [
            "sonnet",
            "opus",
            "haiku",
            "claude-sonnet-4-6",
            "claude-opus-4-7",
            "claude-haiku-4-5-20251001",
            "deepseek-v4-pro",
        ],
    },
    "reading": {
        "page_cache_size": 20,
        "scroll_speed": 1.0,
        "preload_pages": 5,
        "idle_timeout_minutes": 5,
        "flush_interval_seconds": 30,
    },
}


class Config:
    """全局配置单例"""

    _instance: Config | None = None

    def __new__(cls) -> Config:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        self._data: dict[str, Any] = {}
        self._config_path: Path | None = None

    @property
    def data_dir(self) -> Path:
        custom = self.get("data", "dir")
        if custom:
            return Path(custom).expanduser()
        return Path.home() / ".claude-book-reader"

    @property
    def obsidian_vault_path(self) -> Path:
        p = self.get("obsidian", "vault_path")
        path = Path(p)
        if not path.is_absolute():
            path = Path.cwd() / path
        return path.resolve()

    def load(self, path: str | Path | None = None) -> None:
        if path is None:
            path = self.data_dir / "config.yaml"
        else:
            path = Path(path)
        self._config_path = Path(path)

        if self._config_path.exists():
            with open(self._config_path, encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            self._data = self._deep_merge(DEFAULT_CONFIG, loaded)
        else:
            self._data = DEFAULT_CONFIG.copy()
            self.save()

    def save(self) -> None:
        if self._config_path is None:
            self._config_path = self.data_dir / "config.yaml"
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, allow_unicode=True, default_flow_style=False)

    def get(self, *keys: str, default: Any = None) -> Any:
        node = self._data
        for k in keys:
            if isinstance(node, dict):
                node = node.get(k)
            else:
                return default
            if node is None:
                return default
        return node

    def set(self, *keys: str, value: Any) -> None:
        node = self._data
        for k in keys[:-1]:
            if k not in node:
                node[k] = {}
            node = node[k]
        node[keys[-1]] = value

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        result = base.copy()
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = Config._deep_merge(result[k], v)
            else:
                result[k] = v
        return result
