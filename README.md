# Founder Outreach

A small FastAPI application for finding public founder profiles, reviewing and approving prospects, tracking outreach, and generating editable message drafts. Search results stay temporary until approved. The app never sends outreach messages automatically.

## What it does

- Searches public pages with DDGS and filters results using founder-related signals.
- Extracts a founder name and company from result titles and snippets.
- Keeps search matches in the current browser page until you approve them.
- Saves approved founders, outreach statuses, and drafts in SQLite.
- Serves the frontend and JSON API from the same FastAPI application.

DDGS is an unofficial metasearch library. Result availability, rate limits, and snippet quality can vary. Search results need human review and do not prove a person's current role.

## Run locally

Requires Python 3.12 or newer.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
uvicorn main:app --reload
```

Open <http://127.0.0.1:8000/>. The API documentation is at <http://127.0.0.1:8000/docs>.

Run the automated checks locally with:

```powershell
pytest
```

To run the suite inside the same Linux environment used by the container:

```powershell
docker build --target test -t founder-outreach-tests .
docker run --rm founder-outreach-tests
```

By default, local development creates `founders.db` beside the Python files. Set `FOUNDER_OUTREACH_DB_PATH` to use another SQLite file.

## Run in a container

Requires Docker Desktop with Docker Compose.

```powershell
docker compose up --build -d
```

Open <http://127.0.0.1:8000/>. Compose stores the database in a named volume, so approved founders and drafts survive container replacement. `docker compose down` stops the app and keeps the volume. `docker compose down -v` also deletes the saved database.

To use a different local port, set `PORT` before starting Compose:

```powershell
$env:PORT = "8080"
docker compose up --build -d
```

Then open <http://127.0.0.1:8080/>.

The image runs as a non-root user, includes a health check, and runs the additive SQLite migration before starting Uvicorn. The local `founders.db` is intentionally excluded from the image and Git; a new container volume starts with an empty database. Back up the container database with:

```powershell
docker compose cp founder-outreach:/data/founders.db .\founders.db.backup
```

## Deployment considerations

- The app has no user login or access control. Put authentication and HTTPS in front of it before exposing it beyond a trusted environment.
- SQLite is suitable for a single app instance with a persistent writable disk. Do not run multiple replicas against a copied or ephemeral database. A multi-instance deployment should move to a managed database such as PostgreSQL and use a shared migration process.
- The deployment platform must preserve `/data`. If it replaces the volume, the saved approvals, statuses, and drafts are lost.
- DDGS depends on public search providers and is not a guaranteed professional-data feed. A deployment may see throttling or changes in results.
- The app prepares drafts only. It does not send email, LinkedIn messages, or connection requests.

## Project files

- `main.py` — FastAPI routes, search filtering, parsing, and draft generation.
- `models.py` and `database.py` — SQLite model and configurable database location.
- `frontend/` — browser interface.
- `tests/` — parser, storage, and API tests.
- `Dockerfile` and `compose.yaml` — container build and persistent local deployment.

## License

No license has been selected yet.
