# Contributing to RADAR

Thank you for your interest in contributing to RADAR! This document provides guidelines and information for contributors.

## How to Contribute

### Reporting Issues

- Use the GitHub issue tracker to report bugs
- Include steps to reproduce, expected vs. actual behavior, and your environment details
- Check existing issues before creating a new one

### Submitting Changes

1. Fork the repository
2. Create a feature branch from `main` (`git checkout -b feature/my-feature`)
3. Make your changes with clear, descriptive commit messages
4. Add or update tests as appropriate
5. Ensure all tests pass (`pytest`)
6. Submit a pull request against `main`

### Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR
- Update documentation if your change affects user-facing behavior
- Add tests for new functionality
- Follow the existing code style (enforced by `ruff`)

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/radar.git
cd radar

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Install Playwright browsers (for scraping modules)
playwright install chromium

# Copy environment config
cp .env.example .env

# Start PostgreSQL (via Docker)
docker-compose up -d

# Run tests
pytest
```

## Project Structure

Each module under `src/` follows this pattern:

- `database.py` — SQLAlchemy ORM models
- `workflow.py` — CLI entry point / orchestrator
- `service.py` — Business logic (called by API routers)
- `__init__.py` — Public exports

Cross-cutting concerns live in `src/core/`. The web API lives in `src/web/`.

See `AGENTS.md` for a comprehensive guide to the codebase.

## Code Style

- Python: formatted with `ruff` (line length 100, Python 3.11+)
- Frontend (React/JSX): standard Vite + Tailwind conventions
- Type hints encouraged on all public functions
- Docstrings on modules and non-trivial functions

## Database Migrations

We use Alembic for schema migrations:

```bash
# Create a new migration
alembic revision --autogenerate -m "description of change"

# Apply migrations
alembic upgrade head
```

**Important:** Changes to `CompanyModel` or any core schema require an Alembic migration. Do not modify database tables directly.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific module tests
pytest tests/unit/test_universe.py
```

## License

By contributing to RADAR, you agree that your contributions will be licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
