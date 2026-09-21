"""Additional seeded courses beyond the flagship SQL course.

Run via ``python -m app.seed.seed_data`` - :func:`main` there calls into this
module. It can also be run on its own with ``python -m app.seed.extra_courses``.

``seed_data.py`` deliberately scopes itself to "ONE course done properly", so
extra catalogue breadth lives here instead of inflating that file.

Every ``topic_tags`` value below comes from ``TOPIC_VOCABULARY`` in
``seed_data.py`` - the controlled vocabulary agreed in week 1 (plan.md §3.1).
Between them these courses cover the python.* and web.* tags, which the SQL
course (dbms.*) does not touch. Adding a subject outside that list means
extending the vocabulary first, by agreement.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.course import Course, Lesson

logger = logging.getLogger("learnquest.seed")


# --------------------------------------------------------------------------- #
# Course definitions
# --------------------------------------------------------------------------- #

PYTHON_LESSONS: list[dict[str, Any]] = [
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222230001"),
        "title": "Values, Variables and Types",
        "order_index": 1,
        "estimated_minutes": 20,
        "topic_tags": ["python.basics"],
        "content_md": """# Values, Variables and Types

## 1. Names Are Labels, Not Boxes
A Python variable does not *contain* a value. It is a **name bound to an
object**. Assignment rebinds the name; it never copies the object.

```python
a = [1, 2, 3]
b = a          # b is another label for the SAME list
b.append(4)
print(a)       # [1, 2, 3, 4]  <- a changed too
```

To get an independent copy you must ask for one:

```python
b = a.copy()   # or list(a), or a[:]
```

This single idea explains most surprising behaviour beginners hit with lists
and dictionaries.

## 2. The Core Built-in Types

| Type | Example | Mutable? |
|------|---------|----------|
| `int` | `42` | no |
| `float` | `3.14` | no |
| `str` | `"hello"` | no |
| `list` | `[1, 2]` | **yes** |
| `dict` | `{"a": 1}` | **yes** |
| `tuple` | `(1, 2)` | no |
| `set` | `{1, 2}` | **yes** |

Immutability matters: because `str` is immutable, `s.upper()` returns a *new*
string rather than changing `s` in place.

```python
s = "hello"
s.upper()      # 'HELLO'
print(s)       # 'hello'  <- unchanged
s = s.upper()  # rebind to keep the result
```

## 3. Truthiness
Every object is either truthy or falsy. These are all falsy:

```python
False, None, 0, 0.0, "", [], {}, set()
```

So prefer the idiomatic emptiness check:

```python
if not items:          # good
if len(items) == 0:    # works, but noisier
```

## 4. f-strings
Since Python 3.6, f-strings are the clearest way to build text:

```python
name, score = "Ada", 97.5
print(f"{name} scored {score:.1f}%")   # Ada scored 97.5%
```

## Practice
1. Predict the output of the `a`/`b` list example above, then run it.
2. Write a function that takes a list and returns a *sorted copy*, leaving the
   original untouched. (Hint: `sorted()` returns a new list; `.sort()` does not.)
""",
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222230002"),
        "title": "Control Flow, Loops and Comprehensions",
        "order_index": 2,
        "estimated_minutes": 25,
        "topic_tags": ["python.loops", "python.basics"],
        "content_md": """# Control Flow, Loops and Comprehensions

## 1. Iterate Over Items, Not Indices
Coming from C or Java, the instinct is to loop over an index. In Python you
almost never need to:

```python
# Avoid
for i in range(len(names)):
    print(names[i])

# Prefer
for name in names:
    print(name)

# Need the index too?
for i, name in enumerate(names, start=1):
    print(f"{i}. {name}")
```

## 2. Walking Two Sequences Together

```python
students = ["Ada", "Linus", "Grace"]
scores   = [97, 84, 91]

for student, score in zip(students, scores):
    print(f"{student}: {score}")
```

## 3. `break`, `continue` and the `else` Clause
A loop's `else` runs **only if the loop finished without `break`**. It is the
cleanest way to express "searched everything and found nothing":

