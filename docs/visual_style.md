# Visual Style Guide

Spartan, 1990s-web-influenced, but clean and intentional. The aesthetic is monochrome-first, text-dense, no decoration for its own sake. Feels like a well-maintained Unix manual page or an early academic website — but with deliberate whitespace.

---

## Palette

| Role | Light mode | Dark mode |
|------|-----------|-----------|
| Background | `#f5f5f0` | `#0f0f0f` |
| Surface (cards, panels) | `#ececec` | `#1a1a1a` |
| Border | `#c0c0c0` | `#2e2e2e` |
| Body text | `#1a1a1a` | `#d4d4d4` |
| Muted / metadata | `#666666` | `#666666` |
| Accent (links, active) | `#1a1aff` | `#6b9fff` |
| Accent hover | `#0000cc` | `#9bbfff` |
| Danger / destructive | `#cc0000` | `#ff4444` |

No gradients. No shadows (except a single 1px border-bottom where a shadow might otherwise go). No rounded corners beyond 2px on inputs.

---

## Typography

**Typefaces**

- Body: `"IBM Plex Mono", "Courier New", monospace` — everything in mono keeps the terminal feel
- Headings: same mono stack, weight `600`
- No serif or sans-serif faces unless a clear need arises

**Scale** (rem, base 16px)

| Label | Size | Weight | Use |
|-------|------|--------|-----|
| `h1` | 1.5rem | 600 | Page title only |
| `h2` | 1.2rem | 600 | Section headers |
| `h3` | 1rem | 600 | Sub-sections |
| body | 1rem | 400 | All prose |
| small / meta | 0.875rem | 400 | Dates, tags, captions |
| code | 0.875rem | 400 | Inline code blocks |

**Line height:** 1.6 for body; 1.3 for headings.  
**Measure:** max `65ch` for prose columns.

---

## Layout

- Single column, centered, max-width `720px` for content pages; `960px` for dashboard pages (Expenses, Wealth).
- Gutters: `1.5rem` horizontal padding at all breakpoints. No complex grid until a feature demands it.
- Vertical rhythm via consistent `margin-bottom` multiples of `1.5rem`.
- No sticky elements except the top nav bar (single line, 48px tall).

---

## Navigation

- Top bar: site name on the left (plain text, no logo), nav links on the right.
- Active link: underlined, no other treatment.
- Restricted links (Library, Expenses, Wealth, Health) do not appear in the nav for unauthenticated users.
- At ≤600px a hamburger toggle button (plain SVG, `currentColor`, no JS library) collapses the nav-links. Clicking the button toggles an `.open` class that shows/hides the link list. No off-canvas drawer — links simply expand below the site name.

---

## Components

### Links
- Underlined by default (body copy and nav).
- Color: accent blue (see palette).
- No `text-decoration: none` except on headings that are links.

### Buttons
- Flat, no shadow, no gradient.
- Border: `1px solid currentColor`.
- Padding: `0.4rem 0.9rem`.
- Primary action: inverted (dark bg, light text).
- Secondary / cancel: outline only.
- Disabled: `opacity: 0.4`, cursor `not-allowed`.

### Inputs & Forms
- Border: `1px solid #c0c0c0` (light) / `#2e2e2e` (dark).
- Focus: `outline: 2px solid accent`, no glow.
- Labels above inputs, not inline placeholders as labels.
- Error text in red beneath the field, prefixed with `!`.

### Tables
- Full-width, `border-collapse: collapse`.
- `1px solid border` on rows only (no column dividers).
- Header row: `font-weight: 600`, `border-bottom: 2px solid border`.
- Zebra striping: alternating `background: surface`.
- Numeric columns: `text-align: right; font-variant-numeric: tabular-nums`.

### Code blocks
- Background: `#1a1a1a` (both modes — always dark).
- Text: `#d4d4d4`.
- Padding: `1rem`.
- No line numbers unless explicitly needed.
- Scroll horizontally; never wrap.

### Tags / Labels
- Inline, `font-size: 0.75rem`, uppercase, `letter-spacing: 0.05em`.
- Border: `1px solid currentColor`, no background fill.
- No color-coded categories — monochrome only.

### Charts (Expenses / Wealth)
- Monochrome or two-tone maximum (accent + muted).
- No pie charts. Prefer bar or line.
- Axes and gridlines in `border` color, thin (`0.5px`).
- No chart titles inside the chart — use a `<caption>` or heading above.

---

## Iconography

No icon fonts. No emoji in UI chrome. If an icon is needed, use a plain SVG inline (single color, `currentColor`, stroke-based, 16×16 or 20×20). Use sparingly — prefer text labels.

---

## Motion

None. No transitions, no animations, no skeleton loaders. If something takes time, show a plain text `Loading…` string.

---

## Page-specific Notes

**Blog** — wide measure for reading (65ch), generous vertical spacing between sections, no sidebar.

**Gallery** — CSS grid of thumbnails, uniform square aspect ratio, no captions by default (reveal on hover via `title` attribute tooltip). Lightbox (high-resolution image in an overlay) is approved for the gallery. No lightbox on any other page.

**Expenses / Wealth / Health** — dense tabular data is expected; prioritize readable tables over cards. Summaries at the top, detail below.

**Library** — index page only: a plain list of documents with title, date, and one-line description. No visual embellishment.
