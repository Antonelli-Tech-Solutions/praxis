# Migrations

Schema changes are applied in two layers:

1. **`knowledge/serve/schema.sql`** — the additive baseline (`CREATE … IF NOT
   EXISTS`). Applied by `python -m knowledge.serve.db`. Add new tables/columns/
   indexes here; never put `DROP`/`ALTER`/data transforms here.
2. **yoyo migrations in this directory** — anything destructive or
   transforming (drop a table/column, change a type, re-tenant rows, backfill).
   yoyo tracks applied migrations in its `_yoyo_migration` ledger, so each runs
   exactly once per database.

On merges to `main` the `migrate-on-main` workflow runs the bootstrap, then
`yoyo apply` over this directory.

## File convention

- `NNNN_short_name.sql` — pure SQL. Statements separated by `;`. Declare order
  with a `-- depends: <other_id> …` comment when it matters.
- `NNNN_short_name.py` — when the migration needs application code (e.g.
  embeddings). Define `steps = [step(fn)]`; `fn(conn)` receives the psycopg3
  backend connection.

Keep migrations idempotent/guarded where practical (`IF EXISTS`,
`ON CONFLICT DO NOTHING`) so a re-run is harmless even before yoyo's ledger
records them.

## Running locally

yoyo picks its backend from the DSN scheme; this project uses psycopg v3, which
yoyo exposes as `postgresql+psycopg`:

```bash
# PRAXIS_DB_URL is a normal postgresql:// DSN; swap the scheme for yoyo.
YOYO_DB="${PRAXIS_DB_URL/postgresql:\/\//postgresql+psycopg://}"

uv run yoyo list  --batch --database "$YOYO_DB" ./migrations   # see status
uv run yoyo apply --batch --database "$YOYO_DB" ./migrations   # apply pending
```
