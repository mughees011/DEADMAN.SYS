# UI/UX Design Brief — Survival Agent Dashboard

This extends the visual direction already prototyped in `agent-survival-sim.jsx`
("Zero Means Gone") — a ledger/vitals-monitor feel, not a friendly consumer app. The
stakes are real money and permanent death; the UI should read as serious instrumentation,
not a game.

## 1. Design tokens

**Color palette**
| Token | Hex | Use |
|---|---|---|
| `bg-base` | `#0b0f12` | App background |
| `bg-panel` | `#0e1315` | Cards/panels |
| `border` | `#1c2428` | Panel borders, dividers |
| `text-primary` | `#e4ebea` | Headings, primary numbers |
| `text-muted` | `#7b8c8a` | Secondary text, descriptions |
| `text-dim` | `#5a6669` | Labels, timestamps |
| `accent-alive` | `#7fd9bf` | Alive status, positive values, section labels |
| `accent-gold` | `#e8c974` | Boss/generation-0 marker, balances above threshold |
| `accent-danger` | `#d97a7a` / `#e05252` (kill switch) | Death, losses, kill switch control |
| `accent-warn` | `#d99a9a` | Low balance warning (agent nearing death) |

Do not introduce a warm cream/terracotta or generic dark+neon-green palette outside
these tokens — this system already has a specific identity from the prototype; extend
it rather than reinventing per screen.

**Typography**
- Primary typeface: monospace throughout (`IBM Plex Mono` or `JetBrains Mono`) — every
  number in this app represents a real dollar amount or a real countdown, and monospace
  reinforces that this is instrumentation, not marketing copy.
- One weight for headings (semibold), one for body/labels (regular). No third
  decorative typeface — restraint matters more here than personality.
- Tracked-out, small-caps-style section labels (`0.2em` letter spacing, uppercase,
  11px) for panel headers — already established in the prototype, keep consistent.

**Layout**
- Dark, dense, panel-based grid — bordered cards with sharp corners (no/minimal
  border-radius), consistent with the ledger aesthetic.
- Numbers are right-aligned or tabular-numeric everywhere balances appear, so columns
  of figures line up — this is a finance-adjacent tool and should look like one.

## 2. Screens

### 2.1 Home / Roster
- Header: system-wide stats (tick/day count, agents alive, agents dead, total real
  balance under management, total tax reserve).
- Kill switch: persistent, high-contrast, top-right, never scrolls out of view. This is
  the single most important control in the whole app and should never compete visually
  with anything else — it should be immediately findable in under 2 seconds.
- Agent list: indented by generation (visually showing the family tree inline), each
  row = name, generation badge, balance (color-coded: gold above spawn threshold, warn-red
  below a low threshold, muted if dead), days-since-income counter, status.

### 2.2 Agent detail
- Balance-over-time line chart (reuse the `recharts` pattern from the prototype).
- Full decision log: each entry shows the situation snapshot, the chosen action, the
  agent's own legality justification, and the real result — presented as a vertical
  timeline, most recent first.
- If dead: a distinct "final entry" styled differently (e.g. a horizontal rule, skull
  icon, muted-red border) showing cause of death and the lesson it generated.

### 2.3 Family tree
- Simple indented/nested tree view is sufficient for v1 — do not over-invest in a
  force-directed graph unless the population genuinely gets large enough to need it.

### 2.4 Collective memory
- Reverse-chronological feed of lesson strings, each tagged with which agent/generation
  produced it — this is the system's only form of "growing up," so it deserves a clear,
  readable home rather than being buried in individual agent logs.

### 2.5 Kill switch confirmation
- Full-screen or modal takeover on click — this should never be a casual, accidental
  action. Confirmation copy states plainly what will happen ("Every agent stops
  immediately. None of them can be restarted until you turn this off.").
- Once engaged, a persistent top banner in `accent-danger` remains visible on every
  screen until deactivated — the Boss should never be unsure whether the system is live.

## 3. Interaction notes
- No decorative animation. The only motion that earns its place: a subtle pulse on the
  "alive" status dot, and a brief flash on the row of an agent that just changed state
  (spawned, died, earned) — signal, not decoration.
- Empty states matter: a fresh system with one $0 agent and no history should say
  plainly what's about to happen ("Agent-0 has 7 days to earn its first dollar or it
  dies"), not show a blank chart with no context.

## 4. Signature element
The single memorable device for this whole app: the **days-since-income countdown**,
rendered like a dead-man's switch (a shrinking bar or ticking number toward 7), visible
on every agent card. It's the one piece of UI that makes the stakes legible at a glance,
and it's specific to this project's actual mechanic rather than a generic dashboard widget.
