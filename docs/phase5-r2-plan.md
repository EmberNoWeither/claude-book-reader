# Phase 5 R2 实施计划

> 阅读统计 + 阅读仪表盘 + 三套主题系统。R1 已完成（测试 / 异常 / 日志基础设施），本轮聚焦用户可见的功能与体验升级。

**预计工时**：5 个工作日
**前置条件**：R1 已合入 main（commit `3d3dcf1`）
**交付边界**：本计划三个模块独立可发布，每完成一个就单独 commit，但 R2 作为整体在全部完成后才进入 R3。

---

## 目录

- [一、模块概览](#一模块概览)
- [二、模块 A：阅读统计](#二模块-a阅读统计)
- [三、模块 B：阅读仪表盘](#三模块-b阅读仪表盘)
- [四、模块 C：主题系统](#四模块-c主题系统)
- [五、依赖与配置变更](#五依赖与配置变更)
- [六、施工顺序与里程碑](#六施工顺序与里程碑)
- [七、风险与对策](#七风险与对策)
- [八、验收清单](#八验收清单)

---

## 一、模块概览

| 模块 | 工时 | 影响范围 | 风险 |
|---|---|---|---|
| A — 阅读统计 | 1.5d | 新增 `core/reading_tracker.py`、`main_window` 信号接入 | 低 |
| B — 阅读仪表盘 | 1.5d | 新增 `ui/dialogs/dashboard.py` | 低 |
| C — 主题系统 | 2d | **13 个 UI 文件重构内联样式** + 新增 `ui/themes/` | 中（重构面广） |

施工原则：A 先做完成产生数据 → B 消费数据 → C 在干净基线上重构。

---

## 二、模块 A：阅读统计

### A.1 数据模型

**`src/core/reading_tracker.py`**（新增）

```python
@dataclass
class ReadingSession:
    session_id: str       # uuid hex[:10]
    book_id: str
    start_time: str       # ISO8601
    end_time: str         # ISO8601, 空表示进行中
    start_page: int
    end_page: int

    @property
    def duration_sec(self) -> int: ...

    @property
    def pages_read(self) -> int: ...
```

**存储位置**：`~/.claude-book-reader/reading_sessions.json`（PROJECT_PLAN 已定义，复用）

### A.2 ReadingTracker 类

```python
class ReadingTracker(QObject):
    """会话生命周期管理 + 统计查询"""

    session_started = pyqtSignal(str)   # book_id
    session_ended = pyqtSignal(str)     # session_id
    streak_changed = pyqtSignal(int)    # streak days

    # ── 生命周期 ──
    def start_session(self, book_id: str, page: int) -> str: ...
    def update_progress(self, page: int) -> None: ...     # 防抖落盘
    def end_session(self) -> ReadingSession | None: ...
    def get_active(self) -> ReadingSession | None: ...

    # ── 查询 ──
    def sessions_for_day(self, date: date) -> list[ReadingSession]: ...
    def sessions_for_range(self, start: date, end: date) -> list[ReadingSession]: ...
    def total_today_sec(self) -> int: ...
    def pages_today(self) -> int: ...
    def streak_days(self) -> int: ...
    def speed_pages_per_hour(self, days: int = 7) -> float: ...
```

**关键设计**：

- **闲置自动结束**：QTimer 每 60s tick 一次，若距上次 `update_progress` > 5 分钟（可配）则自动 `end_session`
- **防抖落盘**：`update_progress` 仅更新内存 session，每 30s 批量写文件，避免高频翻页 IO
- **崩溃恢复**：启动时检查最后一条 session 若 `end_time` 为空且开始时间 > 1h 前，标记为已结束（end_time=start_time + 估算时长）
- **跨日处理**：若 session 跨越午夜，分裂为两条记录（简单实现：连续运行时按天切分）

### A.3 接入主窗口

**`src/ui/main_window.py`** 改造点：

```python
def __init__(self, ...):
    ...
    self._tracker = ReadingTracker(self._library.storage, self._config)

def _on_book_opened(self, book_id: str) -> None:
    book = self._library.get_book(book_id)
    if book:
        ...
        self._tracker.start_session(book_id, book.current_page)

def _on_book_closed(self) -> None:
    ...
    self._tracker.end_session()

def _on_page_changed(self, page: int, total: int) -> None:
    ...
    self._tracker.update_progress(page)

def closeEvent(self, event) -> None:
    self._tracker.end_session()
    ...
```

### A.4 状态栏 streak 接入

`status_bar.py` 的 `_streak_label` 已存在但从未调用。在 `MainWindow.__init__` 末尾：

```python
self._tracker.streak_changed.connect(self._statusbar.set_streak)
self._statusbar.set_streak(self._tracker.streak_days())
```

### A.5 配置

`config.yaml` 新增：

```yaml
reading:
  idle_timeout_minutes: 5      # 自动结束会话的闲置阈值
  flush_interval_seconds: 30   # session 数据落盘频率
```

### A.6 测试（新增）

`tests/unit/test_reading_tracker.py`：

| 测试 | 验证内容 |
|---|---|
| `test_start_end_session` | 基本生命周期 |
| `test_update_progress` | 翻页更新 end_page |
| `test_streak_consecutive_days` | 连续 3 天有 session → streak=3 |
| `test_streak_broken_by_gap` | 中间断 1 天 → streak 重置 |
| `test_sessions_for_day` | 按日期过滤 |
| `test_pages_today` | 当日页数累加 |
| `test_crash_recovery` | 加载有未结束 session 时正确补全 end_time |
| `test_pause_on_idle` | mock 闲置 > 5 分钟 → 自动 end |

---

## 三、模块 B：阅读仪表盘

### B.1 UI 设计

**`src/ui/dialogs/dashboard.py`**（新增 QDialog）

```
┌──────────────────────────────────────────────────┐
│  📊 阅读仪表盘                            [关闭]   │
├──────────────────────────────────────────────────┤
│  ┌──────────┬──────────┬──────────┬──────────┐  │
│  │ ⏱ 今日   │ 📖 今日  │ 🔥 连续  │ ⚡ 速度  │  │
│  │   45 分钟 │   32 页  │   3 天   │  42 页/h │  │
│  └──────────┴──────────┴──────────┴──────────┘  │
│                                                  │
│  📅 本周阅读热力图                                │
│  ┌────────────────────────────────────────────┐ │
│  │  一 ████████░░ 2.5h                        │ │
│  │  二 ████░░░░░░ 1.2h                        │ │
│  │  三 ██████████ 3.0h                        │ │
│  │  四 ██░░░░░░░░ 0.5h                        │ │
│  │  五 ████████░░ 2.1h                        │ │
│  │  六 ░░░░░░░░░░ 0.0h                        │ │
│  │  日 ██████░░░░ 1.5h                        │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  📚 书库概览: 12 本 │ 3 本在读 │ 7 本已读        │
│                                                  │
│  📝 最近阅读                                      │
│  ┌────────────────────────────────────────────┐ │
│  │ 《Deep Learning》  P156  今日 45 分钟       │ │
│  │ 《线代应该这样学》  P89   昨日 2 小时       │ │
│  │ 《PRML》           P210  3 天前 1.5 小时   │ │
│  └────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

**实现要点**：

- **统计卡片**：4 个 `QFrame` 横向排列，统一样式（圆角边框 + 大数字 + 副标签）
- **热力图**：`QHBoxLayout` 七列；每列：星期标签 + 横向条形（用 `QProgressBar` 或自绘 `QFrame`，宽度按时长线性映射）
- **最近阅读**：`QTableWidget` 三列（书名 / 进度 / 时间），点击行 → 信号 `book_selected.emit(book_id)` 让主窗口打开该书

### B.2 入口

- **菜单**：`工具 (T)` → `阅读仪表盘`
- **快捷键**：`Ctrl+D`
- **代码**：`main_window._setup_menu()` 增加 action，触发 `_on_show_dashboard()` 调用 `DashboardDialog(self._tracker, self._library, self).exec()`

### B.3 测试

仪表盘是纯展示，不写 UI 测试。`ReadingTracker` 的查询方法已在 A.6 覆盖。

---

## 四、模块 C：主题系统

### C.1 现状分析

`grep setStyleSheet src/ui/ → 13 个文件、50+ 处内联样式`：

```
src/ui/main_window.py        — QTabWidget 样式
src/ui/library_panel.py      — label/button/tag 多处
src/ui/notes_panel.py        — list/button/editor/preview HTML
src/ui/claude_panel.py       — header/button/combo
src/ui/reading_toolbar.py    — mode_style / zoom_btn_style
src/ui/reading_view.py       — selection menu / sel_label
src/ui/status_bar.py         — 1 处
src/ui/dialogs/book_info.py  — tag 颜色
src/ui/dialogs/add_tag.py    — 颜色按钮
src/ui/widgets/
  terminal_widget.py         — _BUBBLE_CSS / 输入框
  page_canvas.py             — 高亮色（QGraphicsItem 不走 QSS）
  graph_canvas.py            — 节点色（同上）
  bookmark_widget.py         — list
  tag_chip.py                — 标签气泡
```

**约束**：`page_canvas.py` 和 `graph_canvas.py` 的颜色用于 `QGraphicsItem.setBrush/setPen`，**无法通过 QSS 控制**。需另起一个 `palette` 字典抽象。

### C.2 设计

#### 文件结构

```
src/ui/themes/
├── __init__.py
├── theme_manager.py        # 加载 + 注入 + 切换
├── palette.py              # 颜色变量字典（dataclass）
├── dark.qss                # 暗色主题
├── light.qss               # 亮色主题
└── warm.qss                # 暖色护眼
```

#### `palette.py`

```python
@dataclass(frozen=True)
class Palette:
    """主题色板 — QGraphicsItem 等无法用 QSS 的场景使用"""
    name: str
    bg_primary: str          # 主背景
    bg_secondary: str        # 次背景
    bg_tertiary: str         # 输入框/按钮背景
    text_primary: str
    text_secondary: str
    accent: str              # 强调色
    accent_alt: str          # 次强调（紫）
    success: str
    warning: str
    error: str
    highlight: str           # 笔记高亮
    selection: str           # 文字选中

DARK = Palette(name="dark", bg_primary="#1a1a2e", ...)
LIGHT = Palette(name="light", bg_primary="#ffffff", ...)
WARM = Palette(name="warm", bg_primary="#f4ecd8", ...)

PALETTES = {"dark": DARK, "light": LIGHT, "warm": WARM}
```

#### `theme_manager.py`

```python
class ThemeManager(QObject):
    """主题切换：加载 QSS + 提供 Palette + 通知订阅者"""

    theme_changed = pyqtSignal(str)   # theme_name

    def __init__(self, app: QApplication, config: Config) -> None: ...
    def current(self) -> str: ...
    def palette(self) -> Palette: ...
    def apply(self, name: str) -> None:
        """加载 QSS + setStyleSheet + 发射信号"""
```

#### QSS 模板化

`dark.qss` 等文件使用 **Jinja2 渲染**（项目已有依赖），变量从 Palette 注入：

```qss
/* dark.qss */
QMainWindow { background: {{ bg_primary }}; }
QWidget {
    background: {{ bg_primary }};
    color: {{ text_primary }};
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}
QPushButton {
    background: {{ bg_tertiary }};
    color: {{ text_primary }};
    border-radius: 6px;
    padding: 6px 16px;
}
QPushButton:hover { background: {{ accent_alt }}; }
/* ... */
```

ThemeManager 加载时：

```python
template = jinja_env.get_template(f"{name}.qss")
qss = template.render(**palette.__dict__)
app.setStyleSheet(qss)
```

### C.3 内联样式重构清单

按文件逐个处理。**目标**：保留唯一一处内联样式的位置 = 用到 Palette 颜色但 QSS 表达不便的场景；其余全部移到对应主题的 QSS 文件里，用类选择器区分。

为每类组件加 `objectName` 或 `class` 属性：

```python
self._title.setObjectName("section_header")  # 然后在 QSS 里写 #section_header { ... }
btn.setProperty("variant", "primary")        # QSS: QPushButton[variant="primary"] { ... }
```

**13 个文件预估改动行数**：约 250 行（内联样式删除）+ 约 300 行 QSS 新增。

**核心动作**：
1. 抽出当前 `DARK_STYLESHEET`（在 `app.py`）→ `dark.qss`
2. 编写 `light.qss`、`warm.qss`（基于同样选择器结构，仅改颜色变量）
3. 逐个 UI 文件：
   - 把内联 `setStyleSheet(...)` 删掉
   - 给组件加 `setObjectName` 或 `setProperty`
   - 在 qss 里添加对应选择器
4. `page_canvas.py` / `graph_canvas.py`：订阅 `ThemeManager.theme_changed`，重绘时使用 `palette()` 返回的色值

### C.4 设置入口

#### `SettingsDialog`（重写当前占位实现）

`src/ui/dialogs/settings.py`：

```
┌────────────────────────────────────┐
│  设置                       [取消]  │
├────────────────────────────────────┤
│  外观                              │
│  ┌────────────────────────────┐    │
│  │ 主题   [● 暗色 ○ 亮色 ○ 暖色] │    │
│  │ 语言   [zh-CN  ▼]          │    │
│  └────────────────────────────┘    │
│                                    │
│  阅读                              │
│  ┌────────────────────────────┐    │
│  │ 闲置自动结束会话  [5 分钟 ⇅] │    │
│  │ 默认阅读模式  [单页连续 ▼]   │    │
│  │ 默认缩放      [适应宽度 ▼]   │    │
│  └────────────────────────────┘    │
│                                    │
│  Claude                            │
│  ┌────────────────────────────┐    │
│  │ 默认模型  [sonnet     ▼]   │    │
│  │ 最大并发  [3 ⇅]            │    │
│  └────────────────────────────┘    │
│                                    │
│                  [应用]  [确定]    │
└────────────────────────────────────┘
```

**入口**：菜单 `工具` → `设置...` 或 `Ctrl+,`

### C.5 测试

`tests/unit/test_theme_manager.py`：

| 测试 | 验证内容 |
|---|---|
| `test_default_dark` | 默认主题是 dark |
| `test_apply_light` | 切换到 light 后 Palette 与 QSS 同步 |
| `test_invalid_theme_fallback` | 无效名 → 回退默认 |
| `test_persistence` | 切换后 config.yaml 写入新值 |
| `test_palette_completeness` | 所有 Palette 必须含全部字段 |

QSS 模板渲染单独测试：渲染 `dark.qss` 不能包含未替换的 `{{ }}` 占位符。

---

## 五、依赖与配置变更

### 依赖

**无新增 pip 包**。Jinja2 已有，无需新装。

### 配置 (`config.yaml`)

新增字段：

```yaml
app:
  theme: dark              # dark | light | warm（C 模块）
  language: zh-CN          # 已有

reading:
  idle_timeout_minutes: 5      # A 模块新增
  flush_interval_seconds: 30   # A 模块新增
```

`DEFAULT_CONFIG` 同步更新（`src/core/config.py`）。

---

## 六、施工顺序与里程碑

```
Day 1 ─ Day 1.5   模块 A — ReadingTracker + main_window 接入 + 测试 + commit
Day 1.5 ─ Day 3   模块 B — DashboardDialog UI + 数据接入 + commit
Day 3 ─ Day 5     模块 C — Palette + ThemeManager + QSS 三套 + 13 文件重构 + SettingsDialog + commit
```

### 里程碑

- **M5.R2.1** — 模块 A 合入：阅读 → 关闭，能在 `reading_sessions.json` 看到记录
- **M5.R2.2** — 模块 B 合入：`Ctrl+D` 弹出仪表盘，热力图数据来源真实
- **M5.R2.3** — 模块 C 合入：设置弹窗切换主题 → 应用立即换色，三套主题视觉一致

每个里程碑独立 commit + push，不打包提交。

---

## 七、风险与对策

| 风险 | 概率 | 对策 |
|---|---|---|
| 主题重构遗漏样式 → 部分 widget 颜色不变 | 高 | 用对照清单逐个文件验证；先在 dark 上跑通保留视觉一致，再扩展到 light/warm |
| QSS 选择器优先级与内联样式冲突 | 中 | 删除内联样式优先；保留的必须用 `!important` 或 widget-specific 选择器 |
| QGraphicsItem 颜色无法热切换 | 中 | `ThemeManager.theme_changed` 信号 → page_canvas/graph_canvas 监听，调用 `_redraw_*` |
| ReadingTracker 高频翻页 IO | 中 | 30s 防抖落盘；session 在内存维护，end_session 时一次性写入 |
| 跨午夜会话统计错位 | 低 | A.2 设计已说明：连续运行时按天切分；离散运行时 streak 看 start_time |
| 闲置 timer 与用户实际操作误判 | 低 | 5 分钟阈值偏保守；快捷键/翻页/Claude 交互都视为活跃 |
| 仪表盘 SQL-like 查询性能 | 低 | `reading_sessions.json` 量级有限（个人使用），全量加载内存过滤足够 |

---

## 八、验收清单

R2 完成的判定标准：

### 功能

- [ ] 打开书 → 自动开始 session；关闭书/关闭应用 → session 落盘
- [ ] 翻页 30s 后 `reading_sessions.json` 出现新条目
- [ ] 闲置 5 分钟无操作 → session 自动结束
- [ ] 状态栏 streak 显示连续阅读天数
- [ ] `Ctrl+D` 打开仪表盘，4 张卡片数字与实际操作一致
- [ ] 仪表盘热力图反映本周时长分布
- [ ] 仪表盘最近阅读列表点击可跳转打开书
- [ ] 设置弹窗切换主题立即生效（无需重启）
- [ ] 三套主题（dark/light/warm）下所有面板颜色协调
- [ ] PDF 高亮颜色随主题切换更新
- [ ] 知识图谱节点色随主题切换更新

### 工程

- [ ] `pytest tests/` 全绿；R2 新增测试 ≥ 15 个
- [ ] `ruff check src/ tests/` 全清
- [ ] 主题切换无内存泄漏（多次切换内存稳定）
- [ ] config.yaml 新字段有 DEFAULT 值，向后兼容老配置
- [ ] 文档：`docs/phase5-enhancement-log.md` 追加 R2 完成记录

### 文档

- [ ] `README.md` 更新键盘快捷键表加入 `Ctrl+D`
- [ ] `README.md` 主题章节说明三种主题切换方式
- [ ] `docs/phase5-r2-plan.md`（本文档）标记为已完成

---

## 附录 A：参考代码片段

### A.1 ReadingTracker 闲置检测

```python
class ReadingTracker(QObject):
    def __init__(self, storage, config, parent=None):
        super().__init__(parent)
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(60_000)  # 每分钟 tick
        self._idle_timer.timeout.connect(self._check_idle)
        self._last_activity_ts = 0.0
        self._idle_threshold = config.get("reading", "idle_timeout_minutes", default=5) * 60

    def _check_idle(self) -> None:
        if not self._active:
            return
        if time.time() - self._last_activity_ts > self._idle_threshold:
            self.end_session()
```

### A.2 Palette 用法示例（graph_canvas.py）

```python
class GraphCanvas(QGraphicsView):
    def __init__(self, ..., theme_manager: ThemeManager):
        super().__init__(...)
        self._theme = theme_manager
        self._theme.theme_changed.connect(self._on_theme_changed)
        self._apply_palette()

    def _apply_palette(self):
        p = self._theme.palette()
        self.setBackgroundBrush(QColor(p.bg_secondary))
        # 节点重绘
        for node in self._nodes:
            node.setBrush(QBrush(QColor(p.bg_tertiary)))
            node.setPen(QPen(QColor(p.accent), 2))
```

### A.3 SettingsDialog 主题预览

```python
def _on_theme_changed(self, name: str) -> None:
    # 预览：临时应用主题但不保存
    self._theme_manager.apply(name)
    # 用户点"确定"才持久化到 config
    self._pending_theme = name

def _on_accept(self) -> None:
    self._config.set("app", "theme", value=self._pending_theme)
    self._config.save()
    self.accept()
```
