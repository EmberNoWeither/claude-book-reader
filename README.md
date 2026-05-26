# Claude Book Reader

> 基于 PyQt6 + PyMuPDF 的 PDF 图书管理与智能阅读器，深度集成 Claude Code 实现 AI 辅助阅读、笔记优化与知识图谱构建。

## 功能概览

### 图书管理

- **PDF 导入**：自动提取元数据（标题、作者、页数、目录），支持批量导入
- **分类系统**：树形分类（学科/领域），支持父子层级，选中父分类自动包含子分类书籍
- **标签系统**：跨分类的灵活标签 + 颜色标记，支持多选过滤
- **三种浏览视图**：支持按分类过滤、标签过滤、书名/作者搜索
- **阅读状态追踪**：未读 / 阅读中 / 已读完，打开书籍和翻页自动流转
- **右键菜单**：书籍右键可快速切换标签、分类，查看/编辑书籍信息

### PDF 阅读

- **四种阅读模式**：单页连续滚动、双页连续滚动、单页翻页、双页翻页
- **虚拟渲染**：仅渲染可见页 + 3 页缓冲区，支持大 PDF 流畅阅读
- **40 页 LRU 渲染缓存**：缩放不变时避免重复渲染
- **缩放控制**：放大/缩小/适应宽度/适应页面/原始大小，支持 Ctrl+滚轮，用户缩放不会被面板拖动重置
- **文字选中**：拖拽选词，PDF 坐标精确映射，弹出浮动菜单（问 Claude / 复制 / 笔记 / 翻译 / 高亮）
- **书签系统**：添加/删除/跳转书签，自动匹配章节标题
- **中键拖拽**：平移画布
- **全文检索**：基于 Whoosh 的全文搜索引擎，支持模糊搜索，搜索结果高亮跳转
- **护眼模式**：暖色滤镜（羊皮卷质感）+ 亮度可调（50%-150%），适合长时间阅读

### Claude AI 集成

- **每书独立 Agent**：打开书籍时自动创建专属 AI 会话，维护独立对话历史（最多 40 条）
- **流式响应**：实时显示 Claude 回复（Markdown 渲染 + 代码高亮）
- **多模型支持**：通过下拉菜单在 sonnet / opus / haiku 等模型间切换
- **`--tools ""` 模式**：纯文本输出场景自动禁用 CLI 工具，避免授权提示干扰
- **交互场景**：
  - **选中文字问答**：选中文字 → 右键「问 Claude」→ AI 解释/翻译/展开
  - **截图分析**：框选屏幕区域 → AI 分析图表/公式/排版内容
  - **章节分析**：一键生成章节摘要、核心观点、关键概念、思辨问题
  - **笔记优化**：4 种优化风格（精炼/结构化/扩展/批判性）
  - **笔记追问**：对已有笔记内容向 Claude 追问，回答自动追加到笔记末尾
  - **概念提取**：从笔记中提取关键概念构建知识图谱
  - **全书预览总结**：提取各章节样本 → Claude 生成全书概述、知识体系、阅读建议
  - **交互式 HTML 讲解**：选中文字或笔记 → Claude 生成含动画/交互的 HTML 页面
  - **代码练习生成**：根据书籍内容生成练习题/示例代码/小项目/概念测验
  - **自由问答**：底部终端直接对话

### 笔记系统

- **4 种笔记类型**：页面锚点笔记、文字高亮、章节笔记、全局笔记
- **富文本预览**：QWebEngineView 渲染 Markdown + KaTeX 数学公式
- **AI 标题生成**：自动为笔记生成简洁标题（10 字以内）
- **高亮持久化**：笔记关联的 PDF 高亮区域（基于坐标）自动显示在阅读区
- **右键上下文**：高亮区域右键 → 预览/编辑/删除笔记；笔记列表右键 → 阅览/编辑/删除/追问/生成 HTML 讲解
- **笔记追问**：对已有笔记追问 Claude，回答自动追加

### 知识图谱

