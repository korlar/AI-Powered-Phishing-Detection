# Contributing to AI-Powered Phishing Detection

Thank you for your interest in contributing! This guide will help you get started.

## 🛠️ Development Setup

### Prerequisites
- Python 3.10+
- Git
- (Optional) NVIDIA GPU with CUDA for model training/inference

### Local Environment

```bash
# 1. Clone the repository
git clone https://github.com/yourname/phishing-detection-roberta.git
cd phishing-detection-roberta

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\Activate.ps1  # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your Hugging Face token and a JWT secret

# 5. Start the backend (Terminal 1)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 6. Start the frontend (Terminal 2)
BACKEND_URL=http://localhost:8000 streamlit run frontend/streamlit_app.py
```

## ✅ Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src --cov=backend

# Run a specific test file
python -m pytest tests/backend/test_api.py -v
```

## 🔍 Code Quality

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Lint
ruff check .

# Auto-fix lint issues
ruff check . --fix

# Format
ruff format .
```

## 📝 Coding Standards

- **Type hints**: All function signatures should include type annotations.
- **Docstrings**: Public functions and classes must have docstrings.
- **Tests**: New features should include corresponding unit tests.
- **Line length**: Maximum 100 characters (configured in `pyproject.toml`).
- **Imports**: Use absolute imports. Group as: stdlib → third-party → local.

## 🔀 Pull Request Process

1. Fork the repository and create a feature branch from `main`.
2. Make your changes with clear, descriptive commit messages.
3. Ensure all tests pass (`python -m pytest`).
4. Ensure code passes linting (`ruff check .`).
5. Update documentation if your change affects public APIs or behavior.
6. Open a Pull Request with a clear description of what changed and why.

## 🐛 Reporting Issues

When reporting bugs, please include:
- Python version and OS
- Steps to reproduce the issue
- Expected vs. actual behavior
- Full error traceback (if applicable)

## 📜 License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
