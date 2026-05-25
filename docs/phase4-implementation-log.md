# Phase 4 施工记录：笔记系统 + 知识图谱 + Obsidian 导出

> 日期：2026-05-25
> 状态：已完成

---

## 一、概述

Phase 4 实现了从「阅读笔记」到「知识图谱」到「Obsidian 仓库导出」的完整知识管理链路。核心功能：

1. **笔记系统**：选中文字创建笔记、手动新建笔记、Claude 回复存笔记，单击笔记跳转对应页
2. **Claude 笔记优化**：4 种风格（精炼/结构化/扩展/批判性），右键菜单触发
3. **概念提取**：Claude 分析笔记内容 → 返回 JSON → 解析去重 → 存入知识图谱
4. **知识图谱可视化**：NetworkX 力导向布局 + QGraphicsView 渲染，支持拖拽/缩放
5. **Obsidian 导出**：Jinja2 模板渲染，生成 Books/ + Concepts/ + _MOCs/ 目录结构

---

## 二、新增文件

### 笔记层 (`src/notes/`)

| 文件 | 职责 |
|---|---|
| `src/notes/models.py` | `Note` 数据类：id, book_id, note_type, page, chapter, content, highlighted_text, tags, optimized_content 等字段 |
| `src/notes/note_manager.py` | `NoteManager`：CRUD + 过滤查询（按页/按章/全局/高亮），存储在 `books/{book_id}/notes.json` |
| `src/notes/obsidian_exporter.py` | `ObsidianExporter`：Jinja2 模板渲染，增量同步（内容比对），生成 vault 目录结构；`ExportResult` 统计类 |

### 知识图谱层 (`src/knowledge/`)

| 文件 | 职责 |
|---|---|
| `src/knowledge/models.py` | `Concept`（节点）+ `ConceptLink`（边）数据类，支持 aliases、source_books、relation_type |
| `src/knowledge/graph_engine.py` | `GraphEngine`：NetworkX 图封装，CRUD、按名称/别名去重合并、邻居查询、布局计算（spring/kamada_kawai/shell） |
| `src/knowledge/concept_extractor.py` | `ConceptExtractor`：解析 Claude 返回的 JSON（支持 markdown code fence），去重后批量入库 |

### UI 层

| 文件 | 职责 |
|---|---|
| `src/ui/notes_panel.py` | 右侧笔记面板：全部笔记列表（按页排序）、当前页高亮、内联编辑器、"提取概念"按钮、右键优化菜单、单击跳转页码 |
| `src/ui/widgets/graph_canvas.py` | `GraphCanvas`（QGraphicsView）：节点拖拽、滚轮缩放、双击选中；`GraphDialog`：独立弹窗展示图谱 |

### Obsidian 模板 (`resources/templates/obsidian/`)

| 文件 | 用途 |
|---|---|
| `book-note.md.j2` | 书籍笔记页（frontmatter + 进度 + 笔记列表 + 相关概念） |
| `concept.md.j2` | 概念页（aliases + 相关概念 [[双链]] + 来源书籍） |
| `moc.md.j2` | 知识地图 Map of Content（书籍列表 + 概念索引） |

---

## 三、修改文件

| 文件 | 变更 |
|---|---|
| `src/notes/__init__.py` | 导出 Note, NoteManager, ObsidianExporter, ExportResult |
| `src/knowledge/__init__.py` | 导出 Concept, ConceptLink, GraphEngine, ConceptExtractor |
| `src/core/storage.py` | `_default_for()` 添加 `"notes.json": []` 默认值 |
| `src/claude/context_builder.py` | 新增 `build_note_optimization()` 和 `build_concept_extraction()` 方法 |
| `src/claude/claude_agent.py` | 新增 `send_note_optimization(notes, style)` 和 `send_concept_extraction(notes_content)` 便捷方法 |
| `src/claude/claude_client.py` | `_build_prompt()` 添加 optimize_notes / extract_concepts 两种 action 的 prompt 构建逻辑 |
| `src/ui/reading_view.py` | 浮动菜单新增「📝 笔记」选项；新增 `create_note` 信号和 `_on_create_note()` 槽 |
| `src/ui/claude_panel.py` | 新增 `save_to_notes_requested` 信号，连接 TerminalWidget 的 `save_to_notes` 信号 |
| `src/ui/main_window.py` | 右侧改为 QTabWidget（书签+笔记）；新增"工具"菜单（导出Obsidian Ctrl+E / 知识图谱 Ctrl+Shift+K）；新增 `_on_create_note` / `_on_optimize_note` / `_on_extract_concepts` / `_on_save_claude_to_notes` / `_on_export_obsidian` / `_on_show_graph` 等槽；概念提取完整反馈链路（loading → 成功弹窗 → 错误弹窗） |
| `src/app.py` | 传递 `library.storage` 给 MainWindow |
| `requirements.txt` | 新增 `numpy>=1.24.0`（NetworkX 布局依赖） |