```python
for item in haystack:
    if item == needle:
        print("found it")
        break
else:
    print("not present")
```

## 4. Comprehensions
A comprehension builds a new collection from an existing iterable. It replaces
the append-in-a-loop pattern:

```python
# Loop version
squares = []
for n in numbers:
    if n % 2 == 0:
        squares.append(n ** 2)

# Comprehension - same thing, one line
squares = [n ** 2 for n in numbers if n % 2 == 0]
```

Dict and set comprehensions work the same way:

```python
lengths = {word: len(word) for word in words}
unique_initials = {word[0] for word in words}
```

**Keep them readable.** If you need two conditions and a nested loop, write the
explicit loop instead - a comprehension is not automatically better.

## Practice
1. Given `temps_c = [0, 18, 25, 31]`, build `temps_f` with a comprehension.
2. Use the `for/else` pattern to report whether any number in a list is prime.
""",
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222230003"),
        "title": "Functions, Scope and Default Arguments",
        "order_index": 3,
        "estimated_minutes": 25,
        "topic_tags": ["python.functions"],
        "content_md": """# Functions, Scope and Default Arguments

## 1. Defining and Calling

```python
def greet(name: str, greeting: str = "Hello") -> str:
    return f"{greeting}, {name}!"

greet("Ada")                      # 'Hello, Ada!'
greet("Ada", greeting="Hi")       # 'Hi, Ada!'
```

Type hints are optional and not enforced at runtime, but they document intent
and let editors catch mistakes.

## 2. The Mutable Default Argument Trap
This is the single most common Python bug:

```python
def add_item(item, basket=[]):     # BUG
    basket.append(item)
    return basket

add_item("apple")    # ['apple']
add_item("pear")     # ['apple', 'pear']  <- same list reused!
```

The default is evaluated **once**, when the function is defined. Use `None`:

```python
def add_item(item, basket=None):   # correct
    if basket is None:
        basket = []
    basket.append(item)
    return basket
```

## 3. `*args` and `**kwargs`

```python
def report(title, *values, **options):
    print(title, values, options)

report("Scores", 90, 85, sort=True)
# Scores (90, 85) {'sort': True}
```

`*` collects extra positional arguments into a tuple; `**` collects extra
keyword arguments into a dict.

## 4. Scope: the LEGB Rule
Python resolves a name by looking in order at **L**ocal, **E**nclosing,
**G**lobal, **B**uilt-in scopes.

```python
count = 0

def increment():
    count = count + 1   # UnboundLocalError!
```

Assigning to `count` makes it local to the function, so reading it before
assignment fails. Prefer returning a value over mutating globals:

```python
def increment(count):
    return count + 1
```

## 5. Functions Are Objects
They can be passed around, stored, and returned:

```python
operations = {"double": lambda x: x * 2, "square": lambda x: x ** 2}
operations["square"](5)    # 25
```

## Practice
1. Fix a function that uses a mutable default dict.
2. Write `apply_all(value, *funcs)` that applies each function in turn.
""",
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222230004"),
        "title": "Classes, Objects and Dunder Methods",
        "order_index": 4,
        "estimated_minutes": 30,
        "topic_tags": ["python.oop"],
        "content_md": """# Classes, Objects and Dunder Methods

## 1. A Minimal Class

```python
class Student:
    def __init__(self, name: str, score: int) -> None:
        self.name = name       # instance attribute
        self.score = score

    def passed(self) -> bool:
        return self.score >= 50
```

`__init__` is the initialiser, not a constructor - the object already exists by
the time it runs. `self` is the instance, passed explicitly.

## 2. Class vs Instance Attributes

```python
class Student:
    school = "LearnQuest"          # shared by ALL instances

    def __init__(self, name):
        self.name = name           # unique per instance
```

Beware mutable class attributes - they are shared, which is rarely what you
want:

```python
class Basket:
    items = []        # BUG: every Basket shares one list
```

## 3. Dunder Methods Make Objects Feel Native
Special ("dunder") methods hook your class into Python's syntax:

