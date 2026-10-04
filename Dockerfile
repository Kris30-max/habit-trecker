FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml ./
COPY bot ./bot
RUN pip install . && useradd --create-home app

COPY alembic.ini ./
COPY migrations ./migrations

USER app
CMD ["sh", "-c", "alembic upgrade head && python -m bot"]
