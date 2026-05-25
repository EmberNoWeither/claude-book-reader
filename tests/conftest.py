"""共享 pytest fixtures"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.generate_sample_pdf import generate_sample_pdf


@pytest.fixture(scope="session")
def sample_pdf_path(tmp_path_factory) -> Path:
    """会话级别测试 PDF（生成一次复用）"""
    path = tmp_path_factory.mktemp("fixtures") / "sample.pdf"
    return generate_sample_pdf(path)


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """临时数据目录，模拟 ~/.claude-book-reader/"""
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def tmp_storage(tmp_data_dir):
    """临时 Storage 实例"""
    from core.storage import Storage
    return Storage(tmp_data_dir)


@pytest.fixture
def tmp_library(tmp_data_dir, monkeypatch):
    """指向临时目录的 Library 实例（绕过单例 Config）"""
    from core.config import Config
    from core.library import Library

    cfg = Config()
    monkeypatch.setattr(type(cfg), "data_dir", property(lambda self: tmp_data_dir))
    return Library()
