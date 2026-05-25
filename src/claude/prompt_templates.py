"""预设 Prompt 模板"""

from __future__ import annotations

TEMPLATES: dict[str, str] = {
    "explain_text": """\
你是一位知识渊博的阅读导师。用户在阅读《{book_title}》时选中了以下文字，请帮助解释：

**选中文字**：
{selected_text}

**上下文**（同一段落/章节的附近文字）：
{surrounding_text}

**用户问题**：
{user_query}

请提供清晰、深入的解释。如果涉及专业概念，请用例子说明。""",

    "chapter_analysis": """\
请分析《{book_title}》的第 {chapter} 章：

**章节内容**：
{chapter_text}

请提供：
1. 核心观点（3-5 条）
2. 关键概念列表
3. 与其他章节的可能关联
4. 3 个值得深入思考的问题
5. 建议的补充阅读方向""",

    "reading_plan": """\
请根据以下书籍信息制定阅读计划：

**书名**：{book_title}
**作者**：{author}
**总页数**：{total_pages}
**目录**：
{toc}

请提供：
1. 分阶段阅读计划（按章节或主题分组）
2. 每阶段的预计时间
3. 重点章节标记
4. 建议的阅读顺序（是否可以跳读）
5. 阅读各阶段的目标检查点""",

    "reading_outline": """\
请根据以下目录为《{book_title}》生成详细阅读大纲：

**目录**：
{toc}

请提供：
1. 全书结构概览
2. 各章节核心主题
3. 概念依赖关系（哪些章节需要先读）
4. 重点章节推荐""",

    "optimize_notes": """\
请优化以下阅读笔记：

**书名**：{book_title}
**章节**：{chapter}
**原始笔记**：
{original_notes}

优化要求：{optimization_style}

请输出优化后的笔记，使用 Obsidian 兼容的 Markdown 格式，适当使用 [[双链]] 关联概念。""",

    "extract_concepts": """\
请从以下笔记中提取关键概念，用于构建知识图谱：

**笔记内容**：
{notes_content}

请为每个概念提供：
- 概念名称（简洁，适合作为 Obsidian 笔记标题）
- 简短描述（1-2 句）
- 与其他概念的关系（IS_A / RELATED_TO / PART_OF / LEADS_TO）
- 关系强度（1-10）

输出 JSON 格式。""",

    "analyze_screenshot": """\
用户在阅读《{book_title}》时截取了以下图片区域并提出问题。

**用户问题**：
{user_query}

请根据截图内容进行分析和回答。截图可能是图表、公式、代码或排版内容。
如果截图中有文字，请识别并引用。
如果截图中有图表，请解释图表传达的信息。""",

    "translate": """\
请将以下文字翻译为流畅的中文（来自《{book_title}》P{page}）：

{selected_text}

要求：保持学术/专业语气，专业术语保留英文并在括号内给出中文。""",

    "general_qa": """\
你是《{book_title}》的阅读助手。当前阅读进度：第 {current_page}/{total_pages} 页，{current_chapter}。

用户问题：{user_query}""",
}


def render(template_name: str, **kwargs: str) -> str:
    """渲染指定模板，缺失变量保留原样"""
    template = TEMPLATES.get(template_name, "{user_query}")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
