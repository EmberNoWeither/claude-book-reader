"""ThemeManager 单元测试"""

import pytest

from ui.themes.palette import DARK, LIGHT, PALETTES, Palette


class TestPalette:
    def test_palette_completeness(self):
        fields = set(Palette.__dataclass_fields__.keys())
        for name, p in PALETTES.items():
            for f in fields:
                assert getattr(p, f) is not None, f"{name} missing {f}"

    def test_all_palettes_registered(self):
        assert "dark" in PALETTES
        assert "light" in PALETTES
        assert "warm" in PALETTES

    def test_palette_frozen(self):
        with pytest.raises((TypeError, AttributeError)):
            DARK.name = "modified"


class TestThemeManagerUnit:
    def test_default_dark(self, monkeypatch):
        from core.config import Config

        monkeypatch.setattr(Config, "_instance", None)
        cfg = Config()
        cfg._loaded = True
        cfg._data = {"app": {"theme": "dark"}}

        from ui.themes.theme_manager import ThemeManager

        class FakeApp:
            def setStyleSheet(self, qss):
                self.qss = qss

        app = FakeApp()
        tm = ThemeManager(app, cfg)
        assert tm.current() == "dark"
        assert tm.palette() == DARK
        assert "{{" not in app.qss

    def test_apply_light(self, monkeypatch):
        from core.config import Config

        monkeypatch.setattr(Config, "_instance", None)
        cfg = Config()
        cfg._loaded = True
        cfg._data = {"app": {"theme": "dark"}}

        from ui.themes.theme_manager import ThemeManager

        class FakeApp:
            def setStyleSheet(self, qss):
                self.qss = qss

        app = FakeApp()
        tm = ThemeManager(app, cfg)
        tm.apply("light")
        assert tm.current() == "light"
        assert tm.palette() == LIGHT
        assert "{{" not in app.qss

    def test_invalid_theme_fallback(self, monkeypatch):
        from core.config import Config

        monkeypatch.setattr(Config, "_instance", None)
        cfg = Config()
        cfg._loaded = True
        cfg._data = {"app": {"theme": "nonexistent"}}

        from ui.themes.theme_manager import ThemeManager

        class FakeApp:
            def setStyleSheet(self, qss):
                self.qss = qss

        app = FakeApp()
        tm = ThemeManager(app, cfg)
        assert tm.current() == "dark"

    def test_qss_no_unresolved_placeholders(self, monkeypatch):
        from core.config import Config

        monkeypatch.setattr(Config, "_instance", None)
        cfg = Config()
        cfg._loaded = True
        cfg._data = {"app": {"theme": "warm"}}

        from ui.themes.theme_manager import ThemeManager

        class FakeApp:
            def setStyleSheet(self, qss):
                self.qss = qss

        app = FakeApp()
        ThemeManager(app, cfg)
        assert "{{" not in app.qss
        assert "}}" not in app.qss
