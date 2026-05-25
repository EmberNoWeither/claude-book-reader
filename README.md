# Claude Book Reader

> 基于 PyQt6 + PyMuPDF 的 PDF 图书管理与智能阅读器，深度集成 Claude Code 实现 AI 辅助阅读、笔记优化与知识图谱构建。

## 功能概览

### 📚 图书管理
- **PDF 导入**：自动提取元数据（标题、作者、页数、目录）
- **分类系统**：树形分类（学科/领域），支持父子层级
- **标签系统**：跨分类的灵活标签 + 颜色标记
- **三种浏览视图**：支持按分类过滤、标签过滤、书名/作者搜索
- **阅读状态追踪**：未读 / 阅读中 / 已读完，自动流转

### 📖 PDF 阅读
- **四种阅读模式**：单页连续滚动、双页连续滚动、单页翻页、双页翻页
- **虚拟渲染**：仅渲染可见页 + 缓冲区，支持大 PDF 流畅阅读
- **缩放控制**：放大/缩小/适应宽度/适应页面/原始大小，支持 Ctrl+滚轮
- **文字选中**：拖拽选词，坐标精确映射，弹出浮动菜单
- **书签系统**：添加/删除/跳转书签，自动匹配章节标题
- **中键拖拽**：平移画布
- **全文检索**：基于 Whoosh 的全文搜索引擎，支持模糊搜索

### 🤖 Claude AI 集成
- **每书独立 Agent**：打开书籍时自动创建专属 AI 会话，维护独立对话历史
- **流式响应**：实时显示 Claude 回复（Markdown 渲染）
- **多模型支持**：可在 sonnet / opus / haiku 等模型间切换
- **交互场景**：
  - 📝 **选中文字问答**：选中文字 → 右键「问 Claude」→ AI 解释/翻译/展开
  - 🖼️ **截图分析**：框选屏幕区域 → AI 分析图表/公式/排版内容
  - 📊 **章节分析**：一键生成章节摘要、核心观点、关键概念、思辨问题
  - ✨ **笔记优化**：4 种优化风格（精炼/结构化/扩展/批判性）
  - 🧠 **概念提取**：从笔记中提取关键概念构建知识图谱
  - 💬 **自由问答**：底部终端直接对话

### 📝 笔记系统
- **4 种笔记类型**：页面锚点笔记、文字高亮、章节笔记、全局笔记
- **富文本预览**：Markdown 渲染 + KaTeX 数学公式支持
- **AI 标题生成**：自动为笔记生成简洁标题
- **高亮持久化**：笔记关联的 PDF 高亮区域自动显示在阅读区
- **右键上下文**：高亮区域右键 → 预览/编辑/删除笔记

### 🧠 知识图谱
- **概念提取**：Claude 从笔记中提取概念及关系（JSON 结构化输出）
- **自动去重合并**：同名概念自动合并，别名校验
- **可视化**：NetworkX 力导向布局 + QGraphicsView 交互式画布
- **关系类型**：IS_A / RELATED_TO / PART_OF / LEADS_TO / APPLIES_TO
- **缩放拖拽**：滚轮缩放、拖拽节点、双击展开

### 📤 Obsidian 导出
- **一键导出**：将笔记和概念导出为 Obsidian vault
- **模板渲染**：Jinja2 模板生成标准 Obsidian 笔记（YAML frontmatter + Wikilink）
- **增量同步**：基于内容比较，避免重复写入
- **导出结构**：
  ```
  obsidian-vault/
  ├── Books/          # 每本书的笔记（含元数据、大纲、摘录）
  ├── Concepts/       # 每个概念的独立页面（含 [[双链]]）
  └── _MOCs/          # 知识地图汇总页
  ```

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
| PyQt6-WebEngine | >= 6.5 | 笔记预览中的 Web 渲染 |
| PyMuPDF | >= 1.23 | PDF 解析与渲染 |
| NetworkX | >= 3.0 | 知识图谱数据结构与布局 |
| markdown2 | >= 2.4 | Markdown → HTML 转换 |
| Pygments | >= 2.15 | 代码高亮 |
| Pillow | >= 10.0 | 图像处理 |
| PyYAML | >= 6.0 | YAML 配置读写 |
| Jinja2 | >= 3.1 | Obsidian 模板渲染 |
| Whoosh | >= 2.7 | 全文检索引擎 |

