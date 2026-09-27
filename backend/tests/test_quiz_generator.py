"""AI quiz generation: validation, personalisation and persistence.

The validation tests carry most of the weight. A generated quiz that is merely
*wrong* is caught by anyone reading it; the failures that matter are the ones
that produce a quiz which looks perfectly normal and grades incorrectly - an
mcq whose answer is not among its options can never be answered right, and a
duplicated prompt makes one misunderstanding cost two marks.
"""

from __future__ import annotations

import json
import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.ai import GenerationJob, Topic, TopicMastery
from app.models.course import Course, Lesson
from app.models.quiz import Question, Quiz
from app.models.user import User
from app.services import quiz_generator as qg


def _run(coro):
    import asyncio

    return asyncio.run(coro)


class _FakeLLM:
    def __init__(self, reply):
        self.reply = reply
        self.prompts = []

    async def complete(self, messages, **kwargs):
        self.prompts.append(messages[0]["content"])
        return self.reply


class _DeadLLM:
    async def complete(self, messages, **kwargs):
        raise RuntimeError("provider down")


TAGS = [
    ("dbms.sql_joins", "SQL joins", "dbms"),
    ("dbms.er_model", "ER model and keys", "dbms"),
    ("python.loops", "Loops and iteration", "python"),
]


class GeneratorBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self) -> None:
        self.db = self.Session()
        self.user_id = uuid.uuid4()
        self.db.add(
            User(id=self.user_id, email=f"{self.user_id.hex[:8]}@t.local", full_name="T")
        )
        for tag, label, subject in TAGS:
            self.db.add(Topic(tag=tag, label=label, subject=subject, is_active=True))

        self.course = Course(
            id=uuid.uuid4(), slug=f"c-{uuid.uuid4().hex[:6]}", title="DBMS", is_published=True
        )
        self.lesson = Lesson(
            id=uuid.uuid4(),
            course_id=self.course.id,
            title="Joins",
            order_index=0,
            content_md="An INNER JOIN keeps only matching rows.",
            topic_tags=["dbms.sql_joins"],
        )
        self.db.add_all([self.course, self.lesson])
        self.db.commit()

    def tearDown(self) -> None:
        self.db.rollback()
        for model in (
            GenerationJob, Question, Quiz, TopicMastery, Lesson, Course, Topic, User
        ):
            self.db.query(model).delete()
        self.db.commit()
        self.db.close()

    def _mastery(self, tag: str, score: float, misconception: str | None = None):
        row = TopicMastery(
            user_id=self.user_id,
            topic_tag=tag,
            mastery_score=score,
            misconception=misconception,
            misconception_updated_at=datetime.now(timezone.utc) if misconception else None,
            misconception_correct_streak=0,
            attempts=4,
            correct=1,
        )
        self.db.add(row)
        self.db.commit()
        return row


class TestDifficulty(GeneratorBase):
    def test_difficulty_follows_mastery(self) -> None:
        self.assertEqual(qg.difficulty_for(0.1), "easy")
        self.assertEqual(qg.difficulty_for(0.39), "easy")
        self.assertEqual(qg.difficulty_for(0.4), "medium")
        self.assertEqual(qg.difficulty_for(0.75), "medium")
        self.assertEqual(qg.difficulty_for(0.9), "hard")

    def test_no_history_is_medium_not_easy(self) -> None:
        """A new learner is not assumed to be weak."""
        self.assertEqual(qg.difficulty_for(None), "medium")


