# Error Handling Guide

## Overview

The self-tuning-agent uses a structured exception hierarchy and comprehensive logging for production-ready error handling.

## Exception Hierarchy

All custom exceptions inherit from `SelfTuningAgentError`:

```python
SelfTuningAgentError (base)
├── VersionNotFoundError
├── VersionAlreadyExistsError
├── InvalidVersionStateError
├── FileOperationError
└── ProviderError
```

## Common Error Scenarios

### 1. No Production Version

**Error:** `VersionNotFoundError: No production strategy version set`

**Cause:** No strategy version has been promoted to production.

**Solution:**
```python
manager.create_version("v001", None, {"system_prompt": "Answer clearly."})
manager.promote_to_production("v001")
```

### 2. Provider API Failures

**Error:** `ProviderError: Provider call failed`

**Cause:** LLM API call failed (rate limit, network error, etc.)

**Solution:** The provider automatically retries with exponential backoff (3 attempts). If all retries fail, check:
- API key is valid
- Network connectivity
- Rate limits not exceeded

### 3. Invalid Input

**Error:** `ValueError: Question cannot be empty`

**Cause:** Empty or whitespace-only question provided.

**Solution:** Validate input before calling `answer()`:
```python
question = user_input.strip()
if not question:
    print("Please enter a question")
else:
    result = runtime.answer(question)
```

### 4. File System Errors

**Error:** `FileOperationError: Permission denied`

**Cause:** Insufficient permissions to read/write strategy files.

**Solution:** Ensure the process has read/write access to `strategies_dir` and `datasets_dir`.

## Logging

### Configuration

Set log level in `config.yaml`:
```yaml
log_level: INFO
log_file: logs/agent.log  # Optional
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages (default)
- **WARNING**: Warning messages for recoverable issues
- **ERROR**: Error messages for failures

### Example Log Output

```
2026-04-22 15:30:45 [INFO] src.agent.runtime: Answering question: What is Docker?...
2026-04-22 15:30:46 [INFO] src.agent.providers.claude: Calling Claude API: model=claude-sonnet-4-6
2026-04-22 15:30:47 [INFO] src.agent.providers.claude: Claude response: 245 chars
2026-04-22 15:30:47 [INFO] src.agent.runtime: Generated answer (version=v001, length=245)
```

## Retry Logic

The `ClaudeProvider` automatically retries failed API calls:
- **Max attempts:** 3
- **Backoff:** Exponential (2s, 4s, 8s)
- **Retryable errors:** Rate limits, connection errors, API status errors

## Best Practices

1. **Always catch specific exceptions** rather than bare `except:`
2. **Log errors with context** (version IDs, file paths, etc.)
3. **Validate inputs** before processing
4. **Use try-except-finally** for cleanup operations
5. **Chain exceptions** with `from e` to preserve stack traces

## Troubleshooting

### Tests Failing

Run with verbose output:
```bash
pytest -v --tb=short
```

### Coverage Below Threshold

Check which files need tests:
```bash
pytest --cov=src --cov-report=term-missing
```

### CI Pipeline Failing

Run local CI checks:
```bash
ruff check src/ tests/
mypy src/
pytest --cov=src --cov-fail-under=80
```

