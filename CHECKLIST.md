# LearnQuest AI — 2-Week Delivery Checklist

> **How this works:** one member works at a time, in slot order. When your slot is
> done you **push to `main` and message the group**. The next person pulls and starts.
> Nobody works on the same files at the same time, so there are no merge conflicts.
>
> Tick `[x]` only when it works end to end: API returns real data → UI renders it →
> still works after `git pull`.
>
> Format: `- [x] Task — @yourname, 2026-09-22`

**Legend:** `[ ]` not started · `[~]` in progress · `[x]` done · `[-]` cut

---

## The pitch

> **A tutor that models your mind, not your score — with a real human face.**

A wrong answer doesn't just score 0. The app names **the false belief** behind it,
then the photoreal SyncTalk tutor is seeded with **your** misconception and you have
to teach it out of the mistake. Its score on the retry is your grade.
(*The protégé effect* — real education research.)

---

## File ownership — never edit someone else's files

| Member | Backend | Frontend |
|---|---|---|
| **M1** (AI) | `routers/{tutor,avatar,roadmap}.py`, `services/{llm_client,prompts,mastery,roadmap_planner}.py`, `models/{ai,roadmap}.py` | `pages/{Tutor,Roadmap}/`, `components/avatar/`, `api/{tutor,avatar,roadmap}.js` |
| **M2** (Learning) | `routers/{courses,lessons,progress,quizzes}.py`, `models/{course,progress,quiz}.py` | `pages/{Courses,Lesson,Quiz,Practice}/`, `components/ui/`, `api/{courses,lessons,quizzes}.js` |
| **M3** (Users) | `routers/{auth,users,admin}.py`, `models/user.py`, `deps.py` | `pages/{Auth,Profile,Admin}/`, `components/layout/`, `context/AuthContext.jsx` |
| **M4** (Game) | `routers/{gamification,analytics}.py`, `services/{xp_engine,events}.py`, `models/gamification.py` | `pages/{Dashboard,Achievements,Leaderboard,Stats,History}/`, `api/{gamification,analytics}.js` |

**Shared — announce before touching:** `app/main.py` · `app/models/__init__.py` ·
`frontend/src/App.jsx` · `tailwind.config.js` · `index.css` · `api/client.js`

**Design:** all frontend work follows [docs/DESIGN_GUIDELINES.md](docs/DESIGN_GUIDELINES.md).

---

# 🗓️ WEEK 1 — make the core loop real

## 🔵 Slot 1 · Member 1 · Days 1–2

**AI misconception engine — the novel core.**

- [ ] Implement `services/mastery.py::capture_misconception()` — LLM names the
      **false belief** behind a wrong answer in plain English — @, 2026-__-__
- [ ] Reject invented misconceptions: if the model is unsure, store `None` — @, 2026-__-__
- [ ] Register a `quiz.submitted` handler that calls it *(fires once M2 emits in Slot 2)* — @, 2026-__-__
- [ ] `GET /api/mastery/me/misconceptions` — list with status active/fading/cleared — @, 2026-__-__
- [ ] Decay: N correct answers moves active → fading → cleared — @, 2026-__-__

**✅ Hand off when:** you can POST a wrong answer and see a misconception row written.
**→ Push, then tell M2.**

---

## 🟢 Slot 2 · Member 2 · Days 2–4

**⛔ FIRST: unblock the database.** Quiz + progress tables don't exist — the models
are commented out in `models/__init__.py:3`, so they were never migrated.

- [ ] Uncomment `from app.models import progress, quiz` — @, 2026-__-__
- [ ] Create + run migration `0005_m2_quiz_progress_schema` — @, 2026-__-__
- [ ] Verify `quizzes`, `quiz_questions`, `quiz_attempts`, `lesson_progress` exist — @, 2026-__-__

**Then make quizzes work** — nothing in the app has a game loop without this.

- [ ] `GET /api/quizzes/{id}` — questions **with `correct_answer` stripped**
      (security, plan.md 7.3 — never send answers to the client) — @, 2026-__-__
- [ ] `POST /api/quizzes/{id}/attempts` — create attempt — @, 2026-__-__
- [ ] `POST /api/quizzes/attempts/{id}/submit` — score + persist — @, 2026-__-__
- [ ] **`emit(db, user_id, "quiz.submitted", {...})` on submit** — this is what
      triggers M1's misconception capture *and* M4's XP — @, 2026-__-__
- [ ] `QuizPlayer.jsx` — one question at a time, progress — @, 2026-__-__
- [ ] `QuizResult.jsx` — score + per-question review — @, 2026-__-__
- [ ] `GET /api/me/progress` — real *(M4 needs this in Slot 4)* — @, 2026-__-__

**✅ Hand off when:** you can take a quiz, get a score, and M1's misconception
appears for a wrong answer.
**→ Push, then tell M3.**

---

## 🟠 Slot 3 · Member 3 · Day 4–5

**Auth — blocks every real demo.**

- [ ] Enable **Google OAuth** in the Supabase dashboard (only `email` is on today —
      verified via `/auth/v1/settings`) — @, 2026-__-__
- [ ] Add redirect URLs for **both 5173 and 5174** (Vite falls back) — @, 2026-__-__
- [ ] Verify sign-up creates a `public.users` row — @, 2026-__-__
- [ ] `GET/PATCH /api/users/me` — @, 2026-__-__
- [ ] `Profile.jsx` — name, email, avatar — @, 2026-__-__

**✅ Hand off when:** a stranger can sign up with Google and see their profile.
**→ Push, then tell M4.**