class TestValidation(GeneratorBase):
    def _validate(self, questions, types=("mcq", "true_false"), limit=5):
        return qg.validate_questions(self.db, questions, ["dbms.sql_joins"], types, limit)

    def test_mcq_whose_answer_is_not_an_option_is_dropped(self) -> None:
        """The failure that matters: it looks fine and cannot be answered."""
        out = self._validate(
            [
                {
                    "type": "mcq",
                    "prompt": "Which join keeps only matching rows?",
                    "options": ["LEFT JOIN", "FULL OUTER JOIN"],
                    "correct_answer": "INNER JOIN",
                    "topic_tag": "dbms.sql_joins",
                }
            ]
        )
        self.assertEqual(out, [])

    def test_answer_matching_an_option_by_case_is_repaired(self) -> None:
        out = self._validate(
            [
                {
                    "type": "mcq",
                    "prompt": "Which join keeps only matching rows?",
                    "options": ["INNER JOIN", "LEFT JOIN"],
                    "correct_answer": "inner join",
                    "topic_tag": "dbms.sql_joins",
                }
            ]
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["correct_answer"], "INNER JOIN")

    def test_duplicate_prompts_are_dropped(self) -> None:
        """One misunderstanding must not be able to cost two marks."""
        item = {
            "type": "mcq",
            "prompt": "Which join keeps only matching rows?",
            "options": ["INNER JOIN", "LEFT JOIN"],
            "correct_answer": "INNER JOIN",
            "topic_tag": "dbms.sql_joins",
        }
        near_duplicate = dict(item, prompt="Which JOIN keeps only matching rows??")
        out = self._validate([item, near_duplicate])
        self.assertEqual(len(out), 1)

    def test_invented_tags_fall_back_to_the_lesson_tag(self) -> None:
        out = self._validate(
            [
                {
                    "type": "mcq",
                    "prompt": "Which join keeps only matching rows?",
                    "options": ["INNER JOIN", "LEFT JOIN"],
                    "correct_answer": "INNER JOIN",
                    "topic_tag": "sql.joins",  # not in the vocabulary
                }
            ]
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["topic_tag"], "dbms.sql_joins")

    def test_true_false_is_normalised_and_given_options(self) -> None:
        out = self._validate(
            [
                {
                    "type": "true_false",
                    "prompt": "An INNER JOIN keeps unmatched rows.",
                    "correct_answer": "FALSE",
                    "topic_tag": "dbms.sql_joins",
                }
            ]
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["correct_answer"], "False")
        self.assertEqual(out[0]["options"], ["True", "False"])

    def test_a_type_the_caller_did_not_ask_for_is_dropped(self) -> None:
        out = self._validate(
            [
                {
                    "type": "short_answer",
                    "prompt": "Explain an INNER JOIN in your own words.",
                    "correct_answer": "only matching rows",
                    "topic_tag": "dbms.sql_joins",
                }
            ],
            types=("mcq",),
        )
        self.assertEqual(out, [])

    def test_the_limit_is_respected(self) -> None:
        items = [
            {
                "type": "mcq",
                "prompt": f"Question number {i} about joins?",
                "options": ["INNER JOIN", "LEFT JOIN"],
                "correct_answer": "INNER JOIN",
                "topic_tag": "dbms.sql_joins",
            }
            for i in range(9)
        ]
        self.assertEqual(len(self._validate(items, limit=3)), 3)

    def test_junk_does_not_raise(self) -> None:
        self.assertEqual(self._validate("not a list"), [])
        self.assertEqual(self._validate([None, 5, {"prompt": "hi"}]), [])


