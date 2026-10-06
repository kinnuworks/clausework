# Tablekeeper — surface brief (stage 2 onward)

## Who and why
Diners who want a table tonight or on a given evening. From `stage-2.md`: they choose a
restaurant, a date and a party size, scan the times, pick a table (or an approved pair of
tables for a larger party), sign in if needed, book, and keep a reference they can later
look up and cancel. They are often on a phone, sometimes standing outside. They came to
answer one question fast: *where can we sit, and when?*

## Concept — "Evening Service"
The screen is the host stand at 19:00: a dark, quiet room, warm light on the
things that matter. Deep ink-green ground (not black), warm off-white type, and one
candle-amber accent that only ever marks *what you can act on or have chosen*. The
availability view reads like a floor plan written as a timetable: each time is a
large, confident numeral; beside it sits the room — one seating tile per table, its width
proportional to the seats it holds, approved pairs drawn as one tile with a visible link.
A diner reads "the big table is gone at 19:00, the window pair is free at 19:30" without
parsing a single identifier. No cream paper, no wine red, no serif-on-beige, no stock
card grid. The confirmation is a ticket stub: tear line, reference in huge type, copy.

## System (defined once in `ui/css/tokens.css`)
**Colour**
| Token | Value | Use |
|---|---|---|
| `--ink` | `#0E1A16` | page ground |
| `--surface` | `#15241F` | panels, header |
| `--raised` | `#1C2F28` | tiles, inputs |
| `--line` | `#2C4239` | hairlines (decorative) |
| `--line-strong` | `#5C7A6E` | control borders (3.0–3.8:1, non-text UI) |
| `--text` | `#F3ECDF` | body text |
| `--muted` | `#B8B09F` | secondary text |
| `--faint` | `#8E9A92` | hints, meta |
| `--amber` | `#F4B04A` | accent: primary actions, focus, chosen |
| `--amber-ink` | `#1B1206` | text on amber |
| `--refused` | `#FF9B85` | refused / error |
| `--uncertain` | `#A9CBEB` | uncertain outcome |
| `--success` | `#9ED9B0` | succeeded / confirmed |

**Contrast (WCAG 2.x, computed)** — every text pair ≥ 4.5:1, every control boundary ≥ 3:1.
| Foreground | on ink | on surface | on raised |
|---|---|---|---|
| text | 15.17 | 13.71 | 12.02 |
| muted | 8.28 | 7.48 | 6.56 |
| faint | 6.10 | 5.51 | 4.83 |
| amber | 9.47 | 8.55 | 7.50 |
| refused | 8.73 | 7.88 | 6.91 |
| uncertain | 10.55 | 9.53 | 8.36 |
| success | 11.04 | 9.97 | 8.75 |
| line-strong (borders) | 3.79 | 3.42 | 3.00 |
`--amber-ink` on `--amber`: 9.82. Focus ring: 2 px amber + 2 px ink offset (9.47 vs ink).

**Type** — bundled, SIL OFL 1.1 (licences in `ui/fonts/`):
Display *Bricolage Grotesque* (variable, opsz/wdth/wght) for headings, times and the
reference, tabular numerals; text *Instrument Sans* (variable) for everything else.
Scale: `--fs-xs` 0.8125rem · `--fs-sm` 0.875rem · `--fs-base` 1rem · `--fs-md` 1.125rem ·
`--fs-lg` 1.5rem · `--fs-time` clamp(1.75rem, 1.2rem + 2vw, 2.5rem) · `--fs-xl`
clamp(2rem, 1.4rem + 2.6vw, 3.25rem) · `--fs-ref` clamp(2.5rem, 1.6rem + 4vw, 4rem).
**Spacing** 4-pt: `--s1` 4 · `--s2` 8 · `--s3` 12 · `--s4` 16 · `--s5` 24 · `--s6` 32 · `--s7` 48 px.
**Shape** `--r-tile` 10 px · `--r-control` 8 px · `--r-panel` 16 px · pill 999 px.
**Motion** `--dur` 140 ms, `--ease` cubic-bezier(.2,.7,.2,1); sheet slide, tile press,
fade. All motion is removed under `prefers-reduced-motion: reduce`.

## States — distinguishable without colour
| State | Where | Shape / word / icon (colour is extra) |
|---|---|---|
| empty (before search) | grid area | outlined panel, lantern icon, "Pick a restaurant, date and party size" |
| loading | grid, buttons | dashed ghost tiles + "Checking tables…" text, `aria-busy`, button reads "Searching…" |
| no slots | grid area | `no-slots` panel, closed-door icon, "Closed / no times that day" |
| available | tile | solid border, seat dots filled, word "Open" |
| unavailable | tile | diagonal hatch, struck label, word "Taken" or "Too small", no hover lift |
| chosen | tile | amber fill, check icon, word "Chosen", `aria-pressed=true` |
| succeeded | ticket | ticket stub with tear line, check icon, "Booked" |
| refused | form / lookup | left bar + ⚠ icon + "Not booked" heading, message text |
| uncertain | form | dashed outline + ? icon + "Outcome unknown" heading + safe-retry text |
| confirmed / cancelled | lookup | pill with icon: ● confirmed, ⊘ cancelled (struck) |
| signed out (book) | grid | `auth-error` with sign-in / create-account links |

## Widths
375 px (spec minimum, phone), 768 px (tablet), 1280 px (desktop). Tiles wrap; the page
never scrolls sideways. ≥ 960 px: booking panel sits beside the chosen time in a sticky
column. < 960 px: booking panel is a bottom sheet (non-blocking, ≤ 60 vh, scrolls).

## Rules carried from the spec
Exact `data-testid`s, routes `/ /signup /login /lookup`, visible labels, visible focus,
keyboard everything. The surface never invents an outcome: confirmation comes only from
the server's answer; lost answers show `booking-uncertain` and retry the same key + body.