```python
class Money:
    def __init__(self, amount):
        self.amount = amount

    def __repr__(self):
        return f"Money({self.amount})"

    def __eq__(self, other):
        return isinstance(other, Money) and self.amount == other.amount

    def __add__(self, other):
        return Money(self.amount + other.amount)

Money(5) + Money(7)      # Money(12)
Money(5) == Money(5)     # True
```

- `__repr__` - unambiguous developer-facing text. Always define it.
- `__eq__` - value equality. Define `__hash__` too if instances go in a set.
- `__len__`, `__iter__`, `__getitem__` - make your object behave like a container.

## 4. Prefer Composition Over Deep Inheritance
Inheritance couples classes tightly. A `Course` that *has* a list of `Lesson`
objects is usually clearer than a tangled hierarchy.

## 5. Dataclasses Remove Boilerplate

```python
from dataclasses import dataclass

@dataclass
class Student:
    name: str
    score: int = 0
```

This generates `__init__`, `__repr__` and `__eq__` for you.

## Practice
1. Give `Money` a `__lt__` so a list of `Money` can be sorted.
2. Rewrite `Student` as a dataclass and confirm equality works.
""",
    },
]


WEB_LESSONS: list[dict[str, Any]] = [
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222240001"),
        "title": "Semantic HTML and Modern CSS Layout",
        "order_index": 1,
        "estimated_minutes": 25,
        "topic_tags": ["web.html_css"],
        "content_md": """# Semantic HTML and Modern CSS Layout

## 1. Semantics Before Styling
`<div>` carries no meaning. Semantic elements describe *what* the content is,
which screen readers and search engines rely on:

```html
<header>, <nav>, <main>, <article>, <section>, <aside>, <footer>
```

```html
<!-- Weak -->
<div class="header"><div class="nav">...</div></div>

<!-- Meaningful -->
<header><nav>...</nav></header>
```

A page should have exactly one `<main>`, and headings should descend without
skipping levels (`h1` → `h2` → `h3`).

## 2. The Box Model
Every element is a box: content, then `padding`, then `border`, then `margin`.
Set this once and layout stops fighting you:

```css
*, *::before, *::after { box-sizing: border-box; }
```

Now `width: 300px` means the *visible* box is 300px, padding included.

## 3. Flexbox - One Dimension
Use Flexbox to distribute items along a single axis:

```css
.toolbar {
  display: flex;
  align-items: center;   /* cross axis */
  justify-content: space-between;
  gap: 1rem;             /* replaces margin hacks */
}
```

## 4. Grid - Two Dimensions
Use Grid when you need rows *and* columns:

```css
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1.5rem;
}
```

That single rule produces a responsive card grid with no media queries: columns
are at least 260px and share leftover space equally.

## 5. Mobile First
Write the small-screen rules first, then layer on larger screens:

```css
.sidebar { display: none; }

@media (min-width: 1024px) {
  .sidebar { display: block; }
}
```

## Practice
1. Rebuild a navbar using Flexbox with the logo left and links right.
2. Make a card grid that goes 1 → 2 → 3 columns without writing media queries.
""",
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222240002"),
        "title": "JavaScript Essentials for Applications",
        "order_index": 2,
        "estimated_minutes": 30,
        "topic_tags": ["web.javascript"],
        "content_md": """# JavaScript Essentials for Applications

## 1. `const`, `let` - and Never `var`

```javascript
const MAX = 10;      // cannot be reassigned
let count = 0;       // reassignable
```

`const` prevents *reassignment*, not *mutation* - `const arr = []` still allows
`arr.push(1)`.

## 2. Array Methods Over Loops

```javascript
const users = [
  { name: 'Ada', active: true },
  { name: 'Linus', active: false },
];

const activeNames = users
  .filter((u) => u.active)
  .map((u) => u.name);          // ['Ada']

const total = scores.reduce((sum, n) => sum + n, 0);
```

`map`, `filter` and `reduce` return new arrays, which is exactly what React
wants - mutating state in place will not trigger a re-render.

## 3. Destructuring and Spread

