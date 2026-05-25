"""ConceptExtractor 测试 — 解析 Claude 返回的多种 JSON 格式"""

from __future__ import annotations

import pytest

from knowledge.concept_extractor import ConceptExtractor
from knowledge.graph_engine import GraphEngine


@pytest.fixture
def extractor(tmp_storage):
    return ConceptExtractor(GraphEngine(tmp_storage))


def test_parse_plain_json(extractor):
    response = '[{"name": "BP", "description": "back prop", "relations": []}]'
    concepts = extractor.process_response(response, "book1")
    assert len(concepts) == 1
    assert concepts[0].name == "BP"


def test_parse_json_in_markdown_block(extractor):
    response = """
Some prefix text.

```json
[
  {"name": "Gradient Descent", "description": "optimizer", "relations": []}
]
```

Some suffix.
"""
    concepts = extractor.process_response(response, "book1")
    assert len(concepts) == 1
    assert concepts[0].name == "Gradient Descent"


def test_parse_json_in_unmarked_block(extractor):
    response = "```\n[{\"name\": \"X\", \"relations\": []}]\n```"
    concepts = extractor.process_response(response, "book1")
    assert len(concepts) == 1


def test_invalid_json_returns_empty(extractor):
    concepts = extractor.process_response("Not JSON at all", "book1")
    assert concepts == []


def test_skips_concepts_without_name(extractor):
    response = '[{"description": "no name"}, {"name": "Valid"}]'
    concepts = extractor.process_response(response, "book1")
    assert len(concepts) == 1
    assert concepts[0].name == "Valid"


def test_creates_relations_with_target_concepts(extractor):
    response = """[
        {
            "name": "A",
            "relations": [{"target": "B", "type": "RELATED_TO", "strength": 8}]
        }
    ]"""
    extractor.process_response(response, "book1")
    # B 应被自动创建作为关系目标
    assert extractor._graph.find_by_name("B") is not None
    assert len(extractor._graph.links) == 1
    link = extractor._graph.links[0]
    assert link.relation_type == "RELATED_TO"
    assert link.strength == 8


def test_dedup_across_calls(extractor):
    extractor.process_response('[{"name": "A"}]', "book1")
    extractor.process_response('[{"name": "A"}]', "book2")
    assert len(extractor._graph.concepts) == 1
    # source_books 合并
    a = extractor._graph.find_by_name("A")
    book_ids = {s["book_id"] for s in a.source_books}
    assert book_ids == {"book1", "book2"}


def test_object_response_returns_empty(extractor):
    """非数组的 JSON 不应被接受"""
    concepts = extractor.process_response('{"name": "X"}', "book1")
    assert concepts == []
