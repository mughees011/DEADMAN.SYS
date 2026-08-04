# Backend Schema — Survival Agent System

SQLAlchemy models, SQLite for v1 (Postgres-compatible by design — no SQLite-only types
used). All monetary values stored as `Numeric`/`Decimal`, never `float`, to avoid
rounding drift on real money.

## 1. Tables

### `agents`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | |
| `generation` | Integer | 0 = original Boss-created agent |
| `parent_id` | UUID (FK → agents.id, nullable) | Null for generation 0 |
| `name` | String | Display name |
| `balance` | Numeric(12,2) | Spendable real balance |
| `tax_reserve` | Numeric(12,2) | Set-aside amount, default 0 |
| `tax_rate` | Numeric(4,3) | e.g. 0.150, Boss-configurable per agent |
| `alive` | Boolean | Default true |
| `paused` | Boolean | Default false — Boss-only per-agent freeze |
| `born_at` | DateTime | |
| `died_at` | DateTime (nullable) | |
| `cause_of_death` | Text (nullable) | |
| `last_income_at` | DateTime | Used for the 7-day dead-man check |

### `channels`
| Column | Type | Notes |
|---|---|---|
| `id` | String (PK) | e.g. `"trading"` |
| `description` | Text | Shown to the agent as the tool description |
| `enabled` | Boolean | Boss can disable a channel system-wide |

### `agent_logs`
One row per decision cycle — this is the audit trail, not optional debug output.
| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | |
| `agent_id` | UUID (FK → agents.id) | |
| `cycle_at` | DateTime | |
| `situation_snapshot` | JSON | Balance, days-since-income, memory passed in, boss notes passed in |
| `chosen_channel` | String (FK → channels.id, nullable if "wait") | |
| `plan_text` | Text | Agent's stated plan |
| `legality_justification` | Text | Agent's stated legality reasoning |
| `net_result` | Numeric(12,2) (nullable) | Real $ result, null if "wait" or channel error |
| `tax_deducted` | Numeric(12,2) (nullable) | |
| `error` | Text (nullable) | e.g. "channel not wired up", API failure |

### `lessons`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | |
| `source_agent_id` | UUID (FK → agents.id) | Which dead agent produced this |
| `created_at` | DateTime | |
| `text` | Text | The lesson string |

### `boss_notes`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | |
| `agent_id` | UUID (FK → agents.id, nullable) | Null = applies system-wide |
| `created_at` | DateTime | |
| `text` | Text | |

### `system_state`
Single-row table (or key/value table if you prefer) holding global flags.
| Column | Type | Notes |
|---|---|---|
| `kill_switch` | Boolean | Default false |
| `kill_switch_set_at` | DateTime (nullable) | |
| `updated_by` | String | Always "boss" in v1 (single user) |

## 2. Relationships
- `agents.parent_id` → `agents.id` (self-referential, one-to-many: one parent → many
  children). This is what powers the family tree view.
- `agent_logs.agent_id` → `agents.id` (many-to-one).
- `lessons.source_agent_id` → `agents.id` (many-to-one).
- `boss_notes.agent_id` → `agents.id`, nullable for system-wide notes (many-to-one,
  optional).
- `agent_logs.chosen_channel` → `channels.id` (many-to-one, nullable).

## 3. Authentication flow (v1 — intentionally minimal)
This is a single-user tool for the Boss only. Do not build multi-tenant auth, OAuth,
or role systems — that's speculative complexity for a system with exactly one user.
- Dashboard backend (FastAPI) protected by a single hardcoded credential pair (or a
  long-lived bearer token) stored in `.env` as `DASHBOARD_USER` / `DASHBOARD_PASS_HASH`.
- Session via a signed cookie (e.g. `itsdangerous`) after login; no separate user table
  needed.
- If this ever becomes multi-user, that's a v2 redesign, not a v1 concern — flag it as
  future scope rather than building it in speculatively now.

## 4. Data integrity rules to enforce at the application layer
- `balance` must never go negative in storage — the moment a channel result would push
  it ≤ 0, the death transaction (mark dead, write lesson, zero out) happens atomically
  with the balance update, in one DB transaction.
- An agent with `alive = false` must be fully immutable afterward — no code path may
  update its `balance`, `paused`, or `alive` fields once death is recorded. Enforce this
  in application logic (e.g. a guard at the top of every write path), not just by
  convention.
- Spawning a child and debiting the parent's balance for the spawn cost must happen in
  a single transaction — never create a child without the parent's balance reflecting
  the cost, and vice versa.
