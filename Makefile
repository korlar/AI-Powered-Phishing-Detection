.PHONY: dev backend frontend test lint format train docker clean help


# --- Development ---

dev: ## Start both backend and frontend locally
	@echo "Starting backend on port 8000..."
	uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
	@echo "Starting frontend on port 8501..."
	BACKEND_URL=http://localhost:8000 streamlit run frontend/streamlit_app.py --server.address=0.0.0.0

backend: ## Start only the FastAPI backend
	uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

frontend: ## Start only the Streamlit frontend
	BACKEND_URL=http://localhost:8000 streamlit run frontend/streamlit_app.py --server.address=0.0.0.0

# --- Quality ---

test: ## Run the full test suite
	python -m pytest tests/ -v --tb=short

lint: ## Run ruff + mypy
	ruff check .
	mypy backend src

format: ## Format code with ruff
	ruff format .
	ruff check . --fix

# --- Training ---

train-email: ## Train the email RoBERTa model
	python -m src.models.train_roberta --task email --config configs/training.yaml

train-url: ## Train the URL RoBERTa model
	python -m src.models.train_roberta --task url --config configs/training.yaml

train: train-email train-url ## Train both models

# --- Docker ---

docker: ## Build and run with Docker Compose
	docker compose -f Docker/docker-compose.yml up --build

docker-build: ## Build Docker image only
	docker build -f Docker/Dockerfile -t phishing-detection-roberta:latest .

# --- Utilities ---

clean: ## Remove Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
