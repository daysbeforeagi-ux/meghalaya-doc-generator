.PHONY: dev build up down logs shell-backend shell-frontend

dev:
	docker compose up --build

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

shell-backend:
	docker compose exec backend bash

shell-frontend:
	docker compose exec frontend sh

# Extract style profiles from the reference corpus
extract-profiles:
	docker compose exec backend python -m core.style --extract-all

# Purge expired sessions and their files
purge-expired:
	docker compose exec backend python -m core.db --purge-expired
