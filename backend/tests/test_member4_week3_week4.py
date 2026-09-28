"""Unit and integration tests for Member 4 Week 3 & Week 4 deliverables:
- Analytics (/api/analytics/me/summary, /api/analytics/me/activity, /api/analytics/me/review, /api/analytics/mastery/me)
- Badges expansion (15 badges, data-driven criteria, idempotency, notification generation)
- Daily Challenges (/api/challenges/today, /api/challenges/{id}/claim, events, duplicate prevention)
- Notifications (/api/notifications, /api/notifications/{id}/read, cross-user authorization)
- Edge cases (0 data, 1 day, new day, duplicate awards)
"""

import unittest
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import get_current_user
from app.main import app
from app.models.ai import Message, ReviewItem, TopicMastery
from app.models.course import Course, Lesson
from app.models.gamification import Badge, DailyChallenge, Notification, UserBadge, UserChallenge, UserStats, XPEvent
from app.models.progress import LessonProgress
from app.models.quiz import QuizAttempt
from app.models.user import User
from app.seed.seed_data import ALL_BADGES, seed_all_badges, seed_badges
from app.services.badge_checker import check_badges, get_badge_progress, register_badge_handlers
from app.services.challenges import (
    claim_challenge,
    get_or_create_daily_challenges,
    get_user_challenges_for_today,
    update_challenge_progress,
)
from app.services.events import clear_handlers, emit
from app.services.xp_engine import _utc_today, award_xp


