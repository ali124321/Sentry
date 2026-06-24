#!/bin/bash
cd /Users/ahmedalif/Desktop/sentry/sentry-backend
source venv/bin/activate
export $(cat .env | grep -v "^#" | xargs)
uvicorn app.main:app --reload
