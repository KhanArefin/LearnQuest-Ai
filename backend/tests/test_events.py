"""Unit tests for the LearnQuest AI Event Bus (Member 4 - Gamification & Analytics).

Tests verification requirements:
A. Handler registration works (both @register_handler and @on).
B. emit() calls the correct handler with correct arguments.
C. Multiple handlers can subscribe to one event.
D. One handler failing does not prevent another handler from running and does not crash caller.
E. Unknown event types do not crash the application.
"""

from __future__ import annotations

import unittest
import uuid
from typing import Any
from unittest.mock import MagicMock

from app.services.events import (
    EVENT_TYPES,
    HANDLERS,
    EventType,
    clear_handlers,
    emit,
    on,
    register_handler,
    registered_handlers,
)


class TestEventBus(unittest.TestCase):
    """Test suite for event bus registration and emission."""

    def setUp(self) -> None:
        """Reset handler registry before each test to guarantee complete test isolation."""
        clear_handlers()

    def tearDown(self) -> None:
        """Clean up handler registry after each test."""
        clear_handlers()

    def test_a_handler_registration_works(self) -> None:
        """Requirement A: Test that @register_handler and @on properly register handlers."""
        @register_handler(EventType.LESSON_COMPLETED)
        def sample_lesson_handler(db: Any, user_id: Any, payload: dict[str, Any]) -> str:
            return "lesson_handled"

        # Check registry directly
        self.assertIn(EventType.LESSON_COMPLETED, HANDLERS)
        self.assertEqual(len(HANDLERS[EventType.LESSON_COMPLETED]), 1)
        self.assertEqual(HANDLERS[EventType.LESSON_COMPLETED][0], sample_lesson_handler)

        # Check debug inspector helper
        registry = registered_handlers()
        self.assertIn(EventType.LESSON_COMPLETED, registry)
        self.assertIn("sample_lesson_handler", registry[EventType.LESSON_COMPLETED])

        # Test that the @on alias also registers properly
        @on(EventType.QUIZ_SUBMITTED)
        def sample_quiz_handler(db: Any, user_id: Any, payload: dict[str, Any]) -> str:
            return "quiz_handled"

        self.assertIn(EventType.QUIZ_SUBMITTED, HANDLERS)
        self.assertEqual(HANDLERS[EventType.QUIZ_SUBMITTED][0], sample_quiz_handler)

    def test_b_emit_calls_correct_handler(self) -> None:
        """Requirement B: Test that emit() routes the event and passes correct arguments."""
        calls: list[dict[str, Any]] = []

        @register_handler("lesson.completed")
        def handle_lesson(db: Any, user_id: Any, payload: dict[str, Any]) -> str:
            calls.append({"db": db, "user_id": user_id, "payload": payload})
            return "done"

        @register_handler("quiz.submitted")
        def handle_quiz(db: Any, user_id: Any, payload: dict[str, Any]) -> str:
            calls.append({"db": db, "user_id": user_id, "payload": payload})
            return "quiz_done"

        mock_db = MagicMock()
        test_user_id = uuid.uuid4()
        test_payload = {"lesson_id": "les-123", "course_id": "crs-456", "seconds": 300}

        results = emit(
            db=mock_db,
            user_id=test_user_id,
            event_type="lesson.completed",
            payload=test_payload,
        )

        # Verify only the lesson handler was invoked
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["db"], mock_db)
        self.assertEqual(calls[0]["user_id"], test_user_id)
        self.assertEqual(calls[0]["payload"], test_payload)
        self.assertEqual(results, ["done"])

    def test_c_multiple_handlers_can_subscribe_to_one_event(self) -> None:
        """Requirement C: Test that multiple handlers can subscribe to a single event."""
        execution_order: list[str] = []

        @register_handler("course.enrolled")
        def handler_one(db: Any, user_id: Any, payload: dict[str, Any]) -> str:
            execution_order.append("handler_one")
            return "res_1"

        @register_handler("course.enrolled")
        def handler_two(db: Any, user_id: Any, payload: dict[str, Any]) -> str:
            execution_order.append("handler_two")
            return "res_2"

        results = emit(None, "user-abc", "course.enrolled", {"course_id": "crs-001"})

        self.assertEqual(execution_order, ["handler_one", "handler_two"])
        self.assertEqual(results, ["res_1", "res_2"])

    def test_d_handler_failure_isolation(self) -> None:
        """Requirement D: One failing handler must NEVER break the caller or other handlers."""
        successful_calls: list[str] = []

        @register_handler("quiz.submitted")
        def broken_handler(db: Any, user_id: Any, payload: dict[str, Any]) -> None:
            raise RuntimeError("Database timeout in gamification badge check!")

        @register_handler("quiz.submitted")
        def working_handler(db: Any, user_id: Any, payload: dict[str, Any]) -> str:
            successful_calls.append("working_handler_executed")
            return "success"

        # Calling emit must NOT raise RuntimeError
        try:
            results = emit(None, "user-xyz", "quiz.submitted", {"score": 100})
        except Exception as err:
            self.fail(f"emit() raised an unexpected exception: {err}")

        # The working handler must have executed despite the earlier failure
        self.assertEqual(successful_calls, ["working_handler_executed"])
        self.assertEqual(results, ["success"])

    def test_e_unknown_event_types_do_not_crash(self) -> None:
        """Requirement E: Unknown/unregistered event types do not crash the application."""
        # Case 1: Unregistered standard event type (has no handlers yet)
        try:
            res1 = emit(None, "user-1", "daily.login", {})
            self.assertEqual(res1, [])
        except Exception as err:
            self.fail(f"emit() crashed on standard event with no handlers: {err}")

        # Case 2: Completely unknown event string
        try:
            res2 = emit(None, "user-2", "nonexistent.system.event", {"data": 42})
            self.assertEqual(res2, [])
        except Exception as err:
            self.fail(f"emit() crashed on completely unknown event: {err}")

    def test_extensibility_custom_event_type(self) -> None:
        """Requirement 4 & 5: Event bus is extensible for future events without modifying emit()."""
        custom_event = "custom.achievement.unlocked"

        @register_handler(custom_event)
        def handle_custom(db: Any, user_id: Any, payload: dict[str, Any]) -> str:
            return f"custom: {payload.get('badge')}"

        self.assertIn(custom_event, EVENT_TYPES)
        results = emit(None, "user-99", custom_event, {"badge": "speed_demon"})
        self.assertEqual(results, ["custom: speed_demon"])


if __name__ == "__main__":
    unittest.main()