- **概念提取**：Claude 从笔记中提取概念及关系（JSON 结构化输出）
- **自动去重合并**：同名概念自动合并，别名校验
- **可视化**：NetworkX 多种布局算法（spring / kamada_kawai / shell）+ QGraphicsView 交互式画布
- **关系类型**：IS_A / RELATED_TO / PART_OF / LEADS_TO / APPLIES_TO
- **交互**：滚轮缩放、拖拽节点、双击展开、按书籍过滤

### Obsidian 导出

- **一键导出**：将笔记和概念导出为 Obsidian vault
- **模板渲染**：Jinja2 模板生成标准 Obsidian 笔记（YAML frontmatter + Wikilink 双链）
- **增量同步**：基于内容比较，避免重复写入
- **导出结构**：
  ```
  obsidian-vault/
  ├── Books/          # 每本书的笔记（含元数据、大纲、摘录）
  ├── Concepts/       # 每个概念的独立页面（含 [[双链]]）
  └── _MOCs/          # 知识地图汇总页
  ```

### 阅读统计与仪表盘

- **自动追踪**：打开书籍自动开始计时，关闭自动结束，支持闲置超时自动结束
- **统计指标**：今日阅读时长、今日页数、阅读速度（页/小时）、连续阅读天数
- **崩溃恢复**：启动时自动修复未正常结束的会话记录
- **仪表盘**：统计卡片 + 本周热力图 + 书库概览 + 最近阅读列表（可点击跳转）

### 主题系统

- **三套主题**：暗色（深蓝黑）、亮色（白底灰调）、暖色护眼（米黄底）
- **即时切换**：设置中切换主题立即生效，无需重启
- **全局覆盖**：QSS 模板（Jinja2 渲染）+ Palette 色板，覆盖所有 UI 组件和知识图谱/高亮颜色
- **持久化**：主题选择保存到 `config.yaml`，下次启动自动应用

### 交互式 HTML 讲解

- **生成**：选中文字或笔记 → 「生成交互讲解」→ Claude 生成单文件 HTML（动画/交互/代码示例）
- **查看**：QWebEngineView 渲染，支持完整交互
- **持久化**：自动保存到 `books/{id}/html_explanations/`，附带元数据索引
- **列表管理**：浏览所有已生成的 HTML 讲解，支持打开和删除
- **再编辑**：在查看器中点击「再编辑」→ 输入修改要求 → Claude 生成新版本

### 代码练习生成

- **四种类型**：练习题（含参考答案）、代码讲解示例、小项目实战、概念测验 + 代码验证
- **本地输出**：用户配置输出目录，每本书自动创建子文件夹
- **多文件解析**：自动解析 Claude 输出的 `=== filename: xxx ===` 格式，写入多个文件
- **持久化配置**：输出目录保存到 `config.yaml`，下次无需重新选择

---

## 安装

### 环境要求

