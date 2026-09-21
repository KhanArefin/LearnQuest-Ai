"""Builds and re-plans a student's roadmap graph.

OWNER: Member 1. See plan.md 6.x.

The LLM does not invent the curriculum. It is given the *actual* published
lessons and the controlled topic vocabulary, and asked only to select and order
them for a goal. Anything it returns that does not match a real topic tag is
discarded, so a hallucinated skill can never reach a student's plan.

If the model is unavailable or returns nothing usable, `fallback_plan` produces
a deterministic ordering from course/lesson order. The feature therefore always
works offline - which matters for a live demo.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.ai import TopicMastery
from app.models.course import Course, Lesson
from app.services.llm_client import get_llm

logger = logging.getLogger("learnquest.roadmap")

MAX_NODES = 12
MIN_NODES = 4

ROADMAP_PROMPT = """You are LearnQuest's curriculum planner.

A student's goal:
"{goal}"
Time available: about {weeks} weeks.

These are the ONLY skills available. Use their exact `tag` values:
{catalogue}

The student's current mastery (0.0 = new, 1.0 = mastered):
{mastery}

Design a learning roadmap of {lo}-{hi} steps.

Rules:
- Use ONLY tags from the list above. Never invent a tag.
- Order from foundations to advanced.
- Skip or lightly cover skills the student has already mastered (>0.75).
- `depends_on` lists the `key` values of steps that must come first. Use [] for
  the first step. Only reference keys that appear EARLIER in your list.
- `title` is a short quest name a student would enjoy seeing (max 60 chars).
- `summary` is one sentence on what they will be able to do afterwards.

