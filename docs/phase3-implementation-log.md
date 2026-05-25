# Phase 3 施工记录：Claude Code 集成

> 日期：2026-05-25
> 状态：已完成

---

## 一、概述

Phase 3 实现了 Claude Code 的完整集成，打通了「选中文字 → 问 Claude → 流式回复」的核心交互闭环。施工过程中遭遇并解决了三个关键平台问题：

1. **Windows 命令调用**：`claude` 是 `.cmd` 脚本，`QProcess` 直接调用失败，需通过 `cmd /c` 转发
2. **stream-json 格式**：`--output-format stream-json` 必须配合 `--verbose` 才能正常输出
3. **命令行编码/截断**：多行中文 prompt 通过命令行参数传递时被 Windows shell 截断，改为写入临时文件通过 stdin 传入

---

## 二、新增文件

### 后端：Claude 集成层 (`src/claude/`)

| 文件 | 职责 |
|---|---|
| `src/claude/prompt_templates.py` | 9 种场景的 Prompt 模板（explain_text / chapter_analysis / reading_plan / reading_outline / optimize_notes / extract_concepts / analyze_screenshot / translate / general_qa）及 `render()` 渲染函数 |
| `src/claude/context_builder.py` | 上下文数据类（`BookContext` / `InteractionContext` / `ClaudeContext`）及 `ContextBuilder`，负责构建各类交互上下文对象，写入临时 JSON 文件 |
| `src/claude/claude_client.py` | `ClaudeClient`：通过 `QProcess` 启动 `claude -p -` 子进程，prompt 写入临时文件通过 stdin 传入，解析 `stream-json` 流式输出，发射 `response_chunk` / `response_finished` / `error_occurred` 信号 |
| `src/claude/claude_agent.py` | `ClaudeAgent`：与单本书绑定，维护对话历史（最多 40 条），封装各类发送方法（文字问答 / 截图问答 / 章节分析 / 自由问答）；`ClaudeAgentManager`：管理所有书籍的 Agent 实例，限制最多 3 个并发 |

### UI 层

| 文件 | 职责 |
|---|---|
| `src/ui/widgets/terminal_widget.py` | 聊天终端组件：消息列表驱动的重绘机制（user / assistant / thinking / error 四种气泡），Markdown 渲染（markdown2），Ctrl+Enter 发送，"存笔记"按钮 |
| `src/ui/widgets/screenshot_tool.py` | 全屏透明覆盖层截图工具：`QRubberBand` 框选，截图保存为 PNG 临时文件，Esc 取消 |
| `src/ui/claude_panel.py` | 底部 Claude 交互面板：上下文预览条（显示选中文字或截图路径）+ `TerminalWidget` + 章节分析 / 截图 / 清空按钮，管理 Agent 信号连接与断开 |

### Skill 定义

| 文件 | 职责 |
|---|---|
| `skills/book-reader.md` | Claude Code Skill 定义（保留备用） |
| `.claude/skills/book-reader.md` | 同上，注册到项目级 skill 目录 |

---

## 三、修改文件

| 文件 | 变更 |
|---|---|
| `src/claude/__init__.py` | 导出所有公共类 |
| `src/ui/reading_view.py` | 新增 `ask_claude` 信号；新增 `_selected_text` / `_selected_page` 状态；`_on_text_selected` 改为选中后立即弹出浮动菜单（问Claude / 复制 / 翻译）；新增 `_show_selection_menu()` / `_on_ask_claude()` / `_on_copy_selection()` / `_on_translate()` |
| `src/ui/main_window.py` | 引入 `ClaudeAgentManager` / `BookContext` / `ClaudePanel` / `ScreenshotTool`；`_setup_ui()` 改为垂直分割器（上方主区域 + 下方 Claude 面板 220px）；`_on_book_opened()` 初始化 Agent；`_on_book_closed()` 关闭 Agent；`_on_page_changed()` 同步页码到 Agent；新增 `_on_ask_claude()` / `_on_screenshot()` / `_on_screenshot_taken()` / `_toggle_claude_panel()` 槽；新增 Ctrl+Shift+S（截图）/ Ctrl+Shift+A（切换 Claude 面板）快捷键 |

---

## 四、架构设计

### 信号流

```
用户选中文字
  │
  ▼
PageCanvas.text_selected(text, page)
  │
  ▼
ReadingView._on_text_selected()
  ├── 显示选中预览条
  ├── 弹出浮动菜单
  └── emit ask_claude(text, page)  ← 用户点击"问 Claude"后
        │
        ▼
MainWindow._on_ask_claude()
  └── ClaudePanel.set_text_selection(text, page)
        │
        ▼
用户在终端输入问题 → TerminalWidget.message_submitted(text)
  │
  ▼
ClaudePanel._on_message_submitted()
  └── ClaudeAgent.send_text_question(...)
        │
        ▼
ClaudeClient.invoke(ctx)
  └── QProcess: cmd /c claude -p - --output-format stream-json --verbose
        stdin ← prompt 临时文件 (UTF-8)
        │
        ▼
_on_stdout() → _parse_stream_line() → response_chunk.emit(chunk)
        │
        ▼
TerminalWidget.append_assistant_chunk()
        │
        ▼
_on_finished() → response_finished.emit(full_text)
        │
        ▼
TerminalWidget.finish_assistant_stream(full_text)  ← Markdown 渲染
```

### 主窗口布局（Phase 3 后）

