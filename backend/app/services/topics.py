"""The controlled topic vocabulary. OWNER: Member 1.

Why this is a hard constraint and not a suggestion
--------------------------------------------------
`topic_tag` is the join key for everything that makes this project more than a
quiz app: `topic_mastery`, the misconception behind a wrong answer, the
Teach-Back session that argues it out, and the roadmap that sequences what to
study next. All four find each other by tag and nothing else.

While every tag was typed by a human that was safe. It stops being safe the
moment a model is tagging generated content: asked to label a lesson about
INNER JOIN it will produce `sql.joins`, `dbms.joins`, `databases.inner_join` and
`dbms.sql_joins` across four calls, all meaning the same thing. Each becomes a
separate mastery row. A student's misconception about joins is then recorded
against a tag that nothing else will ever look up again, the map fragments into
singletons, and the whole model of "we are tracking this belief over time"
silently becomes false.

So generated tags are matched against this vocabulary and anything unmatched is
dropped, exactly as `roadmap_planner.validate_steps()` drops steps that name a
lesson which does not exist. Adding a tag is a deliberate act.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Iterable

from sqlalchemy.orm import Session

logger = logging.getLogger("learnquest.topics")


def _normalise(tag: str) -> str:
    """Lowercase, trim, collapse separators. Does not invent a namespace."""
    text = re.sub(r"[\s-]+", "_", str(tag or "").strip().lower())
    return re.sub(r"[^a-z0-9._]", "", text)


def active_tags(db: Session) -> list[str]:
    from app.models.ai import Topic

    rows = (
        db.query(Topic.tag)
        .filter(Topic.is_active.is_(True))
        .order_by(Topic.subject, Topic.tag)
        .all()
    )
    return [r[0] for r in rows]


def vocabulary(db: Session) -> list[dict[str, Any]]:
    """The full active vocabulary, for prompts and for the admin UI."""
    from app.models.ai import Topic

    rows = (
        db.query(Topic)
        .filter(Topic.is_active.is_(True))
        .order_by(Topic.subject, Topic.tag)
        .all()
    )
    return [r.to_dict() for r in rows]


def prompt_block(db: Session, subject: str | None = None) -> str:
    """The vocabulary formatted for a prompt: `tag - label`, one per line.

    A model given the list picks from it far more reliably than one told to
    "use a dotted tag", which is the whole reason this is passed in rather than
    described.
    """
    from app.models.ai import Topic

    query = db.query(Topic).filter(Topic.is_active.is_(True))
    if subject:
        query = query.filter(Topic.subject == subject)

    rows = query.order_by(Topic.subject, Topic.tag).all()
    return "\n".join(f"{r.tag} - {r.label}" for r in rows)


def resolve(db: Session, tags: Iterable[str]) -> list[str]:
    """Keep only tags that exist in the vocabulary, normalised and deduped.

    Returns an empty list rather than raising: a lesson with no recognised tag
    is a lesson the mastery model cannot track, and the caller decides whether
    that is worth rejecting. Silently inventing a tag to avoid an empty list
    would be the worst of the available options.
    """
    known = set(active_tags(db))
    out: list[str] = []
    for raw in tags or []:
        tag = _normalise(raw)
        if tag in known and tag not in out:
            out.append(tag)
        elif tag and tag not in known:
            logger.info("Dropped unknown topic tag %r from generated content", raw)
    return out


def is_known(db: Session, tag: str) -> bool:
    return _normalise(tag) in set(active_tags(db))