Return ONLY valid JSON, no markdown fence:
{{"steps": [
  {{"key": "slug-like-id", "title": "...", "summary": "...",
    "tag": "exact.tag.from.list", "depends_on": []}}
]}}"""


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return slug[:60] or "step"


def build_catalogue(db: Session) -> dict[str, dict[str, Any]]:
    """Every topic tag a published lesson actually teaches.

    Maps tag -> {tag, lesson_id, lesson_title, course_title, minutes, order}.
    This is the grounding set: the planner cannot go outside it.
    """
    catalogue: dict[str, dict[str, Any]] = {}

    rows = (
        db.query(Lesson, Course)
        .join(Course, Lesson.course_id == Course.id)
        .filter(Course.is_published.is_(True))
        .order_by(Course.created_at.asc(), Lesson.order_index.asc())
        .all()
    )

    for position, (lesson, course) in enumerate(rows):
        for tag in lesson.topic_tags or []:
            # First lesson to teach a tag owns it - they are ordered by course
            # then lesson index, so this is the earliest introduction.
            if tag in catalogue:
                continue
            catalogue[tag] = {
                "tag": tag,
                "lesson_id": lesson.id,
                "lesson_title": lesson.title,
                "course_title": course.title,
                "minutes": lesson.estimated_minutes or 20,
                "order": position,
            }

    return catalogue


def get_mastery(db: Session, user_id: uuid.UUID) -> dict[str, float]:
    rows = db.query(TopicMastery).filter(TopicMastery.user_id == user_id).all()
    return {r.topic_tag: float(r.mastery_score or 0.0) for r in rows}


def fallback_plan(
    catalogue: dict[str, dict[str, Any]],
    mastery: dict[str, float],
) -> list[dict[str, Any]]:
    """Deterministic plan: curriculum order, mastered topics last.

    Used when the LLM is unavailable or returns nothing usable, so the roadmap
    feature degrades instead of failing.
    """
    entries = sorted(catalogue.values(), key=lambda e: e["order"])
    # Push already-mastered skills to the end rather than dropping them: a plan
    # that silently omits topics is confusing.
    entries.sort(key=lambda e: mastery.get(e["tag"], 0.0) > 0.75)

    steps: list[dict[str, Any]] = []
    previous_key: str | None = None
    for entry in entries[:MAX_NODES]:
        key = _slugify(entry["tag"])
        steps.append(
            {
                "key": key,
                "title": entry["lesson_title"],
                "summary": f"Work through {entry['lesson_title']} from {entry['course_title']}.",
                "tag": entry["tag"],
                "depends_on": [previous_key] if previous_key else [],
            }
        )
        previous_key = key
    return steps


def _extract_json(raw: str) -> dict[str, Any] | None:
    """Parse the model's reply, tolerating a ```json fence or stray prose."""
    if not raw:
        return None
    text = raw.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fall back to the outermost {...} block.
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def validate_steps(
    steps: Any,
    catalogue: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep only steps that reference real skills and form a valid DAG.

    Drops: unknown tags, duplicates, malformed entries, and dependency edges
    that point at a step we did not keep (which also makes cycles impossible,
    since every edge must point strictly backwards).
    """
    if not isinstance(steps, list):
        return []

    cleaned: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    seen_tags: set[str] = set()

    for raw in steps:
        if not isinstance(raw, dict):
            continue

        tag = str(raw.get("tag", "")).strip()
        if tag not in catalogue or tag in seen_tags:
            continue  # hallucinated or duplicate skill

        key = _slugify(raw.get("key") or tag)
        if key in seen_keys:
            key = f"{key}-{len(cleaned) + 1}"

        depends_raw = raw.get("depends_on") or []
        if not isinstance(depends_raw, list):
            depends_raw = []
        # Only backwards edges to steps we actually kept.
        depends = [_slugify(d) for d in depends_raw if _slugify(d) in seen_keys]

        title = str(raw.get("title") or catalogue[tag]["lesson_title"]).strip()[:200]
        summary = str(raw.get("summary") or "").strip()[:500] or None

        cleaned.append(
            {
                "key": key,
                "title": title,
                "summary": summary,
                "tag": tag,
                "depends_on": depends,
            }
        )
        seen_keys.add(key)
        seen_tags.add(tag)

        if len(cleaned) >= MAX_NODES:
            break

    return cleaned


async def generate_steps(
    db: Session,
    user_id: uuid.UUID,
    goal: str,
    weeks: int,
) -> tuple[list[dict[str, Any]], str, dict[str, dict[str, Any]]]:
    """Return (steps, generated_by, catalogue)."""
    catalogue = build_catalogue(db)
    if not catalogue:
        return [], "empty", catalogue

    mastery = get_mastery(db, user_id)

    catalogue_lines = "\n".join(
        f"- tag: {e['tag']} | {e['lesson_title']} ({e['course_title']}, ~{e['minutes']}m)"
        for e in sorted(catalogue.values(), key=lambda x: x["order"])
    )
    mastery_lines = (
        "\n".join(f"- {tag}: {score:.2f}" for tag, score in sorted(mastery.items()))
        or "- (no history yet - treat as a complete beginner)"
    )

    prompt = ROADMAP_PROMPT.format(
        goal=goal.strip(),
        weeks=weeks,
        catalogue=catalogue_lines,
        mastery=mastery_lines,
        lo=MIN_NODES,
        hi=MAX_NODES,
    )

    try:
        raw = await get_llm().complete(
            [{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1600,
            json_mode=True,
        )
        payload = _extract_json(raw)
        steps = validate_steps((payload or {}).get("steps"), catalogue)
        if len(steps) >= MIN_NODES:
            return steps, "llm", catalogue
        logger.warning(
            "Roadmap LLM returned %d usable steps (min %d); using fallback.",
            len(steps),
            MIN_NODES,
        )
    except Exception as exc:  # noqa: BLE001 - never fail the request over this
        logger.error("Roadmap generation failed, using fallback: %s", exc)

    return fallback_plan(catalogue, mastery), "fallback", catalogue


def decorate_nodes(nodes: list[Any]) -> list[dict[str, Any]]:
    """Attach derived lock state to serialised nodes.

    A node is `completed` if it has a completion timestamp, `available` once
    every dependency is complete, and `locked` otherwise. Deriving this rather
    than storing it means re-planning can never leave stale state behind.
    """
    serialised = [n.to_dict() for n in nodes]
    done = {n["node_key"] for n in serialised if n["is_completed"]}

    for node in serialised:
        if node["is_completed"]:
            node["status"] = "completed"
        elif all(dep in done for dep in node["depends_on"]):
            node["status"] = "available"
        else:
            node["status"] = "locked"
        node["blocked_by"] = [d for d in node["depends_on"] if d not in done]

    return serialised


# --------------------------------------------------------------------------- #
# XP integration
# --------------------------------------------------------------------------- #
# Registered here rather than in xp_engine.py so the roadmap feature owns its
# own side effects (xp_engine.py belongs to Member 4). `register_handler`
# accepts new event types and adds them to EVENT_TYPES, which is the documented
# extension point - see app/services/events.py.

from app.services.events import register_handler  # noqa: E402


@register_handler("roadmap.node_completed")
def on_roadmap_node_completed(db: Any, user_id: Any, payload: dict[str, Any]) -> Any:
    """Credit the quest's XP to user_stats via the normal XP pipeline.

    Routed through award_xp rather than touching user_stats directly so the
    immutable xp_events audit row is always written (xp_engine.py's stated
    critical rule), and levels/streaks update the same way as every other
    XP source.
    """
    from app.services.xp_engine import award_xp

    amount = int(payload.get("xp") or 0)
    if amount <= 0:
        return None

    return award_xp(
        db=db,
        user_id=user_id,
        amount=amount,
        reason="roadmap.node_completed",
        event_type="roadmap.node_completed",
        ref_type="roadmap_node",
        ref_id=payload.get("node_id"),
        metadata={"topic_tag": payload.get("topic_tag")},
    )