```
MainWindow
├── QSplitter (Vertical)
│   ├── QSplitter (Horizontal)  ← 上方主区域
│   │   ├── LibraryPanel (左, 260px)
│   │   ├── ReadingView (中, stretch)
│   │   │   ├── ReadingToolbar
│   │   │   ├── SelectionLabel (选中预览条)
│   │   │   └── PageCanvas
│   │   └── BookmarkWidget (右, 220px)
│   └── ClaudePanel (下, 220px, 可拖拽调整)
│       ├── 标题栏 (书名 / 截图 / 章节分析 / 清空)
│       ├── ContextPreview (上下文预览条, 条件显示)
│       └── TerminalWidget (聊天气泡 + 输入框)
└── ReaderStatusBar
```

### ClaudeClient 调用方式

```
prompt 文本 (UTF-8)
  │
  ▼
写入临时文件 ~/.../claude-book-reader/prompts/prompt-{id}.txt
  │
  ▼
QProcess.setStandardInputFile(path)
  │
  ▼
cmd /c claude -p - --output-format stream-json --verbose
  │
  ▼
stdout: 逐行 JSON 对象
  {"type":"system", ...}          ← 忽略
  {"type":"assistant", "message": {"content": [{"type":"text","text":"..."}]}}  ← 提取
  {"type":"result", "result":"..."}  ← 提取（完整响应）
```

### TerminalWidget 消息渲染机制

```
_messages: list[dict]  ← 消息列表（role: user|assistant|thinking|error）
  │
  ├── append_user()        → 追加 user 消息 → _redraw()
  ├── begin_assistant_stream() → 追加 thinking 占位 → _redraw()
  ├── append_assistant_chunk() → 累积到 _last_assistant_text（不重绘）
  └── finish_assistant_stream() → 替换 thinking → assistant → _redraw()
                                   └── markdown2 渲染 Markdown → HTML
```

重绘时 `setHtml()` 整个文档，确保"正在思考"占位符被正确替换，不会残留。

---

## 五、问题与修复记录

### 问题 1：`Book` 对象无 `total_pages` 属性

**根因**：`Book` dataclass 中字段名为 `pages`，不是 `total_pages`。

**修复**：`main_window.py` 中 `BookContext` 初始化改为 `total_pages=book.pages`。

---

### 问题 2：`QAction` 导入路径错误

**根因**：PyQt6 中 `QAction` 属于 `QtGui`，不在 `QtWidgets`。

**修复**：`reading_view.py` 中改为 `from PyQt6.QtGui import QAction`。

---

### 问题 3：`Unknown command: /book-reader`

**根因**：Claude Code 自定义命令需放在 `.claude/commands/`，而非 `.claude/skills/`。且 `-p` 模式下 skill 调用方式与交互模式不同。

**修复**：放弃自定义命令方式，改为直接将上下文内容构建为 prompt 文本，通过 `_build_prompt()` 序列化后传给 claude，无需任何命令注册。

---

### 问题 4：`stdin` 等待警告（3 秒延迟）

**现象**：`Warning: no stdin data received in 3s, proceeding without it.`

**根因**：`QProcess` 启动后 stdin 管道保持打开，claude CLI 等待 stdin 输入 3 秒后才继续。

**修复**：启动后立即调用 `self._process.closeWriteChannel()`（后续改为 stdin 文件重定向后此问题自然消失）。

---

### 问题 5：回复内容为空（核心问题）

**根因**：`_build_prompt()` 生成的 prompt 包含换行符和中文，通过 `cmd /c claude -p "..."` 命令行参数传递时，Windows shell 在换行处截断，claude 收到空内容，返回空响应，`_full_response` 为空，`finish_assistant_stream("")` 被调用，"正在思考"消失但无回复显示。

**修复**：
1. 将 prompt 写入 UTF-8 临时文件（`~/.../claude-book-reader/prompts/prompt-{id}.txt`）
2. 使用 `QProcess.setStandardInputFile(path)` 重定向 stdin
3. 改用 `claude -p -`（从 stdin 读取 prompt）
4. 彻底绕开命令行长度限制和编码问题

---

### 问题 6：`claude_client.py` 重复定义导致 `NameError`

**根因**：多次 Edit 操作后文件中存在两份 `_build_prompt` 和 `ClaudeClient` 定义，旧版本引用了已删除的 `_build_command` 函数。

**修复**：用 `Write` 工具完整重写文件，消除重复定义。

---

### 问题 7："正在思考"占位符残留

**根因**：`TerminalWidget` 原实现用 `browser.append()` 追加新气泡，"正在思考"文本无法被移除。

**修复**：改为消息列表驱动的 `_redraw()` 机制，`finish_assistant_stream()` 找到最后一条 `thinking` 消息替换为 `assistant`，然后 `setHtml()` 重绘整个文档。

---

## 六、快捷键新增

| 快捷键 | 功能 |
|---|---|
| `Ctrl+Shift+S` | 截图选区 |
| `Ctrl+Shift+A` | 切换 Claude 面板显示/隐藏 |
| `Ctrl+Enter`（终端内） | 发送消息给 Claude |

---

## 七、依赖

Phase 3 无新增 pip 依赖，所有功能基于已有依赖实现：

```
PyQt6       - QProcess 子进程管理、UI 组件
markdown2   - Claude 回复的 Markdown → HTML 渲染（可选，降级为 <pre> 显示）
```

Claude Code CLI（`claude`）需已安装并在系统 PATH 中：

```
npm install -g @anthropic-ai/claude-code
```

---

## 八、后续工作（Phase 4）

Phase 4 将实现笔记系统与知识管理：

- 页面锚点笔记、全局笔记、高亮批注（PDF 内嵌）
- 笔记面板 UI（`src/ui/notes_panel.py`）
- Claude 笔记优化（精炼 / 结构化 / 扩展 / 批判性）
- Obsidian 仓库导出（`src/notes/obsidian_exporter.py`）
- 概念提取 → 知识图谱（NetworkX + QGraphicsView 可视化）
