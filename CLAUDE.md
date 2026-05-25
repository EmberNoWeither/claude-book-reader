# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py

# Package/install (creates `claude-book-reader` CLI entry point)
pip install -e .
```

No test runner or linter is configured yet. The `tests/` directory exists but is empty.

## Architecture

Python 3.10+ desktop app built with PyQt6. Entry point: `main.py` → `src/app.py` → `src/ui/main_window.py`.

**Layer structure:**

```
src/ui/          — PyQt6 widgets (main window, panels, dialogs, page canvas)
src/core/        — Business logic (library, book models, storage, config, search)
src/reader/      — PDF engine (PyMuPDF wrapper + LRU-cached page renderer)
src/notes/       — Note management and Obsidian export
src/knowledge/   — NetworkX knowledge graph + Claude-powered concept extraction
src/claude/      — Claude agent integration (QProcess wrapper, context builder)
src/utils/       — File ops, image processing, logging
```

**UI layout:** 3-panel + bottom design — `library_panel.py` (left) | `reading_view.py` + `page_canvas.py` (center) | QTabWidget with `bookmark_widget.py` + `notes_panel.py` (right) | `claude_panel.py` (bottom).

**Data storage:** All state persisted as JSON/YAML files under `~/.claude-book-reader/` — no database. `src/core/storage.py` handles atomic writes (write to `.tmp`, then rename). Per-book notes in `books/{id}/notes.json`. Global concepts in `concepts.json` + `concept_links.json`.

**PDF rendering:** `src/reader/page_renderer.py` maintains a 40-page LRU render cache. `src/ui/widgets/page_canvas.py` implements virtual rendering (only visible pages + 3-page buffer) with 4 reading modes (single page, double page, continuous scroll, flip).

**Claude integration:** `src/claude/claude_client.py` spawns `claude -p - --model <model>` via QProcess with stdin file redirect (Windows-safe). `src/claude/claude_agent.py` maintains per-book conversation history (max 40 messages). Supports: text Q&A, screenshot analysis, chapter analysis, note optimization, concept extraction. Model selection via `--model` flag, configurable in `config.yaml` under `claude.model` and `claude.available_models`.

**Notes system:** `src/notes/note_manager.py` provides CRUD for page-anchor/chapter/global/highlight notes with title field. `src/ui/notes_panel.py` shows notes filtered by current page/chapter with inline editing (title + content), Claude optimization (4 styles), and auto-title generation via `TitleGenerator`.

**Knowledge graph:** `src/knowledge/graph_engine.py` wraps NetworkX for concept storage, dedup/merge, and layout computation. `src/knowledge/concept_extractor.py` parses Claude JSON responses into graph nodes/edges. `src/ui/widgets/graph_canvas.py` renders the graph via QGraphicsView.

**Obsidian export:** `src/notes/obsidian_exporter.py` renders Jinja2 templates (`resources/templates/obsidian/`) into a vault structure (Books/, Concepts/, _MOCs/). Incremental sync based on content comparison.

## Implementation Status

- **Phase 1–2 complete:** Project structure, library management, full PDF reading core (rendering, bookmarks, full-text search via Whoosh, text selection)
- **Phase 3 complete:** Claude Code integration (text Q&A, screenshot, chapter analysis, streaming responses)
- **Phase 4 complete:** Notes system, knowledge graph (NetworkX + QGraphicsView), Obsidian export
- **Phase 5 planned:** Reading statistics, theme system, translation, packaging

The authoritative technical spec is `PROJECT_PLAN.md`. Implementation logs in `docs/phase2-implementation-log.md` and `docs/phase3-implementation-log.md`.
