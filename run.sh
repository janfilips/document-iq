#!/bin/bash
poetry run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8880