---

## 🟣 Slot 4 · Member 4 · Day 5

**Dashboard — the first screen after login, currently blank.**

- [ ] XP + level + progress bar — `GET /api/me/stats` *(already real)* — @, 2026-__-__
- [ ] Streak counter *(already real)* — @, 2026-__-__
- [ ] "Continue learning" — uses M2's `/api/me/progress` — @, 2026-__-__
- [ ] "Next quest" — `GET /api/roadmap/me` *(already real)* — @, 2026-__-__
- [ ] Wire header streak/XP in `AppLayout.jsx` to real values (hardcoded `0` today) — @, 2026-__-__

**✅ Week 1 is done when:** sign up → dashboard shows real numbers → take a quiz →
get one wrong → the app names your misconception.

---

# 🗓️ WEEK 2 — the novel feature + fill the gaps

## 🔵 Slot 5 · Member 1 · Days 6–8

**SyncTalk photoreal tutor + Teach-Back — the demo moment.**

⚠️ The current Tier B code is **wrong**: `AvatarStage.jsx` renders the stream as
`<img src>` (MJPEG), but the server sends framed binary over WebSocket:
`[4B segment][4B frame_idx][4B total][4B audio_ms] + JPEG`.

- [ ] WS client: decode binary frames → `<canvas>` — @, 2026-__-__
- [ ] Sync the PCM audio segments to the frames — @, 2026-__-__
- [ ] Fall back to the SVG avatar when `AVATAR_SERVICE_URL` is unset or down — @, 2026-__-__
- [ ] **Teach-Back:** seed Nova with the student's own misconception — @, 2026-__-__
- [ ] Nova asks naive questions and pushes back on vague answers — @, 2026-__-__
- [ ] **Nova re-takes the question — its score is the student's grade** — @, 2026-__-__
- [ ] On success mark the misconception `fading` + award XP via `emit()` — @, 2026-__-__

**✅ Hand off when:** the full loop runs — wrong answer → misconception → teach
Nova → Nova passes.
**→ Push, then tell M2.**

---

## 🟢 Slot 6 · Member 2 · Days 8–10

**Courses in HackerRank shape.**

- [ ] Restructure catalogue as **Tracks → Skills → Problems** — @, 2026-__-__
- [ ] Difficulty chips (Easy/Medium/Hard) via `Badge tone=` — @, 2026-__-__
- [ ] Solve % + attempt count per skill — @, 2026-__-__
- [ ] Use `.table-dense` rows, not big cards — @, 2026-__-__
- [ ] Filters: subject, difficulty, status, search — @, 2026-__-__
- [ ] `GET /api/me/history` — real *(M4 needs it next)* — @, 2026-__-__

**✅ Hand off when:** the courses page looks like a practice platform, not a shop.
**→ Push, then tell M3.**

---

## 🟠 Slot 7 · Member 3 · Day 10–11

**Admin panel.**

- [ ] `AdminOverview.jsx` — user/course/activity counts — @, 2026-__-__
- [ ] `AdminCourses.jsx` — create / edit / publish a course — @, 2026-__-__
- [ ] `GET /api/admin/overview` — real numbers — @, 2026-__-__
- [ ] Confirm `DEV_ALLOW_ANONYMOUS=false` anywhere deployed — @, 2026-__-__

**→ Push, then tell M4.**

---

## 🟣 Slot 8 · Member 4 · Days 11–12

**Fill every remaining dead page.**

- [ ] `GET /api/leaderboard` — real → `Leaderboard.jsx` (`.table-dense`) — @, 2026-__-__
- [ ] Seed badges + `GET /api/me/badges` → `Achievements.jsx` — @, 2026-__-__
- [ ] `GET /api/mastery/me` → `Stats.jsx` + **misconception map** (M1's API) — @, 2026-__-__
- [ ] `History.jsx` from M2's `/api/me/history` — @, 2026-__-__

**✅ Hand off when:** no nav link is a dead end.

---

## 🔴 Days 13–14 · Everyone · Integration & demo

- [ ] Run the full demo script below, start to finish, three times — @, 2026-__-__
- [ ] Fix whatever breaks — @, 2026-__-__
- [ ] Seed a clean database for the presentation — @, 2026-__-__
- [ ] Rehearse the 5-minute demo — @, 2026-__-__

---

## 🎬 Demo script

1. Sign up → state a goal → **AI draws a branching roadmap** from the real catalogue
2. Open a lesson → take a quiz → **get one wrong**
3. Screen names **the false belief**, not just "incorrect"
4. **Nova appears — photoreal — holding that same wrong belief**
5. Student talks her out of it
6. **Nova re-takes the question and passes** → XP → roadmap re-plans

---

## Already working (don't rebuild)

Landing · Login/Register · Courses list · Course detail · Lesson viewer ·
AI Tutor chat · **AI Roadmap** · XP engine · DB with 3 courses / 15 lessons ·
Professional design system

---

## Cut to fit two weeks

- [-] Practice problems with a code editor and test cases — big build; the quiz
      loop already demonstrates practice
- [-] Daily challenges + notifications — nice-to-have, not on the demo path
- [-] Spaced-repetition review queue (`review_items`) — the roadmap already
      handles "what next"
- [-] Upload-your-own-notes → course pipeline
- [-] Duolingo-style playful design — replaced 2026-09-21 with the professional system

---

## Blockers

> Add a line the moment you are stuck. Do not stall silently — the next person
> in the relay is waiting on you.

- [ ] *(none logged)*