---

## 四、架构设计

### 数据流

```
选中文字 → "📝 笔记" → Note(page=实际页码) → notes.json
                                    ↓
Claude 回复 → "存笔记" → Note(page=当前页码) → notes.json
                                    ↓
笔记面板 → "🧠 提取概念" → Claude → JSON → ConceptExtractor
                                              ↓
                                    GraphEngine.add_concept() → concepts.json
                                    GraphEngine.add_link()    → concept_links.json
                                              ↓
                                    GraphCanvas (QGraphicsView) 可视化
                                              ↓
                        ObsidianExporter → vault/Books/ + vault/Concepts/ + vault/_MOCs/
```

### 右侧面板布局

```
┌─────────────────────┐
│ QTabWidget          │
├─────────────────────┤
│ [🔖 书签] [📝 笔记] │  ← Tab 切换
├─────────────────────┤
│ 📝 笔记    [+ 新建] │  ← Header
├─────────────────────┤
│ ── 当前页 (P12) ──  │  ← Section header
│ 📌 [P12] 内容预览.. │  ← 单击跳转
│ 🖍️ [P12] 高亮文字.. │
│ ── 全部笔记 ──      │
│ 📌 [P3] 早期笔记..  │
│ 📌 [P8] 另一条...   │
├─────────────────────┤
│ [🧠 提取概念]       │  ← Action bar
├─────────────────────┤
│ ┌─────────────────┐ │  ← 编辑器（点+或双击时展开）
│ │ 输入笔记内容... │ │
│ └─────────────────┘ │
│        [保存] [取消] │
└─────────────────────┘
```

### 知识图谱弹窗

```
┌──────────────────────────────────────┐
│ 概念图谱 — abc12345    [刷新布局] [关闭] │
├──────────────────────────────────────┤
│                                      │
│      ┌────┐         ┌─────┐         │
│      │概念A│────────│概念B │         │
│      └────┘         └──┬──┘         │
│         \              │            │
│          \         ┌───┴──┐         │
│           └───────│概念C  │         │
│                    └──────┘         │
│                                      │
│  (拖拽节点 / 滚轮缩放 / 双击选中)     │
└──────────────────────────────────────┘
```

---

## 五、问题与修复

| 问题 | 原因 | 修复 |
|---|---|---|
| "存笔记"按钮点击无反馈 | `TerminalWidget.save_to_notes` 信号未连接到任何槽 | `ClaudePanel` 新增 `save_to_notes_requested` 信号转发，`MainWindow` 连接并实现 `_on_save_claude_to_notes` |
| 笔记面板布局异常 | 编辑器按钮容器无固定高度，全局样式干扰 | 设置 `setFixedHeight(30)`、`setContentsMargins(0,0,0,0)`、面板 `setMinimumWidth(200)` |
| 知识图谱空白无提示 | 无概念数据时 `show_graph()` 直接 return | 改为显示灰色提示文字"暂无概念数据" |
| Obsidian 导出无反馈 | 仅写 statusbar 消息（可能被遮挡） | 改用 `QMessageBox.information` 弹窗 + try/except 错误处理 |
| "概念提取"按钮不可见 | 40px 小按钮在 header 中，颜色与背景接近 | 移到列表下方作为全宽 action bar，带边框和 tooltip |
| 笔记跳转页码不准 | "+"新建笔记使用缓存的 `_current_page`，可能过时 | 新增 `set_live_page_getter()` 回调，创建笔记时直接读取 `canvas.current_page` |
| 笔记列表只显示当前页 | 设计为按页/章/全局分区，其他页笔记不可见 | 改为显示全部笔记（当前页置顶，其余按页码排序） |
| `ModuleNotFoundError: numpy` | NetworkX `spring_layout` 依赖 numpy | `pip install numpy`，添加到 requirements.txt |

---

## 六、新增快捷键

| 快捷键 | 功能 |
|---|---|
| `Ctrl+E` | 导出到 Obsidian |
| `Ctrl+Shift+K` | 打开知识图谱 |

---

## 七、依赖变更

| 包 | 版本 | 用途 |
|---|---|---|
| `numpy` | >=1.24.0 | NetworkX 布局算法依赖 |

其余依赖（networkx, jinja2, pyyaml）在 Phase 1 已安装，Phase 4 首次实际使用。

---

## 八、Phase 5 预览

根据 `PROJECT_PLAN.md`，Phase 5 包含：

- 阅读统计 + 仪表盘（时长/页数/速度/连续天数）
- 主题系统（亮色/暗色/暖色 QSS）
- 翻译功能（选中文字 → Claude 翻译）
- 思维导图生成（Mermaid 语法）
- 性能优化（大 PDF 加载）
- 单元测试
- PyInstaller 打包
