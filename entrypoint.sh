#!/bin/sh

if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
  echo "⏳ Waiting for database at $DB_HOST:$DB_PORT..."
  while ! timeout 1 bash -c "</dev/tcp/$DB_HOST/$DB_PORT" 2>/dev/null; do
    sleep 1
  done
  echo "✅ Database is ready!"
else
  echo "⚠️ DB_HOST or DB_PORT not set. Skipping wait..."
fi

if [ "$APP_ENV" = "development" ]; then
  uvicorn main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8388}" --reload
else
  uvicorn main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8388}" --workers 2
fi