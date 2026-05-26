# Phase 5: 功能增强与问题修复记录

## 概述

本阶段主要完成了阅读体验增强、Claude 集成改进、笔记系统完善以及图书管理基础功能的 bug 修复。

---

## 一、阅读器核心改进

### 1.1 文本选择交互优化

**问题**: 选中文字后操作菜单出现在页面左上角标签位置，用户需要移动鼠标到远处才能点击。

**修复**: 菜单直接在鼠标释放位置弹出（使用 `QCursor.pos()`）。

**文件**: `src/ui/reading_view.py`

### 1.2 缩放比例不再被面板拖动重置

**问题**: 用户手动缩放后，拖动分割面板或调整窗口大小会触发自动适应宽度，丢失用户设置的缩放。

**修复**: 引入 `_user_set_zoom` 标志。手动缩放（Ctrl+滚轮、zoom_in/out）后标记为 True，此后 resize 只重新居中页面不改变缩放比例。`fit_width()`/`fit_page()` 会重置此标志。

**文件**: `src/ui/widgets/page_canvas.py`

---

## 二、模型选择功能

**需求**: 支持用户切换 Claude 模型（通过 `claude --model` 参数）。

**实现**:
- `config.yaml` 新增 `claude.model`（当前选中）和 `claude.available_models`（可选列表）
- `ClaudeClient._build_args()` 接受 `model` 参数，非空时追加 `--model`
- `ClaudeAgent` 和 `ClaudeAgentManager` 透传 model 参数，提供 `set_model()` 方法
- Claude 面板 header 新增 QComboBox 下拉框，切换后保存配置并更新所有 Agent

**文件**:
- `src/core/config.py` — DEFAULT_CONFIG 新增字段
- `src/claude/claude_client.py` — `_build_args(model)`
- `src/claude/claude_agent.py` — 构造函数、`set_model()`、`set_model_all()`
- `src/ui/claude_panel.py` — 模型下拉框 UI

---

## 三、笔记系统增强

### 3.1 笔记标题自动生成

**需求**: 保存 Claude 回复为笔记时，自动生成简短标题。

**实现**:
- `Note` 模型新增 `title: str` 字段
- 新增 `TitleGenerator` 类（独立 QProcess，不走 Agent 历史）
- 保存笔记后立即触发标题生成，完成后更新笔记并刷新列表
- 支持右键"编辑标题"（QInputDialog）和"AI优化标题"
- 双击编辑时上方显示标题输入行

**文件**:
- `src/notes/models.py` — 新增 `title` 字段
- `src/claude/claude_client.py` — 新增 `TitleGenerator` 类
- `src/ui/notes_panel.py` — 标题显示、编辑 UI
- `src/ui/main_window.py` — 信号连接、`_on_title_generated`

### 3.2 笔记高亮持久化

**问题**: 之前尝试用文本匹配方式在 PDF 页面上重绘高亮，但 PDF 分词与存储文本不一致导致匹配失败。

**修复**: 改为存储 PDF 坐标矩形。

- `Note` 模型新增 `highlight_rects: list[list[float]]`（`[[x0,y0,x1,y1], ...]`）
- `PageCanvas._extract_text_between_points()` 返回第三个值 `pdf_rects`
- `_finish_selection()` 和 `_select_word_at()` 保存 `_sel_pdf_rects`
- 创建笔记时 PDF rects 一并保存
- 打开书籍 / 页面滚动时从笔记数据恢复高亮
- Claude 回复存笔记时也保存对应选中文字的 rects

**关键修改**:
- `src/ui/widgets/page_canvas.py` — `set_note_highlights()`、`_redraw_note_highlights()`
- `src/ui/reading_view.py` — `create_note` 信号增加 `pdf_rects` 参数
- `src/ui/claude_panel.py` — `_pending_pdf_rects` 透传
- `src/ui/main_window.py` — `_sync_note_highlights()`

### 3.3 笔记 Markdown 阅览弹窗

**需求**: 右键笔记可弹窗查看完整渲染效果。

**实现**:
- 使用 `QWebEngineView` + KaTeX CDN 渲染 Markdown + 数学公式
- 如果 PyQt6-WebEngine 不可用则 fallback 到 QTextBrowser
- `app.py` 顶部预导入 `QtWebEngineWidgets` 避免 Qt 初始化顺序问题

