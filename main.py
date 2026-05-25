"""Claude Book Reader — 应用入口"""

from __future__ import annotations

import sys
from pathlib import Path

# 确保 src 在 sys.path 中，使绝对导入生效
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))


def main() -> int:
    from app import App
    app = App()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