```javascript
const { name, score = 0 } = student;     // with a default
const [first, ...rest] = items;

const updated = { ...student, score: 100 };   // copy + override
const combined = [...listA, ...listB];
```

## 4. Asynchronous Code
Promises represent a value that arrives later. `async/await` makes them read
like ordinary code:

```javascript
async function loadCourses() {
  try {
    const res = await fetch('/api/courses');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('Failed to load courses', err);
    return { items: [] };
  }
}
```

**A rejected promise you never catch is a silent bug.** Always handle failure.

## 5. Optional Chaining and Nullish Coalescing

```javascript
const city = user?.address?.city ?? 'Unknown';
```

`?.` short-circuits on `null`/`undefined`; `??` falls back only for
`null`/`undefined` - unlike `||`, which also swallows `0` and `''`.

## Practice
1. Fetch the course list and render the titles, handling the error path.
2. Given an array of scores, compute the average with `reduce`.
""",
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222240003"),
        "title": "Thinking in React Components",
        "order_index": 3,
        "estimated_minutes": 30,
        "topic_tags": ["web.react"],
        "content_md": """# Thinking in React Components

## 1. UI as a Function of State
A component maps state to markup. Change the state, React re-renders:

```jsx
function Counter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(count + 1)}>Clicked {count}×</button>;
}
```

## 2. Props Down, Events Up
Data flows one way. A child receives `props` and reports back through
callbacks - it never writes to its parent's state directly.

```jsx
function CourseList({ courses, onSelect }) {
  return (
    <ul>
      {courses.map((c) => (
        <li key={c.id}>
          <button onClick={() => onSelect(c)}>{c.title}</button>
        </li>
      ))}
    </ul>
  );
}
```

## 3. Keys Must Be Stable
`key` tells React which item is which between renders. Using the array index
breaks when the list reorders or an item is removed:

```jsx
{items.map((item, i) => <Row key={i} />)}      // fragile
{items.map((item) => <Row key={item.id} />)}   // correct
```

## 4. State Is Immutable

```jsx
setItems([...items, newItem]);              // add
setItems(items.filter((i) => i.id !== id)); // remove
setUser({ ...user, name: 'Ada' });          // update a field
```

Mutating in place (`items.push(...)`) keeps the same reference, so React sees
no change and skips the re-render.

## 5. Effects Are for Synchronising With the Outside World
Not for deriving values - compute those during render.

```jsx
useEffect(() => {
  let cancelled = false;

  fetchCourses().then((data) => {
    if (!cancelled) setCourses(data.items);
  });

  return () => { cancelled = true; };   // avoids setting state after unmount
}, []);
```

The cleanup function matters: without it, a slow request that resolves after
the user navigates away updates a component that no longer exists.

## Practice
1. Build a search box that filters a list held in state.
2. Add a loading and an error state to the fetch above.
""",
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222240004"),
        "title": "Designing and Consuming REST APIs",
        "order_index": 4,
        "estimated_minutes": 25,
        "topic_tags": ["web.rest_api"],
        "content_md": """# Designing and Consuming REST APIs

## 1. Resources and Verbs
A REST URL names a **resource** (a noun); the HTTP method says what to do:

| Method | Path | Meaning |
|--------|------|---------|
| `GET` | `/api/courses` | list courses |
| `GET` | `/api/courses/{slug}` | one course |
| `POST` | `/api/courses` | create |
| `PATCH` | `/api/courses/{id}` | partial update |
| `DELETE` | `/api/courses/{id}` | remove |

Avoid verbs in paths - `/api/getCourses` duplicates what `GET` already says.

## 2. Status Codes Carry Meaning

- `200 OK` - succeeded
- `201 Created` - new resource made
- `400 Bad Request` - malformed input
- `401 Unauthorized` - not signed in
- `403 Forbidden` - signed in, not allowed
- `404 Not Found` - no such resource
- `500 Internal Server Error` - the server broke

Returning `200` with `{"error": "..."}` defeats every HTTP client's error
handling. Use the real code.

## 3. Paginate Every List
Unbounded lists are a production outage waiting to happen:

```
GET /api/courses?page=1&page_size=20
```

