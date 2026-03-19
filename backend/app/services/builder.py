from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Chunk, Document, DocumentTopic, Topic, TopicRule
from app.services.openai_client import chat_markdown, embed_texts
from app.routes.schemas import BuilderCitation, CompareRequest, CompareResponse, ReimplementRequest, ReimplementResponse


def reimplement_brief(db: Session, payload: ReimplementRequest) -> ReimplementResponse:
    if payload.k < 1 or payload.k > 50:
        raise ValueError("k must be between 1 and 50")

    rows = _retrieve_reimplementation_rows(db=db, payload=payload)
    rows = _diversify_rows(rows=rows, limit=payload.k)
    if not rows:
        return ReimplementResponse(plan_md="No supporting context found.", citations=[])

    context_blocks = _rows_to_context_blocks(rows)
    constraints = payload.constraints.model_dump(exclude_none=True) if payload.constraints else {}
    system_prompt = (
        "You are a builder's assistant. Produce an implementation brief grounded only in supplied context. "
        "Use markdown and include these exact sections: Overview, Key idea, Data/benchmarks, "
        "Baseline implementation plan, Training recipe, Evaluation plan, Ablations, "
        "Pitfalls/failure modes, Sanity checks, References."
    )
    user_prompt = (
        f"Goal: {payload.goal}\n"
        f"Constraints: {constraints}\n"
        f"Topic: {payload.topic or 'none'}\n"
        f"Paper ID: {payload.paper_id or 'none'}\n\n"
        "Use bracketed inline references like [1], [2] tied to context blocks.\n\n"
        "Context:\n"
        + "\n\n".join(context_blocks)
    )
    plan_md = chat_markdown(system_prompt=system_prompt, user_prompt=user_prompt)
    plan_md = _ensure_reimplement_sections(plan_md)
    citations = _rows_to_citations(rows)
    return ReimplementResponse(plan_md=plan_md, citations=citations)


def compare_brief(db: Session, payload: CompareRequest) -> CompareResponse:
    if payload.k < 1 or payload.k > 50:
        raise ValueError("k must be between 1 and 50")

    rows_a, label_a = _retrieve_selector_rows(db=db, selector=payload.a.model_dump(), k=payload.k)
    rows_b, label_b = _retrieve_selector_rows(db=db, selector=payload.b.model_dump(), k=payload.k)

    rows_a = _diversify_rows(rows_a, payload.k)
    rows_b = _diversify_rows(rows_b, payload.k)

    if not rows_a and not rows_b:
        return CompareResponse(comparison_md="No context found for either side.", citations=[])

    system_prompt = (
        "You compare research directions. Output markdown with: "
        "(1) concise summary, "
        "(2) a markdown table with columns: Dimension | A | B, and rows for data, method, compute, evaluation, maturity, "
        "(3) a 'Which to implement first' recommendation based on constraints. "
        "Ground claims in provided context and cite references as [A1], [B2], etc."
    )
    constraints = payload.constraints.model_dump(exclude_none=True) if payload.constraints else {}
    user_prompt = (
        f"Compare A ({label_a}) vs B ({label_b}).\n"
        f"Constraints: {constraints}\n\n"
        "Context A:\n"
        + "\n\n".join(_rows_to_context_blocks(rows_a, prefix="A"))
        + "\n\nContext B:\n"
        + "\n\n".join(_rows_to_context_blocks(rows_b, prefix="B"))
    )
    comparison_md = chat_markdown(system_prompt=system_prompt, user_prompt=user_prompt)
    comparison_md = _ensure_compare_table(comparison_md)

    merged_rows = _merge_unique_rows(rows_a + rows_b)
    citations = _rows_to_citations(merged_rows)
    return CompareResponse(comparison_md=comparison_md, citations=citations)


def _retrieve_reimplementation_rows(db: Session, payload: ReimplementRequest) -> list[tuple[Chunk, Document, float, bool]]:
    if payload.paper_id:
        return _retrieve_for_paper(db=db, paper_id=payload.paper_id, goal=payload.goal, topic=payload.topic, k=payload.k)

    topic = payload.topic
    if not topic:
        inferred_topic = _infer_topic_from_goal(db=db, goal=payload.goal)
        topic = inferred_topic.name if inferred_topic else None

    return _retrieve_for_query(db=db, query=payload.goal, topic=topic, k=payload.k)


def _retrieve_selector_rows(db: Session, selector: dict, k: int) -> tuple[list[tuple[Chunk, Document, float, bool]], str]:
    paper_id = selector.get("paper_id")
    topic = selector.get("topic")
    if paper_id:
        rows = _retrieve_for_paper(db=db, paper_id=paper_id, goal="comparison context", topic=topic, k=k)
        return rows, f"paper_id={paper_id}"
    if topic:
        rows = _retrieve_for_query(db=db, query=topic, topic=topic, k=k)
        return rows, f"topic={topic}"
    raise ValueError("Each compare selector must provide topic or paper_id")


