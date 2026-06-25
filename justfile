# Praxis dev tasks — run `just` to list, or `just <recipe>`.
# Backend and frontend are long-running; start each in its own terminal.

# List available recipes (default).
default:
    @just --list

# Start the FastAPI backend (knowledge/serve) on http://localhost:8000
backend:
    uv run python -m knowledge.serve

# Start the React dashboard (Vite) on http://localhost:5173
frontend:
    cd frontend-react && npm run dev

# Install frontend dependencies
install-frontend:
    cd frontend-react && npm install

# Quick health check that the backend is up
health:
    curl -s http://localhost:8000/health

# --- Local Postgres (pgvector) -----------------------------------------------
# For running the DSN-backed tests/evals (e.g. hybrid_keyword_retrieval) without
# touching prod RDS. The app resolves PRAXIS_DB_URL first, so once it's exported
# nothing reaches AWS Secrets Manager.
#
#   just db-up                            # start the container (waits until ready)
#   export PRAXIS_DB_URL=$(just db-url)   # point THIS shell at it
#   uv run python -m knowledge.serve      # ...then run the backend / tests / evals
#   just db-down                          # stop + delete the container & its data
#
# A recipe can't export into your shell, hence the explicit `export` step above.

# Start the local pgvector Postgres (idempotent; waits until it accepts connections).
db-up:
    docker compose up -d --wait db
    @echo "Local DB ready. Point this shell at it with:"
    @echo "    export PRAXIS_DB_URL=$(just db-url)"

# Print the local DB connection string (use: export PRAXIS_DB_URL=$(just db-url)).
db-url:
    @echo "postgresql://praxis:praxis@localhost:5432/praxis"

# Open a psql shell in the running local DB.
db-shell:
    docker compose exec db psql -U praxis -d praxis

# Stop and remove the local Postgres container and its data volume.
db-down:
    docker compose down -v

# Start the local observability UI (Arize Phoenix) on http://localhost:6006 (Docker)
observability:
    docker start phoenix 2>/dev/null || docker run -d --name phoenix -p 6006:6006 arizephoenix/phoenix:version-17.9.0
    @echo "Phoenix UI: http://localhost:6006"
    @echo "To send traces: run the backend with PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006"

# Stop the local Phoenix container
observability-stop:
    docker stop phoenix

# Start the Phoenix proxy on http://localhost:8800 (dashboard trace links)
observability-proxy:
    @echo "Set VITE_PRAXIS_PHOENIX_PROXY_URL=http://localhost:8800 in frontend-react/.env.local"
    uv run uvicorn frontend.phoenix_proxy.app:app --port 8800
