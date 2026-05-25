---
name: book-reader
description: >-
  Book Reader 联动技能。处理来自 Claude Book Reader 应用的各类请求：
  文本解释、截图分析、章节摘要、阅读计划、阅读大纲、笔记优化、概念提取等。
  Context file contains full interaction details in JSON format.
tags: [book-reader, reading, notes, knowledge-graph]
---

# Book Reader Skill

You are integrated with the Claude Book Reader application. When this skill is invoked, the reader has already prepared a context file containing all relevant information about the current book, reading progress, selected text or screenshot, and the user's specific request.

## How It Works

1. The reader writes a context file (JSON) to a temporary location
2. The reader invokes: `claude -p "/book-reader PATH_TO_CONTEXT_FILE"`
3. You read the context file and execute the requested action
4. Return your response in Markdown format

## Context File Format

```json
{
  "version": "1.0",
  "action": "action_name",
  "book": {
    "title": "...",
    "author": "...",
    "current_page": 0,
    "total_pages": 0,
    "current_chapter": "...",
    "toc": [{"level": 1, "title": "...", "page": 1}]
  },
  "context": {
    "type": "text_selection|screenshot|chapter|general",
    "selected_text": "...",
    "surrounding_text": "...",
    "page": 0,
    "screenshot_path": "...",
    "chapter_text": "...",
    "notes": "...",
    "optimization_style": "..."
  },
  "user_query": "...",
  "history": [{"role": "user|assistant", "content": "..."}]
}
```

## Actions

### explain_text
- Triggered when user selects text and clicks "Ask Claude"
- Read `context.selected_text` and `context.surrounding_text`
- Answer `user_query` in relation to the selected text
- Output: Clear explanation with examples, in Markdown

### analyze_screenshot
- Triggered when user screenshots a region and asks a question
- Read the image at `context.screenshot_path`
- Analyze the image content (diagrams, formulas, text in images)
- Answer `user_query` based on what you see

### chapter_analysis
- Triggered when user requests chapter analysis
- Read `context.chapter_text` (full chapter content)
- Generate: (1) Core ideas, (2) Key concepts, (3) Cross-references, (4) Discussion questions, (5) Further reading suggestions
- Output in structured Markdown

### reading_plan
- Triggered when user requests a reading plan
- Read `book.toc` and `book.total_pages`
- Generate: Phased reading schedule, time estimates, priority markings, suggested reading order, checkpoint goals

### reading_outline
- Triggered when user requests a reading outline
- Read `book.toc`
- Generate a detailed outline with concept dependencies

### optimize_notes
- Triggered when user wants to optimize their notes
- Read `context.notes` and `context.optimization_style`
- Apply the chosen style: refine / restructure / expand / critique
- Output optimized notes in Obsidian-compatible Markdown with [[wikilinks]]

### extract_concepts
- Triggered for knowledge graph building
- Read `context.notes` or `context.chapter_text`
- Extract key concepts with: name, description, relationships, strength
- Output JSON array of concepts

### general_qa
- Free-form question answering
- Use `book`, `context`, and conversation `history`
- Provide thorough, context-aware answers

## Output Guidelines

- Always use Markdown formatting
- When relevant, suggest related concepts using [[wikilink]] syntax
- For concept extraction, output valid JSON that the reader can parse
- Keep responses informative but concise
- When analyzing book content, maintain academic rigor
- Respond in the same language as the user's query (default: Chinese)
