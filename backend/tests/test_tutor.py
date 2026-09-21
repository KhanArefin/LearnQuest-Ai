"""Unit tests for Member 1 AI Avatar Tutor functionality.

Covers:
- Prompt builder and context assembly
- Viseme generation for Tier A lipsync
- Conversation CRUD operations
- Tutor chat messaging with MockLLMClient
- Selection explanation endpoint
- Avatar speak and config endpoints
"""

import unittest
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.ai import Conversation, Message, TopicMastery
from app.models.course import Course, Lesson
from app.models.gamification import UserStats
from app.models.user import User
from app.services.llm_client import MockLLMClient, get_llm
from app.services.prompts import (
    build_tutor_context,
    generate_conversation_title,
    text_to_visemes,
)


class TestTutorAI(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.user_id = uuid.uuid4()
        user = User(
            id=self.user_id,
            email="test@learnquest.local",
            full_name="Test Student",
            role="student",
        )
        self.db.add(user)

        self.course_id = uuid.uuid4()
        course = Course(
            id=self.course_id,
            title="Database Systems",
            slug="database-systems",
        )
        self.db.add(course)

        self.lesson_id = uuid.uuid4()
        lesson = Lesson(
            id=self.lesson_id,
            course_id=self.course_id,
            title="SQL Joins Explained",
            order_index=1,
            content_md="An INNER JOIN selects records that have matching values in both tables.",
            topic_tags=["dbms.sql_joins"],
        )
        self.db.add(lesson)

        # User stats
        stats = UserStats(
            user_id=self.user_id,
            level=3,
            xp=450,
        )
        self.db.add(stats)

        # Topic mastery with misconception
        mastery = TopicMastery(
            id=uuid.uuid4(),
            user_id=self.user_id,
            topic_tag="dbms.sql_joins",
            mastery_score=0.4,
            misconception="Thinks LEFT JOIN discards unmatched rows from the left table.",
            misconception_updated_at=datetime.now(timezone.utc),
            attempts=5,
            correct=2,
        )
        self.db.add(mastery)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_text_to_visemes_generates_valid_timeline(self):
        text = "Hello! Today we learn about SQL joins."
        timeline = text_to_visemes(text)

        self.assertIsInstance(timeline, list)
        self.assertGreater(len(timeline), 2)
        # Starts with silence
        self.assertEqual(timeline[0]["v"], "sil")
        self.assertEqual(timeline[0]["t"], 0.0)
        # Ends with silence
        self.assertEqual(timeline[-1]["v"], "sil")

        for entry in timeline:
            self.assertIn("t", entry)
            self.assertIn("v", entry)
            self.assertIn(entry["v"], ["sil", "AA", "E", "I", "O", "U", "M", "F", "L", "S"])

    def test_generate_conversation_title(self):
        title1 = generate_conversation_title("How do SQL joins work in PostgreSQL?")
        self.assertEqual(title1, "How do SQL joins work in PostgreSQL?")

        long_msg = "Can you please explain in deep detail how relational database normalization 3NF Boyce Codd normal form works?"
        title2 = generate_conversation_title(long_msg)
        self.assertLessEqual(len(title2), 40)
        self.assertTrue(title2.endswith("..."))

    def test_build_tutor_context_includes_learner_profile_and_misconception(self):
        conv_id = uuid.uuid4()
        conv = Conversation(
            id=conv_id,
            user_id=self.user_id,
            title="SQL Questions",
            context_lesson_id=self.lesson_id,
        )
        self.db.add(conv)
        self.db.commit()

        context = build_tutor_context(
            db=self.db,
            user_id=self.user_id,
            conversation_id=conv_id,
            current_lesson_id=self.lesson_id,
        )

        self.assertGreater(len(context), 0)
        system_msg = context[0]
        self.assertEqual(system_msg["role"], "system")
        self.assertIn("SQL Joins Explained", system_msg["content"])
        self.assertIn("dbms.sql_joins", system_msg["content"])
        # Verifies misconception is surfaced into tutor prompt (plan.md 6.10)
        self.assertIn("Thinks LEFT JOIN discards unmatched rows", system_msg["content"])

    def test_conversation_and_message_db_persistence(self):
        conv = Conversation(
            id=uuid.uuid4(),
            user_id=self.user_id,
            title="Practice Session",
            context_lesson_id=self.lesson_id,
        )
        self.db.add(conv)
        self.db.commit()

        user_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role="user",
            content="What is an outer join?",
            tokens=5,
        )
        self.db.add(user_msg)

        assistant_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role="assistant",
            content="An outer join retains rows even if there is no match.",
            tokens=12,
            visemes=[{"t": 0.0, "v": "sil"}, {"t": 0.1, "v": "AA"}],
        )
        self.db.add(assistant_msg)
        self.db.commit()

        messages = (
            self.db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
            .all()
        )
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, "user")
        self.assertEqual(messages[1].role, "assistant")
        self.assertIsNotNone(messages[1].visemes)

    async def _run_async_mock(self):
        llm = MockLLMClient()
        res = await llm.complete([{"role": "user", "content": "Explain SQL joins"}])
        self.assertIsInstance(res, str)
        self.assertGreater(len(res), 5)

    def test_mock_llm_completes(self):
        import asyncio
        asyncio.run(self._run_async_mock())

    async def _run_async_endpoint_tests(self):
        from app.routers.avatar import avatar_config, avatar_status, speak, SpeakRequest
        from app.routers.tutor import (
            create_conversation,
            delete_conversation,
            explain,
            get_conversation,
            list_conversations,
            list_messages,
            send_message,
            CreateConversationRequest,
            ExplainRequest,
            SendMessageRequest,
        )

        user_dict = {"id": str(self.user_id), "email": "test@learnquest.local"}

        # 1. Create conversation
        conv_res = create_conversation(
            user=user_dict,
            body=CreateConversationRequest(title="Test AI Chat", context_lesson_id=self.lesson_id),
            db=self.db,
        )
        self.assertIsNotNone(conv_res["id"])
        conv_id = uuid.UUID(conv_res["id"])
        self.assertEqual(conv_res["title"], "Test AI Chat")

        # 2. List conversations
        list_res = list_conversations(user=user_dict, db=self.db)
        self.assertGreater(list_res["total"], 0)
        self.assertTrue(any(c["id"] == str(conv_id) for c in list_res["items"]))

        # 3. Get single conversation
        single_res = get_conversation(conversation_id=conv_id, user=user_dict, db=self.db)
        self.assertEqual(single_res["id"], str(conv_id))

        # 4. Send message
        msg_res = await send_message(
            conversation_id=conv_id,
            body=SendMessageRequest(content="Can you explain inner joins with an example?"),
            user=user_dict,
            db=self.db,
        )
        self.assertEqual(msg_res["role"], "assistant")
        self.assertTrue(len(msg_res["content"]) > 0)
        self.assertIsInstance(msg_res["visemes"], list)
        self.assertGreater(len(msg_res["visemes"]), 0)

        # 5. List messages
        history_res = list_messages(conversation_id=conv_id, user=user_dict, db=self.db)
        self.assertEqual(len(history_res["items"]), 2)
        self.assertEqual(history_res["items"][0]["role"], "user")
        self.assertEqual(history_res["items"][1]["role"], "assistant")

        # 6. Explain selection
        explain_res = await explain(
            body=ExplainRequest(
                selection="INNER JOIN orders ON customers.id = orders.customer_id",
                lesson_id=self.lesson_id,
            ),
            user=user_dict,
            db=self.db,
        )
        self.assertTrue(len(explain_res["explanation"]) > 0)
        self.assertIsInstance(explain_res["visemes"], list)

        # 7. Avatar endpoints
        status_res = avatar_status()
        self.assertIn("tier", status_res)
        config_res = avatar_config()
        self.assertIn("expressions", config_res)
        self.assertIn("visemes", config_res)

        speak_res = await speak(
            body=SpeakRequest(text="Welcome to LearnQuest!"),
            user=user_dict,
        )
        self.assertGreater(len(speak_res["visemes"]), 0)

        # 8. Delete conversation
        del_res = delete_conversation(conversation_id=conv_id, user=user_dict, db=self.db)
        self.assertTrue(del_res["deleted"])

    def test_api_tutor_endpoints_end_to_end(self):
        import asyncio
        asyncio.run(self._run_async_endpoint_tests())


if __name__ == "__main__":
    unittest.main()
