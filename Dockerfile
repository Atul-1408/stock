# ---- build frontend ----
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- backend + built frontend ----
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 FLASK_ENV=production
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY src/ ./src/
COPY models/ ./models/
COPY --from=web /web/dist ./frontend/dist
RUN useradd --create-home --uid 10001 appuser && mkdir -p /app/data /app/logs && chown -R appuser:appuser /app
USER appuser
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/health/live', timeout=3)"
# One worker: SQLite is single-writer and the rate limiter is in-memory until Redis is added.
CMD ["gunicorn", "--chdir", "src", "-w", "1", "--threads", "8", "--timeout", "60", "--graceful-timeout", "30", "--keep-alive", "5", "--access-logfile", "-", "--error-logfile", "-", "-b", "0.0.0.0:5000", "app:app"]