class TestGeneration(GeneratorBase):
    def _reply(self, n=2):
        return json.dumps(
            {
                "questions": [
                    {
                        "type": "mcq",
                        "prompt": f"Which join keeps only matching rows, take {i}?",
                        "options": ["INNER JOIN", "FULL OUTER JOIN"],
                        "correct_answer": "INNER JOIN",
                        "explanation": "Unmatched rows are discarded.",
                        "topic_tag": "dbms.sql_joins",
                        "difficulty": "medium",
                    }
                    for i in range(n)
                ]
            }
        )

    def test_generates_and_persists_without_leaking_answers(self) -> None:
        fake = _FakeLLM(self._reply())
        with patch("app.services.llm_client.get_llm", return_value=fake):
            result = _run(
                qg.generate_quiz(
                    self.db, lesson_id=self.lesson.id, user_id=self.user_id, num_questions=2
                )
            )

        self.assertEqual(len(result["questions"]), 2)
        self.assertEqual(result["source"], "ai_generated")
        # The caller is about to take this quiz.
        for q in result["questions"]:
            self.assertNotIn("correct_answer", q)
            self.assertNotIn("explanation", q)

        stored = self.db.query(Quiz).filter(Quiz.id == uuid.UUID(result["id"])).first()
        self.assertEqual(stored.source, "ai_generated")
        self.assertEqual(stored.generated_by_user, self.user_id)
        self.assertEqual(self.db.query(Question).filter(Question.quiz_id == stored.id).count(), 2)

    def test_difficulty_comes_from_this_students_mastery(self) -> None:
        self._mastery("dbms.sql_joins", 0.15)
        fake = _FakeLLM(self._reply(1))
        with patch("app.services.llm_client.get_llm", return_value=fake):
            _run(
                qg.generate_quiz(
                    self.db, lesson_id=self.lesson.id, user_id=self.user_id, num_questions=1
                )
            )
        self.assertIn("easy", fake.prompts[0])

    def test_a_live_misconception_is_targeted(self) -> None:
        """The belief the app named is the belief it re-tests."""
        self._mastery(
            "dbms.sql_joins",
            0.3,
            misconception="You believe an INNER JOIN keeps unmatched rows.",
        )
        fake = _FakeLLM(self._reply(1))
        with patch("app.services.llm_client.get_llm", return_value=fake):
            _run(
                qg.generate_quiz(
                    self.db, lesson_id=self.lesson.id, user_id=self.user_id, num_questions=1
                )
            )
        self.assertIn("keeps unmatched rows", fake.prompts[0])
        self.assertIn("plausible distractor", fake.prompts[0])

    def test_a_cleared_misconception_is_not_targeted(self) -> None:
        row = self._mastery(
            "dbms.sql_joins", 0.8, misconception="An old belief they have overcome."
        )
        row.misconception_cleared_at = datetime.now(timezone.utc)
        self.db.commit()

        fake = _FakeLLM(self._reply(1))
        with patch("app.services.llm_client.get_llm", return_value=fake):
            _run(
                qg.generate_quiz(
                    self.db, lesson_id=self.lesson.id, user_id=self.user_id, num_questions=1
                )
            )
        self.assertNotIn("An old belief", fake.prompts[0])

    def test_a_dead_provider_raises_rather_than_saving_an_empty_quiz(self) -> None:
        with patch("app.services.llm_client.get_llm", return_value=_DeadLLM()):
            with self.assertRaises(RuntimeError):
                _run(
                    qg.generate_quiz(
                        self.db, lesson_id=self.lesson.id, user_id=self.user_id
                    )
                )
        self.assertEqual(self.db.query(Quiz).count(), 0)

    def test_a_missing_lesson_is_a_value_error(self) -> None:
        with self.assertRaises(ValueError):
            _run(qg.generate_quiz(self.db, lesson_id=uuid.uuid4(), user_id=self.user_id))

    def test_adaptive_picks_the_weakest_topics(self) -> None:
        self._mastery("dbms.sql_joins", 0.9)
        self._mastery("python.loops", 0.12)
        fake = _FakeLLM(self._reply(1))
        with patch("app.services.llm_client.get_llm", return_value=fake):
            result = _run(
                qg.generate_adaptive_quiz(self.db, user_id=self.user_id, num_questions=1)
            )

        # Weakest first, and the difficulty follows it.
        self.assertIn("python.loops", fake.prompts[0])
        self.assertIn("easy", fake.prompts[0])
        self.assertEqual(result["source"], "ai_generated")

    def test_adaptive_works_for_a_learner_with_no_history(self) -> None:
        fake = _FakeLLM(self._reply(1))
        with patch("app.services.llm_client.get_llm", return_value=fake):
            result = _run(
                qg.generate_adaptive_quiz(self.db, user_id=self.user_id, num_questions=1)
            )
        self.assertEqual(len(result["questions"]), 1)
        self.assertIn("medium", fake.prompts[0])


if __name__ == "__main__":
    unittest.main()