- **Python** >= 3.10
- **Claude Code CLI**：需单独安装并配置（[安装指南](https://docs.anthropic.com/en/docs/claude-code)）
- **操作系统**：Windows / macOS / Linux

### 安装步骤

```bash
# 1. 克隆项目
git clone <repo-url>
cd claude-book-reader

# 2. 创建虚拟环境（推荐）
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装 CLI 入口（可选，安装后可直接运行 `claude-book-reader`）
pip install -e .
```

### 依赖项

| 包 | 版本 | 用途 |
|---|---|---|
| PyQt6 | >= 6.5 | GUI 框架 |
| PyQt6-WebEngine | >= 6.5 | HTML 讲解查看 / 笔记 Markdown 预览 |
| PyMuPDF | >= 1.23 | PDF 解析与渲染 |
| NetworkX | >= 3.0 | 知识图谱数据结构与布局 |
| numpy | >= 1.24 | 数值计算 |
| markdown2 | >= 2.4 | Markdown → HTML 转换 |
| Pygments | >= 2.15 | 代码高亮 |
| Pillow | >= 10.0 | 图像处理（截图） |
| PyYAML | >= 6.0 | YAML 配置读写 |
| Jinja2 | >= 3.1 | Obsidian 模板 / QSS 主题渲染 |
| Whoosh | >= 2.7 | 全文检索引擎 |

---

## 使用

### 启动应用

```bash
python main.py
# 或（如果已 pip install -e .）
claude-book-reader
```

### 基本工作流

```
导入 PDF → 选择书籍 → 开始阅读
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
    选中文字问 AI   创建笔记/高亮   截图分析
          │             │             │
          ▼             ▼             │
    Claude 回答     AI 优化笔记       │
          │             │             │
          └─────────────┼─────────────┘
                        ▼
              ┌─────────────────┐
              │ 概念提取 → 知识图谱 │
              │ HTML 讲解 / 代码练习│
              │ 导出到 Obsidian    │
              └─────────────────┘
```

### 主要功能入口

| 功能 | 入口 |
|---|---|
| 选中文字问 Claude | 拖拽选中文字 → 右键菜单「问 Claude」 |
| 截图问 Claude | `Ctrl+Shift+S` 或工具栏截图按钮 |
| 章节分析 | 工具栏「章节分析」按钮 |
| 全书预览总结 | 书库中右键书籍 →「AI 全书预览总结」 |
| 查看已保存的总结 | 打开书后 → 工具菜单「查看全书总结」 |
| 生成 HTML 交互讲解 | 选中文字/右键笔记 →「生成交互讲解」 |
| 浏览已保存的 HTML 讲解 | `Ctrl+Shift+H` 或工具菜单「交互式讲解列表」 |
| 生成代码练习 | `Ctrl+Shift+E` 或工具菜单「生成代码练习」 |
| 笔记优化 | 笔记面板选中笔记 →「优化」按钮 |
| 笔记追问 | 笔记面板右键笔记 →「追问」 |
| 概念提取 | 笔记面板「提取概念」按钮 |
| 导出 Obsidian | `Ctrl+E` 或工具菜单 |
| 知识图谱 | `Ctrl+Shift+K` 或工具菜单 |
| 阅读仪表盘 | `Ctrl+D` 或工具菜单 |
| 护眼模式 | 工具栏「护眼」按钮 + 亮度滑块 |
| 切换主题 | `Ctrl+,` → 设置 → 外观 → 主题选择 |

### 快捷键

| 快捷键 | 功能 |
|---|---|
| `Ctrl+O` | 导入 PDF |
| `Ctrl+W` | 关闭书籍 |
| `Ctrl+Q` | 退出应用 |
| `Ctrl+1/2/3/4` | 切换阅读模式（单页连续/双页连续/单页翻页/双页翻页） |
| `Ctrl+=` / `Ctrl+-` | 缩放 |
| `Ctrl+0` | 100% 原始大小 |
| `Ctrl+Shift+W` | 适应宽度 |
| `Ctrl+G` | 跳转到指定页码 |
| `Ctrl+B` | 添加书签 |
| `Ctrl+N` | 新建笔记 |
| `Ctrl+D` | 阅读仪表盘 |
| `Ctrl+Shift+S` | 截图选区（发给 Claude 分析） |
| `Ctrl+Return` | 发送消息给 Claude |
| `Ctrl+E` | 导出到 Obsidian |
| `Ctrl+Shift+K` | 打开知识图谱 |
| `Ctrl+Shift+H` | 交互式 HTML 讲解列表 |
| `Ctrl+Shift+E` | 生成代码练习 |
| `Ctrl+Shift+P` | 查看当前书籍的全书总结 |
| `Ctrl+Shift+L` | 切换书库面板 |
| `Ctrl+Shift+N` | 切换书签/笔记面板 |
| `Ctrl+Shift+A` | 切换 Claude 面板 |
| `Ctrl+,` | 设置 |
| `F11` | 全屏阅读 |
| `Esc` | 清除选区 / 退出截图模式 |
| `← → ↑ ↓` | 翻页/滚动 |
| `Home / End` | 跳到首页/末页 |
| `中键拖拽` | 平移画布 |
| `双击单词` | 选中该词 |

---

## 项目架构

```
claude-book-reader/
├── main.py                       # 应用入口
├── setup.py                      # 打包配置
├── requirements.txt              # 依赖列表
├── PROJECT_PLAN.md               # 详细技术方案
│
├── src/
│   ├── app.py                    # QApplication 初始化、暗色主题 QSS、异常钩子
│   │
│   ├── core/                     # 核心业务层
│   │   ├── config.py             # 应用配置管理（YAML 读写）
│   │   ├── book.py               # 数据模型（Book/Category/Tag/Bookmark）
│   │   ├── library.py            # 图书库管理器（CRUD + PDF 导入）
│   │   ├── storage.py            # JSON/YAML 文件存储（原子写入 + 缓存）
│   │   ├── search_engine.py      # Whoosh 全文搜索引擎
│   │   └── reading_tracker.py    # 阅读会话追踪（统计、连续天数）
│   │
│   ├── reader/                   # PDF 引擎层
│   │   ├── pdf_engine.py         # PyMuPDF 封装（打开/渲染/文字提取/搜索/TOC）
│   │   └── page_renderer.py      # 页面 → QPixmap + 40 页 LRU 缓存
│   │
│   ├── ui/                       # UI 层（PyQt6）
│   │   ├── main_window.py        # 主窗口 — 三面板 + 底栏布局编排
│   │   ├── library_panel.py      # 左侧书库面板
│   │   ├── reading_view.py       # 中央阅读视图容器
│   │   ├── reading_toolbar.py    # 阅读工具栏（模式/缩放/导航/护眼）
│   │   ├── notes_panel.py        # 右侧笔记面板（列表 + 内联编辑）
│   │   ├── claude_panel.py       # 底部 Claude 交互面板（模型选择）
│   │   ├── status_bar.py         # 底部状态栏（页码/模式/缩放/连续天数）
│   │   ├── themes/               # 主题系统
│   │   │   ├── theme_manager.py  # 主题管理器（QSS 加载 + 切换）
│   │   │   ├── palette.py        # 颜色调色板定义
│   │   │   ├── dark.qss          # 暗色主题
│   │   │   ├── light.qss         # 亮色主题
│   │   │   └── warm.qss          # 暖色护眼主题
│   │   ├── dialogs/              # 对话框（14 个）
│   │   │   ├── add_book.py       # 导入图书
│   │   │   ├── add_category.py   # 新建分类
│   │   │   ├── add_tag.py        # 新建标签
│   │   │   ├── book_info.py      # 书籍信息编辑（含标签多选）
│   │   │   ├── book_preview.py   # AI 全书预览总结（流式）
│   │   │   ├── code_exercise.py  # 代码练习生成
│   │   │   ├── dashboard.py      # 阅读统计仪表盘
│   │   │   ├── html_explanation.py # 交互式 HTML 讲解生成
│   │   │   ├── html_list.py      # HTML 讲解列表管理
│   │   │   ├── html_viewer.py    # HTML 讲解查看器（QWebEngineView）
│   │   │   ├── preview_viewer.py # 全书总结查看器
│   │   │   └── settings.py       # 设置（主题/语言/阅读/Claude）
│   │   └── widgets/              # 自定义组件
│   │       ├── page_canvas.py    # PDF 页面画布（QGraphicsView 虚拟渲染 + 文字选中 + 笔记高亮叠加）
│   │       ├── screenshot_tool.py # 截图选区工具
│   │       ├── terminal_widget.py # 聊天终端（对话气泡 + Markdown + 代码高亮）
│   │       ├── bookmark_widget.py # 书签列表
│   │       ├── graph_canvas.py    # 知识图谱可视化（QGraphicsView 交互）
│   │       └── tag_chip.py        # 标签芯片组件
│   │
│   ├── claude/                   # Claude Code 集成
│   │   ├── claude_agent.py       # Agent 管理器（每书一个独立会话，LRU 淘汰）
│   │   ├── claude_client.py      # QProcess 子进程调用 + stream-json 解析 + TitleGenerator
│   │   ├── context_builder.py    # 上下文数据模型（BookContext / ClaudeContext / no_tools）
│   │   └── prompt_templates.py   # 预设 Prompt 模板
│   │
│   ├── notes/                    # 笔记系统
│   │   ├── models.py             # Note 数据模型（含 highlight_rects）
│   │   ├── note_manager.py       # 笔记 CRUD
│   │   └── obsidian_exporter.py  # Jinja2 模板 → Obsidian vault（增量同步）
│   │
│   ├── knowledge/                # 知识图谱
│   │   ├── models.py             # Concept / ConceptLink 数据模型
│   │   ├── graph_engine.py       # NetworkX 图引擎（CRUD/去重/布局）
│   │   └── concept_extractor.py  # 解析 Claude JSON → 图节点/边
│   │
│   └── utils/
│       └── logger.py             # 日志工具（stderr + 按天滚动文件，保留 7 天）
│
├── resources/
│   └── templates/obsidian/       # Obsidian 导出模板（Jinja2）
│       ├── book-note.md.j2
│       ├── concept.md.j2
│       └── moc.md.j2
│
├── tests/                        # 测试（pytest）
│   ├── conftest.py               # 共享 fixtures
│   ├── fixtures/
│   │   └── generate_sample_pdf.py # 测试用 PDF 生成器
│   ├── unit/                     # 10 个单元测试文件
│   └── integration/
│       └── test_obsidian_export.py
│
└── docs/                         # 实施日志
    ├── phase2-implementation-log.md
    ├── phase3-implementation-log.md
    ├── phase4-implementation-log.md
    ├── phase5-enhancement-log.md
    └── phase5-r2-plan.md
```

### 数据存储

所有数据以 JSON/YAML 文本文件存储在 `~/.claude-book-reader/` 下：

```
~/.claude-book-reader/
├── config.yaml              # 应用配置（主题、Claude 模型、阅读偏好、代码练习目录）
├── library.json             # 全部书籍元数据数组
├── categories.json          # 树形分类
├── tags.json                # 标签定义（含颜色）
├── bookmarks.json           # 书签（按 book_id 索引）
├── reading_sessions.json    # 阅读会话记录
├── concepts.json            # 知识图谱节点
├── concept_links.json       # 知识图谱边
├── search_index/            # Whoosh 全文索引
├── logs/                    # 按天滚动的日志文件
└── books/
    └── <uuid>/
        ├── metadata.json    # 单书 TOC、同步状态
        ├── notes.json       # 笔记列表
        ├── book_preview.json # 全书预览总结
        ├── text_cache/      # 逐页文字缓存
        └── html_explanations/ # 交互式 HTML 讲解
            ├── index.json   # 讲解元数据索引
            └── *.html       # 生成的 HTML 文件
```

### Claude 通信机制

```
用户输入问题
    ↓
ClaudeAgent 构建上下文（BookContext + InteractionContext + 对话历史 + 全书预览）
    ↓
ClaudeClient 将 prompt 写入临时文件 + 设置 stdin 重定向
    ↓
QProcess 启动: claude -p - --model <model> --output-format stream-json [--tools ""]
    ↓                                        ↑
    │                              no_tools=True 时禁用所有 CLI 工具
    ↓
逐行解析 JSON 流（type: "assistant" 的 text 片段）
    ↓
TerminalWidget 实时显示（Markdown 渲染 + 代码高亮）
    ↓
完整响应追加到 ClaudeAgent 对话历史（最多 40 条）
```

---

## 配置

编辑 `~/.claude-book-reader/config.yaml`：

```yaml
app:
  language: zh-CN
  theme: dark                    # dark | light | warm
  default_reading_mode: single_continuous
  default_zoom: fit_width

obsidian:
  vault_path: ./obsidian-vault   # 导出目标路径
  auto_sync: false
  sync_on_close: true

claude:
  max_concurrent_agents: 3
  agent_timeout_minutes: 60
  model: ""                      # 留空使用 CLI 默认模型
  available_models:              # 下拉菜单可选模型列表
    - sonnet
    - opus
    - haiku
    - claude-sonnet-4-6
    - claude-opus-4-7
    - claude-haiku-4-5-20251001

reading:
  page_cache_size: 20
  scroll_speed: 1.0
  preload_pages: 5
  idle_timeout_minutes: 5        # 闲置超时自动结束阅读会话
  flush_interval_seconds: 30     # 会话数据落盘频率

code_exercises:
  output_dir: ""                 # 代码练习输出目录（空则每次询问）
```

---

## 开发

### 运行测试

```bash
# 运行全部测试
pytest tests/

# 带覆盖率报告
pytest tests/ --cov=src --cov-report=html

# 跳过慢速测试
pytest tests/ -m "not slow"

# 代码检查
ruff check src/ tests/
```

### 当前开发状态

| Phase | 内容 | 状态 |
|---|---|---|
| Phase 1 | 项目结构、图书管理、存储层、书架 UI | ✅ 完成 |
| Phase 2 | PDF 阅读核心、4 种模式、书签、文字选中、全文检索 | ✅ 完成 |
| Phase 3 | Claude 集成、Agent 管理、终端面板、截图分析 | ✅ 完成 |
| Phase 4 | 笔记系统、知识图谱、Obsidian 导出 | ✅ 完成 |
| Phase 5 R1 | 测试基础设施、异常处理、日志系统 | ✅ 完成 |
| Phase 5 R2 | 阅读统计+仪表盘、主题系统、护眼模式、笔记追问、全书预览 | ✅ 完成 |
| Phase 5 R3 | HTML 交互讲解、代码练习生成、no-tools 模式 | ✅ 完成 |

### 待实现功能

以下功能在原始 PROJECT_PLAN 中规划，尚未实施：

| 功能 | 优先级 | 说明 |
|---|---|---|
| **思维导图生成** | P2 | Claude 生成 Mermaid 语法思维导图，导出到 Obsidian 渲染 |
| **翻译功能** | P2 | 选中文字 → 一键翻译（目前可通过「问 Claude」手动翻译实现） |
| **PyInstaller 打包** | P2 | 打包为独立 exe（Windows）/ app（macOS），无需 Python 环境 |
| **Obsidian 双向同步** | P2 | 检测 Obsidian 中的外部变更，合并回应用 |
| **Agent 会话持久化** | P2 | 关闭书籍时保存会话摘要，下次打开可选恢复上下文 |
| **性能优化** | P1 | 大 PDF（500+ 页）内存占用优化、冷启动速度 |
| **跨平台测试** | P1 | macOS / Linux 上的完整测试（目前主要在 Windows 开发） |
| **笔记全文搜索** | P2 | 在笔记内容中进行全文检索 |
| **阅读提醒** | P3 | 定时提醒阅读、每日阅读目标 |
| **EPUB 支持** | P3 | 扩展支持 EPUB 格式（目前仅 PDF） |
| **多语言 UI** | P3 | UI 界面国际化（目前仅中文） |

### 技术栈

- **GUI**：PyQt6 (QGraphicsView, QSplitter, QProcess, QWebEngineView)
- **PDF**：PyMuPDF (fitz)
- **图算法**：NetworkX (spring_layout, Kamada-Kawai, shell_layout)
- **全文检索**：Whoosh (纯 Python)
- **模板**：Jinja2 (Obsidian 导出 + QSS 主题渲染)
- **配置**：YAML
- **数据**：JSON 纯文本（原子写入，Git 友好）

---

## 常见问题

### Claude CLI 未找到

确保已安装 Claude Code CLI，并确认 `claude` 命令在 PATH 中可见：

```bash
claude --version
```

### Claude 输出包含工具授权提示

部分场景（HTML 讲解生成、代码练习生成、全书预览）已默认使用 `no_tools=True` 模式（`--tools ""`），Claude 不会尝试调用文件写入工具。如果普通问答也出现此问题，请在 Claude 面板的输入中明确说明「请直接输出文本，不要使用工具」。

### PDF 文字选中偏移

不同 PDF 生成方式（LaTeX / Word / 扫描件）的坐标精度不同。如果选中文字时出现偏移，这属于已知问题。扫描版 PDF 不支持文字选中。

### 知识图谱布局

应用内使用 NetworkX 多种布局算法进行可视化。丰富的图探索体验请导出到 Obsidian 后使用 Graph View。

### 笔记高亮不显示

笔记高亮基于 PDF 坐标存储。如果关闭书籍后重新打开时高亮不显示，请检查是否在正确的页面上——高亮仅显示在创建时对应的页面。

---

## License

MIT
