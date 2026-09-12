# LearnQuest AI — Gamification & Event Bus Technical Guide

**Module:** Member 4 — Gamification & Analytics  
**Sprint:** Week 1  
**Status:** Implemented & Verified  
**References:** [plan.md §4.3, §9.1–9.3](file:///Users/oni/Documents/GitHub/LearnQuest-Ai/plan.md#L446-L465)

---

## 1. Architectural Overview & Event Flow

The LearnQuest AI Event Bus provides an isolated, asynchronous/synchronous best-effort decoupling layer between domain modules (AI/Tutor, LMS/Courses, Auth/User) and motivation mechanics (Gamification/Analytics).

```
Application Action (Lesson completion, Quiz submission, Enrollment, etc.)
  │
  ▼
emit(db, user_id, event_type, payload)   ─── [backend/app/services/events.py]
  │
  ├─► Try/Except Failure Isolation (handler failure never breaks caller)
  │
  ▼
Registered Event Handler                 ─── [@register_handler in services/xp_engine.py]
  │
  ├─► Deduplication & Idempotency Check
  ├─► Daily Caps Check (e.g. Tutor XP cap: 25 XP/day)
  │
  ▼
XP Engine: award_xp()
  │
  ├─► Mutates `user_stats` (xp, level, streaks, learning time)
  └─► Records immutable row in `xp_events` ledger (source of truth)
```

---

## 2. Event Specifications & Payloads

| Event Name | Emitting Module | Trigger / Action | Expected Payload | XP Award |
| :--- | :--- | :--- | :--- | :--- |
| `lesson.completed` | Member 2 (LMS) | Learner completes lesson | `{"lesson_id": "...", "course_id": "...", "seconds": 120}` | +50 XP |
| `quiz.submitted` | Member 2 (LMS) | Quiz submitted & graded | `{"quiz_id": "...", "attempt_id": "...", "correct_count": 3, "total_questions": 5}` | 10 base + (5 × correct) + (25 if 100%) |
| `course.enrolled` | Member 2 / 3 | User enrolls in a course | `{"course_id": "..."}` | +20 XP |
| `tutor.session` | Member 1 (AI) | Conversation reaches milestone | `{"conversation_id": "...", "message_count": 3}` | +5 XP (max 25 XP/day) |
| `daily.login` | Member 3 (Auth) | First login / request of day | `{"date": "YYYY-MM-DD"}` (or `{}`) | +10 XP + streak bonus |
| `quiz.generated` | Member 1 (AI) | AI generates a quiz | `{"quiz_id": "...", "topic": "..."}` | Supported on Event Bus |

---

## 3. XP Rules & Level Curve

### XP Rules
- **Lesson Completed:** `+50 XP`
- **Quiz Submitted:**
  - `+10 XP` base participation
  - `+5 XP` per correct answer
  - `+25 XP` perfect score bonus ($100\%$ score)
  - *Example 1:* 3/5 correct $\rightarrow$ $10 + (3 \times 5) = 25\text{ XP}$
  - *Example 2:* 5/5 correct (perfect) $\rightarrow$ $10 + (5 \times 5) + 25 = 60\text{ XP}$
- **Course Enrolled:** `+20 XP`
- **Tutor Session:** `+5 XP` per session, capped at `25 XP/day` across all sessions.
- **Daily Login:** `+10 XP` + Streak bonus (`+5 × min(current_streak, 10)`).

### Level Formula
$$\text{XP threshold for level } n = 100 \times n^{1.5}$$

- **Level 1:** $0\text{ to }282\text{ XP}$ (starting baseline)
- **Level 2:** $283\text{ XP}$
- **Level 5:** $1118\text{ XP}$
- **Level 10:** $3162\text{ XP}$

Implemented in `xp_engine.py`:
- `xp_for_level(n)`: returns cumulative threshold for level $n$.
- `level_from_xp(xp)` (and alias `level_for_xp`): calculates level for given cumulative XP.

---

## 4. How Team Members Emit Events Safely

Other team members do **NOT** need to import `xp_engine.py` or know about `user_stats`. Only import `emit`:

```python
from app.services.events import emit

# Inside an authenticated endpoint (db is Session from Depends(get_db)):
emit(
    db=db,
    user_id=current_user["id"],   # Always use authenticated user, NEVER client body
    event_type="lesson.completed",
    payload={
        "lesson_id": str(lesson.id),
        "course_id": str(course.id),
        "seconds": 180,
    },
)
```

### Safety Guarantees:
1. **Zero Caller Disruption:** If a gamification handler raises any database error or unexpected exception, `emit()` logs the exception and swallows it. Your HTTP request will **never** return a 500 because of an XP engine or badge issue.
2. **Atomic DB Transactions:** All XP and ledger mutations execute inside a protected database transaction (`db.commit()`), with automatic rollback (`db.rollback()`) on errors.
3. **No Circular Dependencies:** `events.py` has no internal imports into models or routers.

---

## 5. Duplication Protection & Idempotency

- **`lesson.completed`:** Deduplicated by `(user_id, 'lesson.completed', lesson_id)`. Retrying the same lesson completion does not award double XP.
- **`quiz.submitted`:** Deduplicated by `attempt_id`.
- **`course.enrolled`:** Deduplicated by `course_id`.
- **`daily.login`:** Deduplicated by `(user_id, 'daily.login', calendar_date)`.
- **`tutor.session`:** Bounded by the strict $25\text{ XP/day}$ cap.

### Known Limitations & Week 2 Recommendations
- **Multiple tutor sessions within one long conversation:** When multiple milestone tutor events occur in a single ongoing conversation, passing only `conversation_id` as `ref_id` would deduplicate after the first session. The current implementation bounds tutor XP safely using the daily $25\text{ XP}$ cap.
- **Recommendation for Week 2:** Member 1's tutor service can pass a distinct milestone turn ID or `session_id` in `payload["session_id"]` to enable granular per-milestone deduplication.

---

## 6. Verification & Test Execution

Run the complete test suite:

```bash
cd backend
.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v
```

All 27 unit and scenario tests pass cleanly.