**数学公式修复**: markdown2 会将 `$` 内的 `_` 解释为斜体标记。修复方法：渲染前用正则提取所有 `$$...$$` 和 `$...$` 块替换为占位符，markdown 处理后再还原。

**Claude prompt 约束**: 要求模型输出标准 LaTeX（下标用 `_{}` 包裹）。

**文件**:
- `src/ui/notes_panel.py` — `_show_note_preview()`
- `src/app.py` — WebEngine 预导入
- `src/claude/claude_client.py` — prompt 末尾公式格式要求
- `requirements.txt` — 新增 `PyQt6-WebEngine`

### 3.4 高亮区域右键菜单

**需求**: 鼠标移到已高亮区域后右键可操作对应笔记。

**实现**:
- `PageCanvas.contextMenuEvent()` 检测右键是否在 `_note_highlight_items` 上
- 命中时发射 `note_highlight_right_clicked(page, global_pos)` 信号
- MainWindow 弹出菜单，列出该页所有有高亮的笔记，每条有"阅览/编辑/删除"子选项

**文件**:
- `src/ui/widgets/page_canvas.py` — 信号 + contextMenuEvent
- `src/ui/main_window.py` — `_on_note_highlight_menu()`

---

## 四、图书管理 Bug 修复

### 4.1 标签无法分配给书籍（核心缺陷）

**问题**: BookInfoDialog 没有标签 UI，`book.tags` 永远为空，标签过滤形同虚设。

**修复**:
- BookInfoDialog 添加标签多选复选框（显示颜色，勾选状态）
- `_save()` 中将勾选的标签 ID 写入 `book.tags`
- 书籍右键菜单新增"标签"子菜单，可直接勾选/取消标签

**文件**: `src/ui/dialogs/book_info.py`、`src/ui/library_panel.py`

### 4.2 分类层级缩进错误

**问题**: `get_category_flat()` 返回的列表没有深度信息，缩进只区分"有/无父级"。

**修复**: `get_category_flat()` 返回 `list[tuple[Category, int]]`，各调用处按 `depth` 计算缩进。

**文件**: `src/core/library.py`、`src/ui/dialogs/book_info.py`、`src/ui/dialogs/add_category.py`

### 4.3 分类过滤不包含子分类

**问题**: 选中父分类时只显示直属书籍，不显示子分类下的书。

**修复**: 新增 `_collect_category_ids(cat_id)` 递归收集所有后代分类 ID，过滤时用集合匹配。

**文件**: `src/ui/library_panel.py`

### 4.4 标签按钮互斥逻辑缺失

**问题**: 多个标签按钮可同时处于选中状态，但过滤只取最后一个。

**修复**: 点击标签时遍历所有标签按钮，取消其他的选中状态（通过 `tag_id` property 识别）。

**文件**: `src/ui/library_panel.py`

### 4.5 书籍右键菜单功能不足

**问题**: 只有"打开/信息/移除"三个选项，无法快速管理标签和分类。

**修复**: 新增"标签"子菜单（带勾选状态）和"分类"子菜单（单选），修改后立即刷新列表。

**文件**: `src/ui/library_panel.py`

---

## 五、依赖变更

| 包 | 版本 | 用途 |
|----|------|------|
| PyQt6-WebEngine | >=6.5.0 | 笔记 Markdown + 数学公式渲染 |

---

## 六、配置变更

`config.yaml` 新增：
```yaml
claude:
  model: ""                    # 当前选中模型（空=CLI默认）
  available_models:            # 下拉框可选项
    - sonnet
    - opus
    - haiku
    - claude-sonnet-4-6
    - claude-opus-4-7
    - claude-haiku-4-5-20251001
```

---

## 七、经验总结

1. **PDF 文本匹配不可靠** — PyMuPDF 的 word 分割与用户视觉上的"词"不一致（尤其中文），应存储坐标而非文本匹配。
2. **Markdown + LaTeX 冲突** — markdown 引擎会破坏 `$` 内的 `_`，必须先提取数学块再处理。
3. **Qt WebEngine 初始化顺序** — 必须在 QApplication 创建前导入，否则运行时报错。
4. **UI 功能应闭环验证** — 标签系统有创建、有过滤、有模型字段，但缺少"分配"环节导致整个功能链断裂。实现功能时应端到端走通一遍。

