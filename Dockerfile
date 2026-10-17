FROM python:3.12-slim AS app-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FOUNDER_OUTREACH_DB_PATH=/data/founders.db

WORKDIR /app

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app app \
    && mkdir -p /data \
    && chown app:app /data

COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app main.py models.py database.py migrate_database.py ./
COPY --chown=app:app frontend ./frontend

FROM app-base AS test
COPY requirements-dev.txt ./requirements-dev.txt
RUN python -m pip install --no-cache-dir -r requirements-dev.txt
COPY --chown=app:app tests ./tests
COPY --chown=app:app test_search.py ./test_search.py
USER app
CMD ["python", "-m", "pytest", "-q"]

FROM app-base AS production
USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/').read()" || exit 1

CMD ["sh", "-c", "python migrate_database.py && exec uvicorn main:app --host 0.0.0.0 --port 8000"]
