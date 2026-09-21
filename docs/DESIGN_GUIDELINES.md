# LearnQuest Design Guidelines

**Status:** authoritative for all frontend work.
**Applies to:** everything under `frontend/src/`.
**Read this before building any page or component.**

LearnQuest uses a **professional, information-dense** design language modelled on
HackerRank. Screens are flat, compact and quiet. The UI should recede so the
content — problems, code, progress, data — is what the eye lands on.

If a screen looks like a consumer game, it is wrong for this product.

---

## 1. The five rules

1. **Depth comes from a 1px border, not a shadow.** Cards, tables and inputs use
   `border-line`. Shadows are only for things that genuinely float (dropdowns,
   modals, toasts).
2. **Dense by default.** Body text is **14px**, tables are 13px. Padding is
   `p-4`, not `p-8`. Fit more real information on screen.
3. **Small radii.** `rounded` (4px) for nearly everything, `rounded-lg` (6px) for
   cards. `rounded-pill` is reserved for status chips only.
4. **Colour means status, never decoration.** Green = easy/passing.
   Amber = medium/warning. Red = hard/failing. Purple = the one primary action.
   Everything else is neutral grey.
5. **Normal weights.** `font-medium` (500) for emphasis, `font-semibold` (600)
   for headings. Nothing is `font-extrabold`, nothing is UPPERCASE except small
   `label` / table headers.

---

## 2. Tokens

All tokens live in `frontend/tailwind.config.js`. **Use token names, never raw hex.**

### Colour

| Token | Hex | Use for |
|---|---|---|
| `primary-600` | `#7C3AED` | The one primary action per view, active nav |
| `primary-700` | `#6D28D9` | Hover / pressed |
| `easy` | `#00AF54` | Easy difficulty, passing, solved |
| `medium` | `#FFB300` | Medium difficulty, warnings |
| `hard` | `#E5384B` | Hard difficulty, failures, destructive |
| `info` | `#2D7FF9` | Informational callouts |
| `ink` | `#1F2933` | Headings |
| `body` | `#39424E` | Body copy |
| `muted` | `#6B7885` | Secondary text, table headers |
| `faint` | `#9AA5B1` | Placeholders, disabled |
| `line` | `#E4E7EB` | The 1px hairline border |
| `line-strong` | `#CBD2D9` | Input borders, dividers that must read |
| `surface` | `#FFFFFF` | Cards, tables, panels |
| `canvas` | `#F5F7FA` | Page background |

Each difficulty has `-bg` and `-fg` variants for tinted chips:
`bg-easy-bg text-easy-fg`.

### Type

**Inter** for UI, **JetBrains Mono** for code. Loaded in `frontend/index.html`.

| Role | Classes |
|---|---|
| Page title | `text-2xl font-semibold text-ink` |
| Section heading | `text-lg font-semibold` |
| Card title | `text-base font-semibold` |
| Body | *(default — 14px)* |
| Table / dense text | `text-sm` (13px) |
| Secondary | `text-sm text-muted` |
| Label / table header | `.label` (11px, uppercase, muted) |

### Shape and spacing

- Radius: `rounded` (4px) default, `rounded-lg` (6px) cards, `rounded-pill` chips only.
- Border: **1px** (`border border-line`). The Tailwind default is 1px, so a bare
  `border` is correct.
- Spacing: 4px scale. Cards `p-4`. Sections `py-6` to `py-8`. Keep it tight.

---

## 3. Components

**Always import from `components/ui/`. Never hand-roll a button.**

### Button
```jsx
<Button variant="primary" size="md">Submit</Button>
```
Flat, 32px tall at `md`. Variants: `primary`, `secondary`, `success`, `danger`,
`ghost`, `link`. **One primary per view** — everything else is `secondary` or `ghost`.

### Card
```jsx
<Card>…</Card>
```
1px border, no shadow. `CardHeader` adds a titled header with a divider.

### Tables — the backbone of this UI
Use the `.table-dense` class for problem lists, course lists, leaderboards:
```jsx
<table className="table-dense">
```
13px, 1px row separators, uppercase muted headers. Prefer a table over a grid of
cards whenever the rows share the same columns.

### Badge / chips
`<Badge tone="easy|medium|hard|info|primary|neutral">`. Tinted text on a light
background — never a heavy solid block.

### Inputs
`Input` / `Select`, or the `.field` class. 1px border, 2px focus ring.

---

## 4. Layout and navigation

