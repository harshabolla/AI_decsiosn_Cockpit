.PHONY: setup dev dev-backend dev-frontend test lint clean docker-up docker-down

setup:
	cd apps/backend && pip install -r requirements.txt
	cd apps/frontend && npm install

dev-backend:
	cd apps/backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd apps/frontend && npm run dev

dev:
	@echo "Starting backend and frontend..."
	docker compose up --build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

test:
	cd apps/backend && pytest tests/

lint:
	cd apps/frontend && npm run lint
	cd apps/backend && flake8 app/ || true

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".next" -exec rm -rf {} +
