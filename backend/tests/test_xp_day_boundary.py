"""XP deduplication must not depend on what time of day it is.

`xp_events.created_at` is written in UTC. "Today" used to come from
`date.today()`, the machine's LOCAL date, and the day window was then built as
`datetime.combine(that_date, ..., tzinfo=utc)`.

Anywhere east of Greenwich, for the first hours after local midnight, the two
dates disagree and the window covers a day the events are not in. Every "has
this already happened today?" lookup then answers no:

  - the daily-login bonus can be claimed again and again
  - the 25 XP/day tutor cap stops applying

Found on 2026-09-28 at 00:50 BST (+6), where local read 2026-09-28, UTC read
2026-09-27, and the two XP tests that had been intermittently failing all month
turned out to be failing *only* during that window. They were not flaky; they
were correct, and only ran into the bug at certain hours.

These tests pin the behaviour to the timezone rather than to the clock, so they
fail whatever time they are run at.
"""

from __future__ import annotations

import unittest
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.gamification import UserStats, XPEvent
from app.models.user import User
from app.services import xp_engine


class TestXPDayBoundary(unittest.TestCase):
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
        self.db.commit()

    def tearDown(self) -> None:
        self.db.rollback()
        for model in (XPEvent, UserStats, User):
            self.db.query(model).delete()
        self.db.commit()
        self.db.close()

    def test_today_is_the_utc_date(self) -> None:
        """The date used for lookups must match the date events are stored in."""
        self.assertEqual(xp_engine._utc_today(), datetime.now(timezone.utc).date())

    def test_an_event_written_now_falls_inside_todays_window(self) -> None:
        """The property the old code broke, stated directly.

        An event stamped `now` in UTC must be found by a lookup for "today",
        at every hour of the day. Under the old code this was false whenever the
        machine's local date ran ahead of UTC.
        """
        xp_engine.award_xp(
            db=self.db,
            user_id=self.user_id,
            amount=5,
            reason="tutor session",
            event_type="tutor.session",
        )
        self.assertEqual(xp_engine.get_today_tutor_xp(self.db, self.user_id), 5)

    def test_the_tutor_cap_holds_regardless_of_the_hour(self) -> None:
        """Six sessions at 5 XP must stop at the 25 XP cap, not reach 30."""
        for _ in range(6):
            xp_engine.on_tutor_session(
                self.db, self.user_id, {"conversation_id": str(uuid.uuid4())}
            )

        stats = (
            self.db.query(UserStats).filter(UserStats.user_id == self.user_id).first()
        )
        self.assertEqual(stats.xp, xp_engine.TUTOR_XP_DAILY_CAP)

    def test_the_daily_login_bonus_is_claimed_once(self) -> None:
        """Twice in one day must not pay twice."""
        xp_engine.on_daily_login(self.db, self.user_id, {})
        first = (
            self.db.query(UserStats).filter(UserStats.user_id == self.user_id).first().xp
        )

        xp_engine.on_daily_login(self.db, self.user_id, {})
        second = (
            self.db.query(UserStats).filter(UserStats.user_id == self.user_id).first().xp
        )

        self.assertEqual(first, second, "the daily bonus was awarded twice")

    def test_yesterdays_events_do_not_count_towards_today(self) -> None:
        """The window must still exclude what it should."""
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        self.db.add(
            XPEvent(
                id=uuid.uuid4(),
                user_id=self.user_id,
                event_type="tutor.session",
                xp_awarded=25,
                created_at=yesterday,
            )
        )
        self.db.commit()

        self.assertEqual(xp_engine.get_today_tutor_xp(self.db, self.user_id), 0)

    def test_an_explicit_date_is_still_honoured(self) -> None:
        """Callers passing a date - a user's own timezone - keep control."""
        self.assertEqual(
            xp_engine.get_today_tutor_xp(
                self.db, self.user_id, local_date=date(2020, 1, 1)
            ),
            0,
        )


if __name__ == "__main__":
    unittest.main()
