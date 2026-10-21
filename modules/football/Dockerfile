# Multi-stage build: install deps in a builder, copy a slim runtime image.
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app

# Non-root user
RUN useradd --create-home --uid 10001 appuser

COPY --from=builder /install /usr/local
COPY app ./app
COPY model ./model

USER appuser
EXPOSE 8080

# gunicorn runs the Flask app; readiness/liveness are served by the app.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", \
     "--threads", "4", "--timeout", "60", "app.wsgi:app"]