def _retrieve_for_query(db: Session, query: str, topic: str | None, k: int) -> list[tuple[Chunk, Document, float, bool]]:
    topic_obj = _resolve_topic(db=db, topic=topic) if topic else None
    query_embedding = embed_texts([query])[0]

    rows = _vector_rows(db=db, query_embedding=query_embedding, k=k, topic_id=topic_obj.id if topic_obj else None)
    merged = [(chunk, doc, float(score), topic_obj is not None) for chunk, doc, score in rows]

    if len(merged) < k:
        merged = _add_keyword_fallback(
            db=db,
            rows=merged,
            query=query,
            k=k,
            topic_id=topic_obj.id if topic_obj else None,
        )

    return merged[:k]


def _retrieve_for_paper(
    db: Session,
    paper_id: str,
    goal: str,
    topic: str | None,
    k: int,
) -> list[tuple[Chunk, Document, float, bool]]:
    doc_uuid = UUID(paper_id)
    paper = db.execute(select(Document).where(Document.id == doc_uuid)).scalar_one_or_none()
    if paper is None:
        raise ValueError(f"Unknown paper_id: {paper_id}")

    explicit_topic = _resolve_topic(db=db, topic=topic) if topic else None
    inferred_topic_id = explicit_topic.id if explicit_topic else _first_topic_id_for_document(db=db, document_id=paper.id)

    base_rows = db.execute(
        select(Chunk, Document)
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.id == paper.id)
        .order_by(Chunk.chunk_index.asc())
        .limit(max(2, k // 2))
    ).all()
    merged: list[tuple[Chunk, Document, float, bool]] = [(chunk, doc, 1.0, True) for chunk, doc in base_rows]

    query_embedding = embed_texts([goal])[0]
    neighbor_rows = _vector_rows(
        db=db,
        query_embedding=query_embedding,
        k=k * 3,
        topic_id=inferred_topic_id,
        source=paper.source,
        exclude_document_id=paper.id,
    )
    merged.extend((chunk, doc, float(score), inferred_topic_id is not None) for chunk, doc, score in neighbor_rows)

    if len(merged) < k:
        global_rows = _vector_rows(
            db=db,
            query_embedding=query_embedding,
            k=k * 3,
            topic_id=inferred_topic_id,
        )
        existing_chunk_ids = {chunk.id for chunk, _doc, _score, _topic_match in merged}
        for chunk, doc, score in global_rows:
            if chunk.id in existing_chunk_ids:
                continue
            merged.append((chunk, doc, float(score), inferred_topic_id is not None))
            if len(merged) >= k:
                break

    return merged[:k]


def _vector_rows(
    db: Session,
    query_embedding: list[float],
    k: int,
    topic_id: UUID | None = None,
    source: str | None = None,
    exclude_document_id: UUID | None = None,
) -> list[tuple[Chunk, Document, float]]:
    distance = Chunk.embedding.cosine_distance(query_embedding)
    score = (1 - distance).label("score")

    stmt = select(Chunk, Document, score).join(Document, Chunk.document_id == Document.id)
    if topic_id:
        stmt = stmt.join(DocumentTopic, DocumentTopic.document_id == Document.id).where(DocumentTopic.topic_id == topic_id)
    if source:
        stmt = stmt.where(Document.source == source)
    if exclude_document_id:
        stmt = stmt.where(Document.id != exclude_document_id)

    return db.execute(stmt.order_by(distance).limit(k)).all()


def _add_keyword_fallback(
    db: Session,
    rows: list[tuple[Chunk, Document, float, bool]],
    query: str,
    k: int,
    topic_id: UUID | None,
) -> list[tuple[Chunk, Document, float, bool]]:
    existing_chunk_ids = {chunk.id for chunk, _doc, _score, _topic_match in rows}
    terms = [term.strip().lower() for term in query.split() if len(term.strip()) >= 4][:5]
    if not terms:
        return rows

    conditions = [Chunk.text.ilike(f"%{term}%") for term in terms]
    stmt = select(Chunk, Document).join(Document, Chunk.document_id == Document.id).where(or_(*conditions))
    if topic_id:
        stmt = stmt.join(DocumentTopic, DocumentTopic.document_id == Document.id).where(DocumentTopic.topic_id == topic_id)

    keyword_rows = db.execute(stmt.limit(k * 3)).all()
    merged = rows[:]
    for chunk, doc in keyword_rows:
        if chunk.id in existing_chunk_ids:
            continue
        merged.append((chunk, doc, 0.25, topic_id is not None))
        existing_chunk_ids.add(chunk.id)
        if len(merged) >= k:
            break
    return merged


def _infer_topic_from_goal(db: Session, goal: str) -> Topic | None:
    goal_text = goal.lower()
    topic_rows = db.execute(select(TopicRule, Topic).join(Topic, TopicRule.topic_id == Topic.id)).all()

    best_topic: Topic | None = None
    best_score = 0
    for rule, topic in topic_rows:
        score = 0
        for keyword in rule.include_keywords or []:
            if keyword and keyword.lower() in goal_text:
                score += 1
        if topic.name.lower() in goal_text:
            score += 2
        if score > best_score:
            best_score = score
            best_topic = topic

    return best_topic if best_score > 0 else None


def _resolve_topic(db: Session, topic: str) -> Topic:
    topic = topic.strip()
    topic_uuid: UUID | None = None
    try:
        topic_uuid = UUID(topic)
    except ValueError:
        topic_uuid = None

    if topic_uuid is not None:
        found = db.execute(select(Topic).where(Topic.id == topic_uuid)).scalar_one_or_none()
    else:
        found = db.execute(select(Topic).where(Topic.name.ilike(topic))).scalar_one_or_none()
    if found is None:
        raise ValueError(f"Unknown topic: {topic}")
    return found


def _first_topic_id_for_document(db: Session, document_id: UUID) -> UUID | None:
    return db.execute(
        select(DocumentTopic.topic_id)
        .where(DocumentTopic.document_id == document_id)
        .order_by(DocumentTopic.confidence.desc())
        .limit(1)
    ).scalar_one_or_none()


def _diversify_rows(rows: list[tuple[Chunk, Document, float, bool]], limit: int) -> list[tuple[Chunk, Document, float, bool]]:
    first_pass: list[tuple[Chunk, Document, float, bool]] = []
    used_documents: set[UUID] = set()
    used_chunks: set[UUID] = set()

    for row in rows:
        chunk, doc, _score, _topic_match = row
        if doc.id in used_documents:
            continue
        first_pass.append(row)
        used_documents.add(doc.id)
        used_chunks.add(chunk.id)
        if len(first_pass) >= limit:
            return first_pass

    for row in rows:
        chunk, _doc, _score, _topic_match = row
        if chunk.id in used_chunks:
            continue
        first_pass.append(row)
        used_chunks.add(chunk.id)
        if len(first_pass) >= limit:
            break

    return first_pass


def _rows_to_context_blocks(rows: list[tuple[Chunk, Document, float, bool]], prefix: str = "") -> list[str]:
    blocks = []
    for idx, (chunk, doc, score, topic_match) in enumerate(rows, start=1):
        label = f"{prefix}{idx}" if prefix else str(idx)
        blocks.append(
            f"[{label}] {doc.title}\n"
            f"Source: {doc.source}\n"
            f"URL: {doc.url}\n"
            f"Score: {score:.4f}\n"
            f"TopicMatch: {topic_match}\n"
            f"Snippet: {chunk.text[:350]}"
        )
    return blocks


def _rows_to_citations(rows: list[tuple[Chunk, Document, float, bool]]) -> list[BuilderCitation]:
    return [
        BuilderCitation(
            document_id=doc.id,
            title=doc.title,
            url=doc.url,
            source=doc.source,
            chunk_id=chunk.id,
            snippet=chunk.text[:350],
        )
        for chunk, doc, _score, _topic_match in rows
    ]


def _merge_unique_rows(rows: list[tuple[Chunk, Document, float, bool]]) -> list[tuple[Chunk, Document, float, bool]]:
    merged: list[tuple[Chunk, Document, float, bool]] = []
    seen_chunks: set[UUID] = set()
    for row in rows:
        chunk, _doc, _score, _topic_match = row
        if chunk.id in seen_chunks:
            continue
        seen_chunks.add(chunk.id)
        merged.append(row)
    return merged


# TODO(export as zip): package selected references and notes into downloadable bundles.
# TODO(project scaffolds): generate starter project structures from reimplementation plans.
# TODO(evaluation harness): emit reusable eval harness templates per task.


def _ensure_reimplement_sections(markdown: str) -> str:
    required = [
        "## Overview",
        "## Key idea",
        "## Data/benchmarks",
        "## Baseline implementation plan",
        "## Training recipe",
        "## Evaluation plan",
        "## Ablations",
        "## Pitfalls/failure modes",
        "## Sanity checks",
        "## References",
    ]
    output = markdown
    for header in required:
        if header not in output:
            output += f"\n\n{header}\n- TODO: fill from retrieved context."
    return output


def _ensure_compare_table(markdown: str) -> str:
    if "| Dimension | A | B |" in markdown:
        return markdown
    table = (
        "\n\n| Dimension | A | B |\n"
        "|---|---|---|\n"
        "| data | TODO | TODO |\n"
        "| method | TODO | TODO |\n"
        "| compute | TODO | TODO |\n"
        "| evaluation | TODO | TODO |\n"
        "| maturity | TODO | TODO |\n"
    )
    return markdown + table