```json
{ "items": [...], "total": 137, "page": 1, "page_size": 20 }
```

Returning `total` lets the client render page controls without guessing.

## 4. Authentication
Send a bearer token; never put credentials in the URL, where they end up in
server logs and browser history:

```http
Authorization: Bearer <token>
```

## 5. CORS
A browser blocks cross-origin requests unless the server opts in. If the API
runs on `localhost:8000` and the app on `localhost:5173`, the API must list
that origin explicitly - otherwise the request fails before your code sees it.

## Practice
1. Design the endpoints for a "notes" resource, with correct status codes.
2. Call a paginated endpoint and render a "next page" button that stops at the
   end using `total`.
""",
    },
]


COURSES: list[dict[str, Any]] = [
    {
        "id": uuid.UUID("11111111-1111-1111-1111-111111111112"),
        "slug": "python-programming-foundations",
        "title": "Python Programming Foundations",
        "description": (
            "Build a genuine mental model of Python: how names bind to objects, why "
            "mutable defaults bite, how scope resolves, and how to write classes that "
            "feel native. Four hands-on lessons from variables to dunder methods."
        ),
        "subject": "Programming",
        "difficulty": "beginner",
        "estimated_hours": 5,
        "lessons": PYTHON_LESSONS,
    },
    {
        "id": uuid.UUID("11111111-1111-1111-1111-111111111113"),
        "slug": "modern-web-development-react",
        "title": "Modern Web Development with React",
        "description": (
            "Go from semantic HTML and CSS Grid to React components backed by a real "
            "REST API. Covers one-way data flow, stable keys, immutable state, effect "
            "cleanup, pagination, status codes and CORS."
        ),
        "subject": "Web Development",
        "difficulty": "intermediate",
        "estimated_hours": 8,
        "lessons": WEB_LESSONS,
    },
]


# --------------------------------------------------------------------------- #
# Seeding
# --------------------------------------------------------------------------- #


def seed_extra_courses(db: Session, created_by: uuid.UUID | None = None) -> list[Course]:
    """Insert (or refresh) the additional catalogue courses.

    Idempotent, matching ``seed_courses``: an existing course is reused and its
    lessons are replaced, so re-running never duplicates rows.
    """
    seeded: list[Course] = []

    for spec in COURSES:
        course = db.query(Course).filter(Course.slug == spec["slug"]).first()

        if not course:
            course = Course(
                id=spec["id"],
                title=spec["title"],
                slug=spec["slug"],
                description=spec["description"],
                subject=spec["subject"],
                difficulty=spec["difficulty"],
                estimated_hours=spec["estimated_hours"],
                is_published=True,
                source="seeded",
                is_private=False,
                created_by=created_by,
            )
            db.add(course)
            db.commit()
            db.refresh(course)
            logger.info("Created course: %s", course.title)
        else:
            logger.info("Course already exists: %s", course.title)

        # Replace lessons so edits to the content above take effect on re-run.
        db.query(Lesson).filter(Lesson.course_id == course.id).delete()

        for item in spec["lessons"]:
            db.add(
                Lesson(
                    id=item["id"],
                    course_id=course.id,
                    title=item["title"],
                    order_index=item["order_index"],
                    estimated_minutes=item["estimated_minutes"],
                    topic_tags=item["topic_tags"],
                    content_md=item["content_md"].strip(),
                    video_url=None,
                )
            )

        db.commit()
        logger.info("Seeded %s with %d lessons.", course.title, len(spec["lessons"]))
        seeded.append(course)

    return seeded


def main() -> None:
    """Allow seeding just these courses: ``python -m app.seed.extra_courses``."""
    logging.basicConfig(level=logging.INFO)
    from app.database import Base, database_is_configured, get_engine, get_session_factory

    if not database_is_configured():
        logger.warning("DATABASE_URL is not configured. Seed cannot run against a database.")
        return

    Base.metadata.create_all(bind=get_engine())
    db = get_session_factory()()
    try:
        seed_extra_courses(db)
        logger.info("Extra course seeding completed successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
