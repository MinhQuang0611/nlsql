#!/bin/sh

echo "⏳ Waiting for database..."

while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done

echo "✅ Database is ready!"

if [ "$APP_ENV" = "development" ]; then
  uvicorn main:app --host 0.0.0.0 --port 8386 --reload
else
  uvicorn main:app --host 0.0.0.0 --port 8386 --workers 2
fi