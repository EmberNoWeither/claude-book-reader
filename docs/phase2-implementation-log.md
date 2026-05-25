# Phase 2 施工记录：PDF 阅读核心

> 日期：2026-05-24 ~ 2026-05-25
> 状态：已完成

---

## 一、概述

Phase 2 实现了 PDF 阅读核心功能，包括四种阅读模式、页面渲染管线、文字选中、书签系统和全文检索引擎。施工分两轮完成：

- **第一轮**（05-24）：搭建 reader 模块 + UI 组件 + 主窗口集成
- **第二轮**（05-25）：性能优化（虚拟渲染）、画质修复（DPR）、文字选中修复

---

## 二、新增文件

### Reader 引擎层

| 文件 | 职责 |
|---|---|
| `src/reader/pdf_engine.py` | PyMuPDF (fitz) 封装：打开/关闭文档、页数、目录、元数据、文字提取（`get_text` / `get_text("words")`）、页面尺寸、光栅化 (`render_pixmap`)、文本搜索 |
| `src/reader/page_renderer.py` | PDF 页面 → QPixmap 渲染，LRU 缓存（上限 40 页），按 `(page_num, render_zoom)` 键缓存 |

### UI 组件

| 文件 | 职责 |
|---|---|
| `src/ui/widgets/page_canvas.py` | QGraphicsView 页面画布：四种阅读模式布局、虚拟渲染、DPR 感知、文字选中（拖选 + 双击单词）、中键平移、键盘导航 |
| `src/ui/reading_toolbar.py` | 阅读工具栏：模式切换按钮组、缩放控制（+/−/适应宽度/适应页面/100%）、页码跳转、添加书签按钮 |
| `src/ui/reading_view.py` | 阅读视图容器：组合 toolbar + canvas，管理书籍开/闭生命周期，阅读进度持久化，选中文字预览条 |
| `src/ui/widgets/bookmark_widget.py` | 书签列表面板：显示当前书籍书签、双击跳转、右键删除 |

### 搜索

| 文件 | 职责 |
|---|---|
| `src/core/search_engine.py` | Whoosh 全文检索引擎：Schema 定义、逐页索引、模糊搜索、高亮片段、按书籍过滤 |

---

## 三、修改文件

### 第一轮

| 文件 | 变更 |
|---|---|
| `src/ui/main_window.py` | 替换占位 QLabel 为 ReadingView + BookmarkWidget；添加快捷键（Ctrl+1/2/3/4 切换模式、Ctrl+=/- 缩放、Ctrl+0 原始大小、Ctrl+B 书签、Ctrl+G 跳转、Ctrl+Shift+W 适应宽度）；连接 library→reader→statusbar 信号链 |
| `src/app.py` | 暗色主题新增 QGraphicsView 背景样式 |

### 第二轮（性能/画质修复）

| 文件 | 变更 |
|---|---|
| `src/reader/page_renderer.py` | 移除 `zoom_changed()` 激进缓存淘汰；LRU 上限 20→40；参数重命名 `zoom`→`render_zoom` |
| `src/ui/widgets/page_canvas.py` | **重写**：全量渲染 → 虚拟渲染（可见页 ± 3 页缓冲）；新增 DPR 感知（`render_zoom = display_zoom × devicePixelRatio`，item 缩放 `1/dpr`）；文字选中从无反馈 → 持久高亮 + 预览条 + 状态栏消息；ScrollHandDrag 冲突 → 中键平移 |
| `src/ui/reading_view.py` | 文字选中空 handler → 选中预览条 + 信号转发（`text_selected` / `selection_cleared`） |
| `src/ui/main_window.py` | 连接 `text_selected` → 状态栏临时消息；连接 `selection_cleared` → 清除消息 |

---

## 四、架构设计

### 渲染管线

```
PDF 文件
  │
  ▼
fitz.Document ── page.get_pixmap(matrix)
  │
  ▼
QPixmap (render_zoom = display_zoom × DPR)
  │
  ▼
PageRenderer (LRU cache, key = (page_num, render_zoom))
  │
  ▼
QGraphicsPixmapItem (setScale(1/DPR) → 逻辑尺寸显示)
  │
  ▼
QGraphicsScene → QGraphicsView
```

### 主窗口布局

```
MainWindow
├── LibraryPanel (左, 260px)
├── ReadingView (中, stretch)
│   ├── ReadingToolbar (模式 / 缩放 / 导航 / 书签)
│   ├── SelectionLabel (选中文字预览, 条件显示)
│   └── PageCanvas (QGraphicsView)
├── BookmarkWidget (右, 220px)
└── ReaderStatusBar (底)
```

### 虚拟渲染策略

