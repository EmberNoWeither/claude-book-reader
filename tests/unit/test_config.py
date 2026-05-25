"""Config 测试 — 默认值、deep merge、读写"""

from __future__ import annotations

import pytest
import yaml

from core.config import DEFAULT_CONFIG, Config


@pytest.fixture
def fresh_config(monkeypatch, tmp_path):
    """重置 Config 单例，使用临时目录"""
    monkeypatch.setattr(Config, "_instance", None)
    cfg = Config()
    monkeypatch.setattr(type(cfg), "data_dir",
                        property(lambda self: tmp_path))
    return cfg


def test_load_creates_default_when_missing(fresh_config, tmp_path):
    fresh_config.load()
    cfg_path = tmp_path / "config.yaml"
    assert cfg_path.exists()
    assert fresh_config.get("app", "theme") == "dark"


def test_get_with_default(fresh_config):
    fresh_config.load()
    assert fresh_config.get("nonexistent", default="X") == "X"
    assert fresh_config.get("app", "nonexistent", default="Y") == "Y"


def test_set_and_save(fresh_config, tmp_path):
    fresh_config.load()
    fresh_config.set("app", "theme", value="light")
    fresh_config.save()
    raw = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
    assert raw["app"]["theme"] == "light"


def test_deep_merge_preserves_user_overrides(fresh_config, tmp_path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        yaml.dump({"app": {"theme": "light"}, "claude": {"model": "opus"}}),
        encoding="utf-8",
    )
    fresh_config.load()
    # User override applied
    assert fresh_config.get("app", "theme") == "light"
    assert fresh_config.get("claude", "model") == "opus"
    # Default fields preserved
    assert fresh_config.get("app", "language") == "zh-CN"
    assert "sonnet" in fresh_config.get("claude", "available_models")


def test_obsidian_vault_path_resolution(fresh_config, tmp_path, monkeypatch):
    fresh_config.load()
    fresh_config.set("obsidian", "vault_path", value="./my-vault")
    p = fresh_config.obsidian_vault_path
    assert p.is_absolute()
    assert p.name == "my-vault"


def test_default_config_structure():
    """DEFAULT_CONFIG 必须包含所有必要字段"""
    assert "app" in DEFAULT_CONFIG
    assert "claude" in DEFAULT_CONFIG
    assert "available_models" in DEFAULT_CONFIG["claude"]
    assert "obsidian" in DEFAULT_CONFIG
    assert "reading" in DEFAULT_CONFIG