- **Desktop:** top bar (brand, streak/XP, profile) + 192px left rail.
- **Mobile:** bottom tab bar with the five main destinations.
- Max content width `1400px` — this is a data UI, use the screen.
- Page content is wrapped by `AppLayout`; pages render their own `PageHeader`.

**Never add a nav link to a route that does not exist yet** — it 404s. There's a
note in `AppLayout.jsx` marking where `/practice` goes once it ships.

### Heights must not depend on width

A real bug we shipped: a panel used `aspect-square`, so its height tracked its
width and the column grew to 1176px on wide screens. **Do not derive a layout
height from an aspect ratio.** Pin heights, or let flex/grid distribute them, and
cap aspect-ratio boxes with `max-w-*`.

---

## 5. Motion

Minimal. `animate-fade-in` (150ms) for panels appearing, `animate-shimmer` for
skeletons. That is the whole vocabulary. No bouncing, no celebration animations.

**Never animate React state at 60fps.** We shipped a bug where the avatar called
`setState` on every animation frame, re-rendering a complex SVG 60×/sec. Drive
continuous animation with CSS, or only `setState` when the value actually changes.

---

## 6. Accessibility

Contrast ≥ 4.5:1 for normal text. Measured (WCAG 2.1), so you don't have to guess:

| Combination | Ratio | |
|---|---|---|
| `ink` `#1F2933` on white | 14.76 | ✅ |
| `body` `#39424E` on white | 10.18 | ✅ |
| `body` on `canvas` `#F5F7FA` | 9.48 | ✅ |
| `hard-fg` on `hard-bg` chip | 6.65 | ✅ |
| `info-fg` on `info-bg` chip | 5.76 | ✅ |
| white on `primary-600` (buttons) | 5.70 | ✅ |
| `easy-fg` on `easy-bg` chip | 5.58 | ✅ |
| `medium-fg` on `medium-bg` chip | 5.15 | ✅ |
| `muted` `#6B7885` on white | 4.52 | ✅ *(only just)* |
| **`faint` `#9AA5B1` on white** | **2.50** | ❌ **fails** |

Every colour pair in the system passes AA **except `faint`** — use it for
placeholders and disabled states only, never for real content. `muted` clears
the bar by 0.02, so don't darken the background behind it.
- Focus rings are `ring-2 ring-primary-500/50` and must stay visible.
- Colour is never the only signal. A difficulty chip carries the *word*
  "Easy", not just green.
- Every icon-only button needs `aria-label` or `sr-only` text.
- Re-measure when you add a colour. Do not eyeball it.

---

## 7. Voice and copy

- Plain, direct, second person: "You solved 12 of 40 problems."
- Buttons are verbs: **Submit**, **Run**, **Start**, **Save**.
- Sentence case everywhere. UPPERCASE only for `.label` and table headers.
- No exclamation marks in system text.

---

## 8. Checklist before a PR

- [ ] Imported from `components/ui/` rather than styling a raw element
- [ ] Token names only (`text-muted`, `border-line`) — no raw hex
- [ ] Used a `.table-dense` table where rows share columns
- [ ] One primary button on the view
- [ ] Works at 375px, 768px and 1280px
- [ ] Dark mode checked (`dark:` variants present)
- [ ] Focus visible; icon-only buttons labelled
- [ ] No nav link to a route that doesn't exist
- [ ] No layout height derived from width
- [ ] No `setState` inside a `requestAnimationFrame` loop
- [ ] `npx vite build` passes

---

## 9. Where things live

| Path | What |
|---|---|
| `frontend/tailwind.config.js` | Tokens. **Shared file — change by agreement (plan.md 2.4)** |
| `frontend/src/index.css` | Base layer + `.card`, `.field`, `.chip`, `.label`, `.table-dense` |
| `frontend/src/components/ui/` | The component kit. Extend here, not per-page |
| `frontend/src/components/layout/` | `AppLayout` (bar + rail), `PageHeader` |
| `frontend/index.html` | Inter + JetBrains Mono loading |

Changing a token changes every screen. If a change only suits one page, it
belongs in that page.

---

## Appendix — history

The project previously used a playful, Duolingo-style system (Nunito, chunky 3D
buttons, 2px borders, heavy weights). It was replaced in full on 2026-09-21 with
this professional system at the faculty's request. If you find a component with
`btn3d`, `rounded-2xl`, `font-extrabold` or the `eel`/`wolf`/`swan` colour names,
it was missed in the migration — bring it in line with this document.
