# Job Finder — backend

FastAPI API with PostgreSQL, SQLAlchemy, Alembic, and Pydantic. Next.js supplies the views. Controllers call services; services query models directly.

**Status:** T00 inspected and executed the minimal FastAPI scaffold. Domain APIs, persistence, authentication, migrations, and Compose infrastructure are not implemented by this repository yet.

**Current priority:** support the frontend mock-workflow phase with accurate contracts and boundaries. Read [backend context](CONTEXT.md) and workspace `../AGENTS.md`; backend feature work follows UI review.

## Run the existing project

During **T00**, fill these entries from `pyproject.toml`, the lockfile, current scripts, and observed behavior. Preserve useful existing README content.

| Item | Verified value |
| --- | --- |
| Python version / environment and package tool | Python `3.14.5` observed; `pyproject.toml` requires `>=3.14`; uv `0.12.9`, `uv.lock`, and `.venv` are present |
| Install command | `uv sync` (uv lock/project metadata verified; sync was not rerun) |
| API start command, URL, health path | `uv run fastapi dev main.py`; startup verified at `http://127.0.0.1:8765`; `GET /` returned `200` and `{"Hello":"World"}`; FastAPI docs are `/docs` |
| Required environment variable names | No `.env.example` or environment reads observed |
| PostgreSQL / Compose status and startup command | No Compose file, PostgreSQL dependency, or database configuration observed; Docker is unavailable |
| Migration command | No Alembic configuration or migration directory observed; no migration command exists |
| Lint / type checks / focused tests | No lint/type/test configuration; `uv run pytest --collect-only -q` unavailable because pytest is not installed; import and in-process health checks passed |

Copy only safe examples into `.env.example`; real credentials stay in ignored environment files. Setup follows the verified baseline until a foundation task changes it.

## Infrastructure target

`compose.yaml` lives here and runs separate API and PostgreSQL services. Use a slim API image and persistent database volume. Use a private persistent upload volume when uploads are introduced. Frontend development can run from the sibling repository.

Redis, workers, object-storage services, and production deployment are outside the initial foundation. A local upload volume is an initial storage choice; multi-instance storage is a later deployment decision.

## Documentation and verification

Start with [START_HERE](docs/START_HERE.md), then [agent rules](AGENTS.md), [architecture](docs/ARCHITECTURE.md), and [plan](docs/PLAN.md).

Check API startup and the actual health response. After infrastructure work, also verify database connectivity, migrations, and persistence through a container restart. For connection failures inspect configuration and service health; do not delete volumes as a troubleshooting shortcut.
