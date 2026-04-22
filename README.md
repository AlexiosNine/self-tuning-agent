# Self-Tuning Agent

[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A harness-based self-optimizing question-answering agent with evaluation, strategy versioning, and fine-tuning dataset curation.

## Architecture

Three-layer architecture:
- **Agent Runtime**: Executes versioned strategies to answer questions
- **Evaluation Engine**: Scores answers using automatic and human signals
- **Harness Orchestrator**: Manages optimization and strategy promotion

## Features

- 🔄 **Self-optimizing**: Automatically improves based on evaluation results
- 📊 **Strategy versioning**: Track and rollback strategy changes
- 🎯 **Multi-provider support**: Abstract interface for Claude, OpenAI, and local models
- 📈 **Dataset curation**: Collect high-quality samples for fine-tuning
- 🧪 **Deterministic evaluation**: Rule-based scoring for fast iteration

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/OWNER/REPO.git
cd self-tunning

# Install dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test suite
pytest tests/integration/

# Run with verbose output
pytest -v
```

### Basic Usage

```python
from pathlib import Path
from src.agent.runtime import AgentRuntime
from src.agent.providers.claude import ClaudeProvider
from src.harness.version_manager import VersionManager
from anthropic import Anthropic

# Initialize components
strategies_dir = Path("strategies")
manager = VersionManager(strategies_dir)

# Create initial strategy
manager.create_version("v001", None, {"system_prompt": "Answer clearly and concisely."})
manager.promote_to_production("v001")

# Set up runtime with Claude provider
client = Anthropic(api_key="your-api-key")
provider = ClaudeProvider(client)
runtime = AgentRuntime(version_manager=manager, provider=provider, model_name="claude-sonnet-4-6")

# Answer a question
result = runtime.answer("What is Docker?")
print(f"Answer: {result.answer}")
print(f"Strategy: {result.strategy_version}")
```

## Development

### Project Structure

```
self_tunning/
├── src/
│   ├── agent/          # Agent Runtime layer
│   ├── evaluation/     # Evaluation Engine layer
│   ├── harness/        # Harness Orchestrator layer
│   ├── dataset/        # Dataset curation pipeline
│   └── common/         # Shared types and config
├── tests/              # Test suite
├── .github/workflows/  # CI/CD pipelines
└── docs/               # Design specs and plans
```

### Code Quality

This project uses:
- **Ruff**: Fast linting and formatting
- **mypy**: Static type checking
- **pytest**: Testing framework with coverage
- **bandit**: Security scanning
- **pre-commit**: Git hooks for quality checks

```bash
# Run linter
ruff check src/ tests/

# Format code
ruff format src/ tests/

# Type check
mypy src/

# Security scan
bandit -r src/
```

## CI/CD Pipeline

### Continuous Integration

On every push/PR, the CI pipeline runs:
1. **Lint**: Code style and formatting checks
2. **Type Check**: Static type analysis with mypy
3. **Security**: Vulnerability scanning with bandit and safety
4. **Tests**: Full test suite with 80% coverage requirement

All jobs run in parallel for fast feedback (~2-3 minutes).

### Continuous Deployment

On version tags (`v*.*.*`), the CD pipeline:
1. Validates tag matches `pyproject.toml` version
2. Builds Python package (sdist + wheel)
3. Tests the built package
4. Builds and pushes Docker image to GitHub Container Registry
5. Creates GitHub Release with auto-generated notes

### Creating a Release

```bash
# 1. Update version in pyproject.toml
# 2. Commit changes
git add pyproject.toml
git commit -m "chore: bump version to 0.2.0"

# 3. Create and push tag
git tag v0.2.0
git push origin v0.2.0

# CD pipeline triggers automatically
```

## Docker

### Building Locally

```bash
docker build -t self-tunning:latest .
```

### Running Container

```bash
docker run -it --rm \
  -e ANTHROPIC_API_KEY=your-api-key \
  -v $(pwd)/strategies:/app/strategies \
  self-tunning:latest
```

### Using Pre-built Image

```bash
docker pull ghcr.io/OWNER/REPO:latest
```

## Configuration

### Environment Variables

- `ANTHROPIC_API_KEY`: API key for Claude provider (required for production)

### Config File

Edit `config.yaml` to customize:
- Model provider and name
- Strategy and dataset directories
- Optimization thresholds

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and quality checks (`pytest && ruff check`)
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `chore:` Maintenance tasks
- `test:` Test additions or changes

## Documentation

- [Design Specification](docs/superpowers/specs/2026-04-21-self-tunning-agent-design.md)
- [Implementation Plan](docs/superpowers/plans/2026-04-22-self-tunning-agent-implementation.md)
- [Architecture Rules](.claude/rules/architecture.md)

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built with:
- [Anthropic Claude](https://www.anthropic.com/) - AI model provider
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [pytest](https://pytest.org/) - Testing framework
- [Ruff](https://github.com/astral-sh/ruff) - Fast Python linter