```
页面几何计算 (O(1), 不渲染)
  → 设定 SceneRect = 全部页面总高度
  → _update_visible_items():
      计算可见页范围 [first, last]
      扩展到 [first - 3, last + 3]  ← 缓冲
      销毁范围外的 QGraphicsPixmapItem
      创建范围内缺失的 QGraphicsPixmapItem (触发懒渲染)
```

触发时机：`scrollContentsBy()`（滚动）、`resizeEvent()`（窗口大小变化）、`set_zoom()`（缩放）、`_rebuild_layout()`（模式切换）。

### 四种阅读模式

| 模式 | 快捷键 | 布局 | 导航 |
|---|---|---|---|
| 单页连续 | Ctrl+1 | 页面垂直堆叠，居中 | 滚轮/滚动条 |
| 双页连续 | Ctrl+2 | 封面居中，后续成对排列 | 滚轮/滚动条 |
| 单页翻页 | Ctrl+3 | 单页 fitInView | 滚轮/方向键 |
| 双页翻页 | Ctrl+4 | 封面单独 / 双页 fitInView | 滚轮/方向键 |

---

## 五、问题与修复记录

### 问题 1：导入/模式切换/缩放极度缓慢

**根因**：`_layout_scene()` 在每次操作时渲染全部页面（200 页 = 200 次 PyMuPDF 光栅化）。

**修复**：虚拟渲染。只对可见页 + 缓冲页创建 QGraphicsPixmapItem，页面几何信息从 `fitz.Page.rect` 快速计算（无需渲染）。

### 问题 2：字体模糊、渲染质量低

**根因**：
- 缩放计算未乘 `devicePixelRatio`（HiDPI 显示器上分辨率不足）
- 翻页模式下 `fitInView()` 二次缩放损失清晰度
- 缩放时 `zoom_changed()` 激进清空全部缓存

**修复**：
- `render_zoom = display_zoom × devicePixelRatioF()`
- item 应用 `setScale(1.0 / dpr)` 缩回逻辑尺寸
- 移除 `zoom_changed()` 缓存淘汰

### 问题 3：文字选中不工作

**根因**：
- `reading_view.py` 中 `_on_text_selected` 为空函数（pass）——文字被提取但无 UI 反馈
- `ScrollHandDrag` 拖拽模式与文字选中有潜在冲突
- 选中高亮在松手后立即消失

**修复**：
- 选中后保持半透明蓝色高亮矩形（持久显示直到点击其他地方或按 Esc）
- 画布上方显示选中文字预览条
- 状态栏显示 "已选中 N 个字符 (Px)"
- 移除 ScrollHandDrag，改用中键拖拽平移
- 双击单词直接选中

### 问题 4：`QGraphicsView.ShapeFlag.NoFrame` 不存在

**根因**：PyQt6 中 `QGraphicsView.ShapeFlag` 枚举路径错误，应使用 `QFrame.Shape.NoFrame`。

**修复**：导入 `QFrame`，使用 `QFrame.Shape.NoFrame`。

---

## 六、快捷键清单

| 快捷键 | 功能 |
|---|---|
| `Ctrl+1/2/3/4` | 切换阅读模式 |
| `Ctrl+=` / `Ctrl+-` | 放大 / 缩小 |
| `Ctrl+0` | 原始大小 (100%) |
| `Ctrl+Shift+W` | 适应宽度 |
| `Ctrl+B` | 添加书签 |
| `Ctrl+G` | 跳转页码 |
| `Ctrl+O` | 导入 PDF |
| `Ctrl+W` | 关闭书籍 |
| `Ctrl+Q` | 退出 |
| `Ctrl+Shift+L` | 切换书库面板 |
| `Ctrl+Shift+N` | 切换书签面板 |
| `F11` | 全屏阅读 |
| `← → ↑ ↓` | 翻页 / 导航 |
| `Home / End` | 首页 / 末页 |
| `Esc` | 清除文字选中 |
| `鼠标中键拖拽` | 平移画布 |
| `鼠标左键拖拽` | 选中文字 |
| `双击` | 选中单词 |

---

## 七、依赖

Phase 2 涉及的 pip 依赖均在 Phase 1 已安装：

```
PyMuPDF (fitz)  - PDF 解析与渲染
PyQt6           - GUI 框架  
Whoosh          - 全文检索引擎
```

---

## 八、后续工作（Phase 3）

Phase 3 将实现 Claude Code 集成：
- `ClaudeAgent` 常驻子进程管理（每本书一个 agent）
- 上下文文件协议（JSON 格式）
- Skill 定义文件 (`skills/book-reader.md`)
- 终端面板 UI（Claude 对话界面）
- 选中文字 → 问 Claude
- 截图选区 → 问 Claude
- 章节分析 / 阅读计划 / 笔记优化 Prompt 模板