---

## 使用

### 启动应用

```bash
python main.py
# 或（如果已 pip install -e .）
claude-book-reader
```

### 基本流程

```
导入 PDF → 选择书籍 → 开始阅读 → 选中文字问 AI / 创建笔记
                                    ↓
                              导出到 Obsidian 知识仓库
```

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
| `Ctrl+Shift+S` | 截图选区（发给 Claude 分析） |
| `Ctrl+Return` | 发送消息给 Claude |
| `Ctrl+E` | 导出到 Obsidian |
| `Ctrl+Shift+K` | 打开知识图谱 |
| `Ctrl+Shift+L` | 切换书库面板 |
| `Ctrl+Shift+N` | 切换书签/笔记面板 |
| `Ctrl+Shift+A` | 切换 Claude 面板 |
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
├── main.py                    # 应用入口
├── setup.py                   # 打包配置
├── requirements.txt           # 依赖列表
├── PROJECT_PLAN.md            # 详细技术方案
│
├── src/
│   ├── app.py                 # QApplication 初始化、暗色主题 QSS
│   │
│   ├── core/                  # 核心业务层
│   │   ├── config.py          # 应用配置管理（YAML 读写）
│   │   ├── book.py            # 数据模型（Book/Category/Tag/Bookmark）
│   │   ├── library.py         # 图书库管理器（CRUD + PDF 导入）
│   │   ├── storage.py         # JSON/YAML 文件存储（原子写入 + 缓存）
│   │   └── search_engine.py   # Whoosh 全文搜索引擎
│   │
│   ├── reader/                # PDF 引擎层
│   │   ├── pdf_engine.py      # PyMuPDF 封装（打开/渲染/文字提取/搜索）
│   │   └── page_renderer.py   # 页面 → QPixmap + 40 页 LRU 缓存
│   │
│   ├── ui/                    # UI 层（PyQt6）
│   │   ├── main_window.py     # 主窗口 — 三面板 + 底栏布局编排
│   │   ├── library_panel.py   # 左侧书库面板
│   │   ├── reading_view.py    # 中央阅读视图容器
│   │   ├── reading_toolbar.py # 阅读工具栏（模式/缩放/导航）
│   │   ├── notes_panel.py     # 右侧笔记面板（列表 + 内联编辑）
│   │   ├── claude_panel.py    # 底部 Claude 交互面板
│   │   ├── status_bar.py      # 底部状态栏
│   │   ├── dialogs/           # 对话框
│   │   │   ├── add_book.py        # 导入图书
│   │   │   ├── add_category.py    # 新建分类
│   │   │   ├── add_tag.py         # 新建标签
│   │   │   ├── book_info.py       # 书籍信息编辑
│   │   │   └── settings.py        # 设置（Phase 5）
│   │   └── widgets/           # 自定义组件
│   │       ├── page_canvas.py     # PDF 页面画布（QGraphicsView 虚拟渲染 + 文字选中）
│   │       ├── screenshot_tool.py # 截图选区工具
│   │       ├── terminal_widget.py # 聊天终端（对话气泡 + Markdown）
│   │       ├── bookmark_widget.py # 书签列表
│   │       ├── graph_canvas.py    # 知识图谱可视化
│   │       └── tag_chip.py        # 标签芯片组件
│   │
│   ├── claude/                # Claude Code 集成
│   │   ├── claude_agent.py    # Agent 管理器（每书一个独立会话）
│   │   ├── claude_client.py   # QProcess 子进程调用 + stream-json 解析
│   │   ├── context_builder.py # 上下文数据模型（BookContext / ClaudeContext）
│   │   └── prompt_templates.py # 预设 Prompt 模板
│   │
│   ├── notes/                 # 笔记系统
│   │   ├── models.py          # Note 数据模型
│   │   ├── note_manager.py    # 笔记 CRUD
│   │   └── obsidian_exporter.py # Jinja2 模板 → Obsidian vault
│   │
│   ├── knowledge/             # 知识图谱
│   │   ├── models.py             # Concept / ConceptLink 数据模型
│   │   ├── graph_engine.py       # NetworkX 图引擎（CRUD/去重/布局）
│   │   └── concept_extractor.py  # 解析 Claude JSON → 图节点/边
│   │
│   └── utils/
│       └── logger.py          # 日志工具
│
├── resources/
│   └── templates/obsidian/    # Obsidian 导出模板（Jinja2）
│       ├── book-note.md.j2
│       ├── concept.md.j2
│       └── moc.md.j2
│
└── docs/                      # 实施日志
    ├── phase2-implementation-log.md
    ├── phase3-implementation-log.md
    ├── phase4-implementation-log.md
    └── phase5-enhancement-log.md
