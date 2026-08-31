FROM oven/bun:1 AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile
COPY frontend/ ./
RUN bun run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WORK_DIR=/tmp/housing-cleaner

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/ /app/backend/
COPY resources/ /app/resources/
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

RUN mkdir -p /tmp/housing-cleaner

EXPOSE 8765

CMD ["python", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "1"]
