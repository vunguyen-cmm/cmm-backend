# Local Supabase (CMM Backend)

This folder is used by the [Supabase CLI](https://supabase.com/docs/guides/cli) to run Supabase on your machine.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Docker Compose)
- [Supabase CLI](https://supabase.com/docs/guides/cli/getting-started):  
  `brew install supabase/tap/supabase` (macOS) or see the docs

## Commands

From the **project root** (cmm-backend):

```bash
# Start local Supabase (API, Auth, Postgres, Studio)
supabase start

# Stop
supabase stop

# Status and local credentials (API URL, anon key, service_role key)
supabase status
```

After `supabase start`, use the **API URL** and **anon key** from `supabase status` in your `.env`:

- `SUPABASE_URL` = API URL (e.g. `http://127.0.0.1:54321`)
- `SUPABASE_KEY` = anon key (long JWT from `supabase status`)

## Config

- **`config.toml`** – API port (54321), auth, Studio, etc. Restart with `supabase stop` then `supabase start` after changes.
- **`migrations/`** – Add `.sql` migration files here. Run `supabase db reset` to apply all migrations (or `supabase migration up`).

## Testing DB (cmm_dev)

The app config uses `SUPABASE_DB_NAME=cmm_dev` for the testing database name. The default local Postgres database is `postgres`. To use a database named `cmm_dev`:

1. After first `supabase start`, connect to Postgres (port **54322**) and create the DB:
   ```bash
   psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" -c "CREATE DATABASE cmm_dev;"
   ```
2. Or add a migration in `migrations/` that creates and uses `cmm_dev` if your workflow expects it.

Then point any direct Postgres connection strings to `cmm_dev` when needed; the Supabase REST API (used by this app) uses the default project DB.

## Studio

With Supabase running, open **Supabase Studio** at the URL shown by `supabase status` (default: http://127.0.0.1:54323) to browse tables, run SQL, and manage Auth.
