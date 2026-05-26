"""主题色板 — QGraphicsItem 等无法用 QSS 的场景使用"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    name: str
    bg_primary: str
    bg_secondary: str
    bg_tertiary: str
    text_primary: str
    text_secondary: str
    accent: str
    accent_alt: str
    success: str
    warning: str
    error: str
    highlight: str
    selection: str
    border: str


DARK = Palette(
    name="dark",
    bg_primary="#1a1a2e",
    bg_secondary="#16161e",
    bg_tertiary="#313244",
    text_primary="#cdd6f4",
    text_secondary="#6c7086",
    accent="#89b4fa",
    accent_alt="#cba6f7",
    success="#a6e3a1",
    warning="#f9e2af",
    error="#f38ba8",
    highlight="#a6e3a180",
    selection="#89b4fa40",
    border="#45475a",
)

LIGHT = Palette(
    name="light",
    bg_primary="#ffffff",
    bg_secondary="#f5f5f5",
    bg_tertiary="#e8e8e8",
    text_primary="#1e1e2e",
    text_secondary="#6c6c80",
    accent="#1e66f5",
    accent_alt="#8839ef",
    success="#40a02b",
    warning="#df8e1d",
    error="#d20f39",
    highlight="#40a02b60",
    selection="#1e66f540",
    border="#ccd0da",
)

WARM = Palette(
    name="warm",
    bg_primary="#f4ecd8",
    bg_secondary="#ebe3cf",
    bg_tertiary="#ddd5c0",
    text_primary="#3c3836",
    text_secondary="#7c6f64",
    accent="#b57614",
    accent_alt="#8f3f71",
    success="#79740e",
    warning="#b57614",
    error="#9d0006",
    highlight="#79740e60",
    selection="#b5761440",
    border="#bdae93",
)

PALETTES: dict[str, Palette] = {"dark": DARK, "light": LIGHT, "warm": WARM}

