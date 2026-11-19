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
RUN mkdir -p /app/data
EXPOSE 5000
# One worker: SQLite is single-writer and the rate limiter is in-memory until Redis is added.
CMD ["gunicorn", "--chdir", "src", "-w", "1", "--threads", "8", "-b", "0.0.0.0:5000", "app:app"]
