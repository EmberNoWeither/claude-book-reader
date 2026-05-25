"""生成最小测试 PDF — 5 页，含中英文标题、多列、图表占位"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def generate_sample_pdf(output_path: str | Path) -> Path:
    """生成 5 页测试 PDF，返回文件路径。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        title="Sample Test Book",
        author="Test Author",
        subject="Testing",
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=11, leading=15)

    story = []

    # Page 1 — Cover
    story.append(Paragraph("Sample Test Book", h1))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("A minimal PDF for unit tests.", body))
    story.append(Paragraph("Author: Test Author", body))
    story.append(PageBreak())

    # Page 2 — Chapter 1
    story.append(Paragraph("Chapter 1: Introduction", h1))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "This is the first chapter. It contains some lorem ipsum text to "
        "test full-text search and word selection. The keyword UNIQUE_FIRST "
        "should appear only on this page for indexing tests.",
        body,
    ))
    story.append(PageBreak())

    # Page 3 — Chapter 2
    story.append(Paragraph("Chapter 2: Methods", h1))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "Methods section with another keyword UNIQUE_SECOND. "
        "We use back-propagation to compute gradients.",
        body,
    ))
    table = Table([
        ["Method", "Accuracy"],
        ["A", "0.85"],
        ["B", "0.92"],
    ])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(table)
    story.append(PageBreak())

    # Page 4 — Chapter 3
    story.append(Paragraph("Chapter 3: Results", h1))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "Results section. UNIQUE_THIRD keyword for testing.",
        body,
    ))
    story.append(PageBreak())

    # Page 5 — Conclusion
    story.append(Paragraph("Chapter 4: Conclusion", h1))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "Final chapter. UNIQUE_FOURTH keyword.",
        body,
    ))

    doc.build(story)
    return output_path


if __name__ == "__main__":
    out = Path(__file__).parent / "sample.pdf"
    generate_sample_pdf(out)
    print(f"Generated: {out}")