class TestMember4Features(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.user_id = uuid.uuid4()
        self.user = User(
            id=self.user_id,
            email="m4_student@learnquest.test",
            full_name="M4 Student",
            role="student",
        )
        self.db.add(self.user)

        self.other_user_id = uuid.uuid4()
        self.other_user = User(
            id=self.other_user_id,
            email="other_student@learnquest.test",
            full_name="Other Student",
            role="student",
        )
        self.db.add(self.other_user)
        self.db.commit()

        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: {
            "id": str(self.user_id),
            "email": self.user.email,
            "full_name": self.user.full_name,
            "role": "student",
        }
        self.client = TestClient(app)
        from app.services.xp_engine import register_xp_handlers
        from app.services.challenges import register_challenge_handlers
        register_xp_handlers()
        register_badge_handlers()
        register_challenge_handlers()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.db.close()
        clear_handlers()
        Base.metadata.drop_all(bind=self.engine)

    # =========================================================================
    # 1. Analytics Summary & Empty State Edge Cases
    # =========================================================================

    def test_analytics_summary_empty_state(self) -> None:
        """With 0 activity, /api/analytics/me/summary returns zeroed structure without error."""
        res = self.client.get("/api/analytics/me/summary")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["lessons_completed"], 0)
        self.assertEqual(data["quizzes_taken"], 0)
        self.assertEqual(data["avg_score"], 0.0)
        self.assertEqual(data["minutes"], 0)
        self.assertIn("review_queue", data)
        self.assertEqual(data["review_queue"]["total"], 0)
        self.assertEqual(data["review_queue"]["due_today"], 0)
        self.assertEqual(data["review_queue"]["retention_rate"], 0.0)

    def test_analytics_summary_with_real_data(self) -> None:
        """With completed lessons, quizzes, and stats, summary reports actual values."""
        stats = UserStats(
            user_id=self.user_id,
            xp=150,
            level=2,
            current_streak=3,
            total_learning_seconds=1800,  # 30 mins
        )
        self.db.add(stats)

        # Completed lesson
        course = Course(id=uuid.uuid4(), title="Test Course", slug="test-course", created_by=self.user_id)
        self.db.add(course)
        lesson = Lesson(id=uuid.uuid4(), course_id=course.id, title="Lesson 1", order_index=1)
        self.db.add(lesson)
        lp = LessonProgress(
            id=uuid.uuid4(),
            user_id=self.user_id,
            lesson_id=lesson.id,
            status="completed",
            seconds_spent=900,
            completed_at=datetime.now(timezone.utc),
        )
        self.db.add(lp)

        # 2 Quiz attempts: 80% and 100% -> avg 90%
        qa1 = QuizAttempt(
            id=uuid.uuid4(),
            user_id=self.user_id,
            quiz_id=uuid.uuid4(),
            score=80.0,
            submitted_at=datetime.now(timezone.utc),
            duration_seconds=300,
        )
        qa2 = QuizAttempt(
            id=uuid.uuid4(),
            user_id=self.user_id,
            quiz_id=uuid.uuid4(),
            score=100.0,
            submitted_at=datetime.now(timezone.utc),
            duration_seconds=300,
        )
        self.db.add_all([qa1, qa2])
        self.db.commit()

        res = self.client.get("/api/analytics/me/summary")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["lessons_completed"], 1)
        self.assertEqual(data["quizzes_taken"], 2)
        self.assertEqual(data["avg_score"], 90.0)
        self.assertEqual(data["minutes"], 30)
        self.assertEqual(data["xp"], 150)
        self.assertEqual(data["level"], 2)
        self.assertEqual(data["current_streak"], 3)

    # =========================================================================
    # 2. Activity Chart Analytics Edge Cases (0 data, 1 day, 7 days, 56 days)
    # =========================================================================

    def test_analytics_activity_date_ranges(self) -> None:
        """Activity returns continuous arrays for 0 days, 1 day, 7 days, and default 56 days."""
        # 0 days
        res0 = self.client.get("/api/analytics/me/activity?days=0")
        self.assertEqual(res0.status_code, 200)
        self.assertEqual(len(res0.json()["items"]), 0)

        # 1 day
        res1 = self.client.get("/api/analytics/me/activity?days=1")
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(len(res1.json()["items"]), 1)
        self.assertEqual(res1.json()["items"][0]["date"], _utc_today().isoformat())

        # 7 days
        res7 = self.client.get("/api/analytics/me/activity?days=7")
        self.assertEqual(res7.status_code, 200)
        self.assertEqual(len(res7.json()["items"]), 7)

        # 56 days (default)
        res56 = self.client.get("/api/analytics/me/activity")
        self.assertEqual(res56.status_code, 200)
        self.assertEqual(len(res56.json()["items"]), 56)

    def test_analytics_activity_tracks_xp_and_completions(self) -> None:
        """Activity properly populates daily XP, lessons, and quizzes."""
        now = datetime.now(timezone.utc)
        evt = XPEvent(
            id=uuid.uuid4(),
            user_id=self.user_id,
            event_type="lesson.completed",
            xp_awarded=50,
            created_at=now,
        )
        self.db.add(evt)
        self.db.commit()

        res = self.client.get("/api/analytics/me/activity?days=7")
        self.assertEqual(res.status_code, 200)
        items = res.json()["items"]
        today_item = [it for it in items if it["date"] == _utc_today().isoformat()][0]
        self.assertEqual(today_item["xp"], 50)
        self.assertEqual(today_item["lessons"], 1)

    # =========================================================================
    # 3. Review Queue Analytics
    # =========================================================================

    def test_review_queue_analytics(self) -> None:
        """Review queue properly calculates due today, overdue, total, and retention rate."""
        now = datetime.now(timezone.utc)
        # Overdue item (due 2 days ago, reviewed with streak 2)
        r1 = ReviewItem(
            id=uuid.uuid4(),
            user_id=self.user_id,
            topic_tag="dbms.joins",
            due_at=now - timedelta(days=2),
            interval_days=1,
            streak=2,
            last_reviewed_at=now - timedelta(days=3),
        )
        # Due today item (due now, streak 1)
        r2 = ReviewItem(
            id=uuid.uuid4(),
            user_id=self.user_id,
            topic_tag="python.generators",
            due_at=now,
            interval_days=2,
            streak=1,
            last_reviewed_at=now - timedelta(days=1),
        )
        # Due tomorrow (streak 0)
        r3 = ReviewItem(
            id=uuid.uuid4(),
            user_id=self.user_id,
            topic_tag="os.concurrency",
            due_at=now + timedelta(days=1),
            interval_days=4,
            streak=0,
            last_reviewed_at=now - timedelta(days=1),
        )
        self.db.add_all([r1, r2, r3])
        self.db.commit()

        res = self.client.get("/api/analytics/me/review")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total"], 3)
        self.assertEqual(data["overdue"], 1)
        self.assertEqual(data["due_today"], 2)  # overdue counts as due today
        # 2 out of 3 reviewed items retained (streak > 0)
        self.assertEqual(data["retention_rate"], 66.7)
        self.assertEqual(len(data["items"]), 3)

    # =========================================================================
    # 4. Topic Mastery Analytics
    # =========================================================================

    def test_topic_mastery_analytics(self) -> None:
        """Topic mastery returns real records and handles 0/many topics without error."""
        # 0 topics
        res0 = self.client.get("/api/analytics/mastery/me")
        self.assertEqual(res0.status_code, 200)
        self.assertEqual(res0.json()["total"], 0)

        # Seed 2 topics
        tm1 = TopicMastery(
            id=uuid.uuid4(),
            user_id=self.user_id,
            topic_tag="dbms.sql",
            mastery_score=0.45,
            attempts=5,
            correct=2,
            misconception="Thinks joins merge all keys unconditionally",
        )
        tm2 = TopicMastery(
            id=uuid.uuid4(),
            user_id=self.user_id,
            topic_tag="algorithms.trees",
            mastery_score=0.92,
            attempts=10,
            correct=9,
        )
        self.db.add_all([tm1, tm2])
        self.db.commit()

        res = self.client.get("/api/analytics/mastery/me")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["items"][0]["topic_tag"], "dbms.sql")
        self.assertTrue(data["items"][0]["has_misconception"])
        self.assertEqual(data["items"][1]["topic_tag"], "algorithms.trees")
        self.assertFalse(data["items"][1]["has_misconception"])

    # =========================================================================
    # 5. Badges (All 15 Badges, Idempotency, Criteria, Notifications)
    # =========================================================================

    def test_seed_all_15_badges_idempotent(self) -> None:
        """Seeding all badges creates exactly 15 badges and is idempotent."""
        badges = seed_all_badges(self.db)
        self.assertEqual(len(badges), 15)

        # Verify idempotency
        badges_repeat = seed_all_badges(self.db)
        self.assertEqual(len(badges_repeat), 15)
        total_in_db = self.db.query(Badge).count()
        self.assertEqual(total_in_db, 15)

    def test_badge_earning_creates_notification_and_awards_xp_once(self) -> None:
        """When a badge is earned, UserBadge is created, notification written, and XP awarded once."""
        seed_all_badges(self.db)
        badge = self.db.query(Badge).filter(Badge.code == "first_lesson").first()
        self.assertIsNotNone(badge)

        # Trigger lesson completion event
        emit(
            db=self.db,
            user_id=self.user_id,
            event_type="lesson.completed",
            payload={"lesson_id": str(uuid.uuid4())},
        )

        user_badge = (
            self.db.query(UserBadge)
            .filter(UserBadge.user_id == self.user_id, UserBadge.badge_id == badge.id)
            .first()
        )
        self.assertIsNotNone(user_badge)

        # Verify notification was created
        notif = (
            self.db.query(Notification)
            .filter(Notification.user_id == self.user_id, Notification.type == "badge_earned")
            .first()
        )
        self.assertIsNotNone(notif)
        self.assertIn("First Lesson", notif.title)

        # Verify XP awarded
        xp_entry = (
            self.db.query(XPEvent)
            .filter(
                XPEvent.user_id == self.user_id,
                XPEvent.event_type == "badge.earned",
                XPEvent.ref_id == badge.id,
            )
            .first()
        )
        self.assertIsNotNone(xp_entry)
        self.assertEqual(xp_entry.xp_awarded, badge.xp_reward)

        # Retriggering the same event MUST NOT award it twice
        emit(
            db=self.db,
            user_id=self.user_id,
            event_type="lesson.completed",
            payload={"lesson_id": str(uuid.uuid4())},
        )
        badge_count = (
            self.db.query(UserBadge)
            .filter(UserBadge.user_id == self.user_id, UserBadge.badge_id == badge.id)
            .count()
        )
        self.assertEqual(badge_count, 1)

    # =========================================================================
    # 6. Daily Challenges (Today, Progress, Completion, Claim, Duplicate Claim)
    # =========================================================================

    def test_daily_challenges_flow(self) -> None:
        """Full challenge flow: get today -> progress -> complete -> claim -> duplicate claim prevented."""
        # 1. Get today's challenges (creates 3)
        res = self.client.get("/api/challenges/today")
        self.assertEqual(res.status_code, 200)
        items = res.json()["items"]
        self.assertEqual(len(items), 3)

        challenge = items[0]
        ch_id = challenge["id"]
        ch_type = challenge["challenge_type"]
        self.assertFalse(challenge["is_completed"])
        self.assertFalse(challenge["is_claimed"])

        # 2. Cannot claim incomplete challenge
        claim_res = self.client.post(f"/api/challenges/{ch_id}/claim")
        self.assertEqual(claim_res.status_code, 400)
        self.assertIn("not yet completed", claim_res.json()["detail"])

        # 3. Complete the challenge by updating progress
        target = challenge["target_value"]
        update_challenge_progress(self.db, self.user_id, ch_type, increment=target)

        # Verify today's status updated
        res_after = self.client.get("/api/challenges/today")
        updated_ch = [c for c in res_after.json()["items"] if c["id"] == ch_id][0]
        self.assertTrue(updated_ch["is_completed"])
        self.assertFalse(updated_ch["is_claimed"])

        # 4. Claim reward successfully
        claim_success = self.client.post(f"/api/challenges/{ch_id}/claim")
        self.assertEqual(claim_success.status_code, 200)
        claim_body = claim_success.json()
        self.assertTrue(claim_body["claimed"])
        self.assertEqual(claim_body["xp_awarded"], challenge["xp_reward"])

        # 5. Duplicate claim attempt is refused
        dup_claim = self.client.post(f"/api/challenges/{ch_id}/claim")
        self.assertEqual(dup_claim.status_code, 400)
        self.assertIn("already been claimed", dup_claim.json()["detail"])

        # 6. Today endpoint now shows is_claimed = True
        res_claimed = self.client.get("/api/challenges/today")
        claimed_ch = [c for c in res_claimed.json()["items"] if c["id"] == ch_id][0]
        self.assertTrue(claimed_ch["is_claimed"])

    # =========================================================================
    # 7. Notifications API & Security (Cross-User Isolation)
    # =========================================================================

    def test_notifications_lifecycle_and_security(self) -> None:
        """Notifications listing, marking read, and cross-user authorization protection."""
        # Empty notifications
        empty_res = self.client.get("/api/notifications")
        self.assertEqual(empty_res.status_code, 200)
        self.assertEqual(empty_res.json()["unread"], 0)
        self.assertEqual(len(empty_res.json()["items"]), 0)

        # Create notification for self
        n_self = Notification(
            id=uuid.uuid4(),
            user_id=self.user_id,
            type="badge_earned",
            title="First Badge!",
            body="Great job.",
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        # Create notification for other user
        n_other = Notification(
            id=uuid.uuid4(),
            user_id=self.other_user_id,
            type="badge_earned",
            title="Other Badge",
            body="Secret info.",
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add_all([n_self, n_other])
        self.db.commit()

        # Listing only shows caller's notifications
        list_res = self.client.get("/api/notifications")
        self.assertEqual(list_res.status_code, 200)
        data = list_res.json()
        self.assertEqual(data["unread"], 1)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["id"], str(n_self.id))

        # Attempt to mark other user's notification as read -> 403 Forbidden
        cross_res = self.client.post(f"/api/notifications/{n_other.id}/read")
        self.assertEqual(cross_res.status_code, 403)

        # Mark own notification as read
        read_res = self.client.post(f"/api/notifications/{n_self.id}/read")
        self.assertEqual(read_res.status_code, 200)
        self.assertTrue(read_res.json()["is_read"])

        # Unread count is now 0
        list_res2 = self.client.get("/api/notifications")
        self.assertEqual(list_res2.json()["unread"], 0)


if __name__ == "__main__":
    unittest.main()