---

## 八、Phase 5 原计划任务排期（2026-05-25 启动）

> 上文一至七记录的是日常增强，PROJECT_PLAN 第 15 节定义的 Phase 5 任务尚未启动。本节为正式排期。

### 总体进度

| # | 任务 | 优先级 | 状态 |
|---|---|---|---|
| 1 | 单元测试 | P1 | 🚧 进行中 (R1) |
| 2 | 异常处理与日志 | P1 | ⬜ 未开始 (R1) |
| 3 | 性能优化 | P1 | ⬜ 未开始 (R1) |
| 4 | 阅读统计 + 仪表盘 | P1 | ⬜ 未开始 (R2) |
| 5 | 主题系统 | P1 | ⬜ 未开始 (R2) |
| 6 | 翻译功能 | P2 | ✅ 已完成（reading_view.py） |
| 7 | 思维导图 | P2 | ⬜ 未开始 (R3) |
| 8 | PyInstaller 打包 | P2 | ⬜ 未开始 (R3) |
| 9 | 文档（README/手册） | P2 | ✅ README 已完成 |

### 关键决策

- **测试框架**：pytest + pytest-cov
- **测试 PDF**：reportlab 脚本生成（不入库真实 PDF）
- **代码检查**：引入 ruff（提示性，不卡 CI）
- **主题系统**：三套（暗/亮/暖）+ 抽离内联 stylesheet 重构
- **打包目标**：Windows 优先，macOS/Linux 后续考虑

### R1 交付边界

R1（测试 + 异常处理 + 性能基线）作为独立提交点，完成后才进入 R2。完成标准：
- `pytest tests/` 全绿
- 核心模块覆盖率 ≥ 70%
- 全局异常钩子接入，日志按天滚动
- 大 PDF 性能基线记录到 `docs/perf-baseline.md`

---

## 九、R2 后续功能增强（2026-05-26）

> R2 主体（阅读统计 + 仪表盘 + 主题系统）已合入 `87cfab7`。本节记录 R2 之后追加的三项功能。

### 9.1 护眼模式

**功能**：在 PDF 渲染结果上叠加暖色滤镜（羊皮卷质感）+ 用户可调亮度（50%-150%）。

**实现**：
- `page_canvas.py` 新增 `_apply_eye_filter(pixmap)` — 使用 `QPainter.CompositionMode_Multiply` 叠加 `#F5EBD2` 暖色层；亮度通过半透明黑/白层实现
- `reading_toolbar.py` 新增"🌙 护眼"切换按钮 + 亮度 QSlider
- 切换时调用 `_refresh_pages()` 清除已渲染页面并重新渲染

**文件**：`page_canvas.py`, `reading_toolbar.py`, `reading_view.py`

### 9.2 笔记内容追问

**功能**：用户可对已有笔记内容向 Claude 追问，回答自动追加到笔记末尾。

**实现**：
- `notes_panel.py` 右键菜单新增"追问"选项 → 弹出 `QInputDialog` 输入问题
- 发射 `followup_requested(note_id, question)` 信号
- `main_window.py` 接收信号，通过 `ClaudeAgent.send_note_followup()` 发送
- 回答追加格式：`\n\n---\n**追问**: question\n**回答**: response`

**文件**：`notes_panel.py`, `main_window.py`, `claude_agent.py`, `context_builder.py`

### 9.3 全书预览总结

**功能**：在开始阅读前，让 Claude 对全书各章节进行总结分析，结果作为后续提问的上下文。

**实现**：
- `library_panel.py` 右键菜单新增"🤖 AI 全书预览总结"
- 确认对话框提醒 token 消耗后，打开 `BookPreviewDialog` 流式弹窗
- 提取各章节文本样本（有 TOC 取章节首 2 页，无 TOC 等间隔采样），限制 30K 字符
- 结果实时流式显示（`response_chunk` 信号），完成后保存到 `books/{id}/book_preview.json`
- 打开书时自动加载 preview 注入 `ClaudeAgent` 上下文（`set_book_preview`）

**输出结构**：全书概述 → 各章节总结 → 知识体系 → 阅读建议 → 阅读目标

**文件**：`book_preview.py`(新增), `library_panel.py`, `main_window.py`, `claude_agent.py`
