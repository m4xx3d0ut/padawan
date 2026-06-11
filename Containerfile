FROM python:3.11-slim

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends git nodejs \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md /app/
COPY src /app/src
COPY content /app/content
COPY docs /app/docs
RUN python -m pip install --no-cache-dir .
ENV PADAWAN_HOST=0.0.0.0
ENV PADAWAN_PORT=8787
ENV PADAWAN_CONTENT_DIR=/app/content/courses
ENV PADAWAN_DOCS_DIR=/app/docs/wiki
ENV PADAWAN_STATE_DIR=/data/padawan
ENV TMPDIR=/data/padawan/tmp
ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 8787
CMD ["padawan", "serve", "--host", "0.0.0.0", "--port", "8787"]