```

### 数据存储

所有数据以 JSON/YAML 文本文件存储在 `~/.claude-book-reader/` 下：

```
~/.claude-book-reader/
├── config.yaml              # 应用配置（主题、Claude 模型、阅读偏好）
├── library.json             # 全部书籍元数据数组
├── categories.json          # 树形分类
├── tags.json                # 标签定义（含颜色）
├── bookmarks.json           # 书签（按 book_id 索引）
├── reading_sessions.json    # 阅读会话记录
├── concepts.json            # 知识图谱节点
├── concept_links.json       # 知识图谱边
├── search_index/            # Whoosh 全文索引
└── books/
    └── <uuid>/
        ├── metadata.json    # 单书 TOC、同步状态
        ├── notes.json       # 笔记列表
        └── text_cache/      # 逐页文字缓存
```

### Claude 通信机制

```
用户输入问题
    ↓
ClaudeAgent 构建上下文（BookContext + InteractionContext + 对话历史）
    ↓
ClaudeClient 将 prompt 写入临时文件 + 设置 stdin 重定向
    ↓
QProcess 启动: claude -p - --model <model> --output-format stream-json
    ↓
逐行解析 JSON 流（type: "assistant" 的 text 片段）
    ↓
TerminalWidget 实时显示（Markdown 渲染）
    ↓
完整响应追加到 ClaudeAgent 对话历史（最多 40 条）
```

---

## 配置

编辑 `~/.claude-book-reader/config.yaml`：

```yaml
app:
  language: zh-CN
  theme: dark                    # dark（默认）
  default_reading_mode: single_continuous
  default_zoom: fit_width

obsidian:
  vault_path: ./obsidian-vault   # 导出目标路径
  auto_sync: false
  sync_on_close: true

claude:
  max_concurrent_agents: 3
  agent_timeout_minutes: 60
  model: ""                      # 留空使用默认模型
  available_models:              # 下拉菜单可选模型列表
    - sonnet
    - opus
    - haiku

reading:
  page_cache_size: 20
  scroll_speed: 1.0
  preload_pages: 5
```

---

## 开发

### 运行

```bash
pip install -r requirements.txt
python main.py
```

### 当前开发状态

| Phase | 内容 | 状态 |
|---|---|---|
| Phase 1 | 项目结构、图书管理、存储层、书架 UI | ✅ 完成 |
| Phase 2 | PDF 阅读核心、4 种模式、书签、文字选中、全文检索 | ✅ 完成 |
| Phase 3 | Claude 集成、Agent 管理、终端面板、截图分析 | ✅ 完成 |
| Phase 4 | 笔记系统、知识图谱、Obsidian 导出 | ✅ 完成 |
| Phase 5 | 阅读统计、主题系统、翻译、打包发布 | 🚧 待实施 |

详细技术方案见 [PROJECT_PLAN.md](PROJECT_PLAN.md)，各阶段实施日志见 `docs/` 目录。

### 技术栈

- **GUI**：PyQt6 (QGraphicsView, QSplitter, QProcess)
- **PDF**：PyMuPDF (fitz)
- **图算法**：NetworkX (spring_layout, Kamada-Kawai)
- **全文检索**：Whoosh (纯 Python)
- **模板**：Jinja2
- **配置**：YAML
- **数据**：JSON 纯文本（原子写入，Git 友好）

---

## 常见问题

### Claude CLI 未找到

确保已安装 Claude Code CLI，并确认 `claude` 命令在 PATH 中可见：

```bash
claude --version
```

### PDF 文字选中偏移

不同 PDF 生成方式（LaTeX / Word / 扫描件）的坐标精度不同。如果选中文字时出现偏移，这属于已知问题（见 PROJECT_PLAN 第 16 节"技术风险与对策"）。扫描版 PDF 不支持文字选中。

### 知识图谱布局

应用内使用 NetworkX 力导向布局进行简单可视化。丰富的图探索体验请导出到 Obsidian 后使用 Graph View。

---

## License

MIT
