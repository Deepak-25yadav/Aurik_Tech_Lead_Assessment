#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "Starting Industrial Equipment Monitoring Backend Service"
echo "=========================================================="

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    ./.venv/bin/pip install --upgrade pip
    ./.venv/bin/pip install -r requirements.txt
fi

echo "Seeding database..."
./.venv/bin/python scripts/seed_database.py

echo "Starting Uvicorn server on http://localhost:8000..."
echo "OpenAPI documentation available at: http://localhost:8000/docs"
./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
