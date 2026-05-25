"""GraphEngine 测试 — CRUD、去重合并、邻居、布局"""

from __future__ import annotations

import pytest

from knowledge.graph_engine import GraphEngine
from knowledge.models import Concept, ConceptLink


@pytest.fixture
def engine(tmp_storage):
    return GraphEngine(tmp_storage)


def test_empty_engine(engine):
    assert engine.concepts == []
    assert engine.links == []


def test_add_concept(engine):
    c = engine.add_concept(Concept(name="反向传播"))
    assert engine.get_concept(c.id).name == "反向传播"
    assert len(engine.concepts) == 1


def test_add_concept_dedup_by_name(engine):
    c1 = engine.add_concept(Concept(name="Backprop", source_books=[{"book_id": "b1"}]))
    c2 = engine.add_concept(Concept(name="Backprop", source_books=[{"book_id": "b2"}]))
    # 应返回同一对象，source_books 合并
    assert c1.id == c2.id
    assert len(engine.concepts) == 1
    assert {s["book_id"] for s in c1.source_books} == {"b1", "b2"}


def test_add_concept_dedup_by_alias(engine):
    c1 = engine.add_concept(Concept(name="反向传播", aliases=["BP", "backprop"]))
    c2 = engine.add_concept(Concept(name="BP"))
    assert c2.id == c1.id


def test_add_concept_case_insensitive(engine):
    c1 = engine.add_concept(Concept(name="Gradient"))
    c2 = engine.add_concept(Concept(name="gradient"))
    assert c1.id == c2.id


def test_add_link(engine):
    a = engine.add_concept(Concept(name="A"))
    b = engine.add_concept(Concept(name="B"))
    link = engine.add_link(ConceptLink(source_id=a.id, target_id=b.id))
    assert link in engine.links


def test_add_link_skipped_when_concept_missing(engine):
    a = engine.add_concept(Concept(name="A"))
    link = engine.add_link(ConceptLink(source_id=a.id, target_id="missing"))
    # 链接不会被添加
    assert link not in engine.links


def test_remove_concept_cleans_links(engine):
    a = engine.add_concept(Concept(name="A"))
    b = engine.add_concept(Concept(name="B"))
    engine.add_link(ConceptLink(source_id=a.id, target_id=b.id))
    engine.remove_concept(a.id)
    assert engine.get_concept(a.id) is None
    assert all(link.source_id != a.id and link.target_id != a.id for link in engine.links)


def test_neighbors(engine):
    a = engine.add_concept(Concept(name="A"))
    b = engine.add_concept(Concept(name="B"))
    c = engine.add_concept(Concept(name="C"))
    engine.add_link(ConceptLink(source_id=a.id, target_id=b.id))
    engine.add_link(ConceptLink(source_id=b.id, target_id=c.id))
    n1 = {n.name for n in engine.neighbors(a.id, depth=1)}
    n2 = {n.name for n in engine.neighbors(a.id, depth=2)}
    assert n1 == {"B"}
    assert n2 == {"B", "C"}


def test_concepts_for_book(engine):
    engine.add_concept(Concept(name="A", source_books=[{"book_id": "b1"}]))
    engine.add_concept(Concept(name="B", source_books=[{"book_id": "b2"}]))
    b1_concepts = engine.concepts_for_book("b1")
    assert len(b1_concepts) == 1
    assert b1_concepts[0].name == "A"


def test_compute_layout(engine):
    a = engine.add_concept(Concept(name="A"))
    b = engine.add_concept(Concept(name="B"))
    engine.add_link(ConceptLink(source_id=a.id, target_id=b.id))
    pos = engine.compute_layout([a.id, b.id])
    assert a.id in pos
    assert b.id in pos
    assert all(isinstance(p, tuple) and len(p) == 2 for p in pos.values())


def test_compute_layout_empty(engine):
    assert engine.compute_layout([]) == {}


def test_save_and_reload(engine, tmp_storage):
    a = engine.add_concept(Concept(name="A"))
    b = engine.add_concept(Concept(name="B"))
    engine.add_link(ConceptLink(source_id=a.id, target_id=b.id))
    engine.save()

    # 新引擎重新加载
    engine2 = GraphEngine(tmp_storage)
    assert len(engine2.concepts) == 2
    assert len(engine2.links) == 1
