FROM python:3.13-slim
WORKDIR /app
COPY backend/requirements.lock /app/backend/requirements.lock
RUN pip install --no-cache-dir -r backend/requirements.lock
COPY backend /app/backend
COPY data/products/products.sqlite3 /app/data/products/products.sqlite3
COPY data/recommendation /app/data/recommendation
ENV PORT=8000
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT} --no-access-log"]
