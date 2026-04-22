import logging
from pathlib import Path

from src.common.logger import setup_logger


def test_setup_logger_console_only() -> None:
    logger = setup_logger("test_logger", level="INFO")

    assert logger.name == "test_logger"
    assert logger.level == logging.INFO
    assert len(logger.handlers) >= 1
    assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)


def test_setup_logger_with_file(tmp_path: Path) -> None:
    log_file = tmp_path / "test.log"
    logger = setup_logger("test_logger_file", level="DEBUG", log_file=log_file)

    logger.info("Test message")

    assert log_file.exists()
    content = log_file.read_text()
    assert "Test message" in content
    assert "[INFO]" in content


def test_setup_logger_no_duplicate_handlers() -> None:
    logger1 = setup_logger("same_logger")
    logger2 = setup_logger("same_logger")

    # Should return same logger, not add duplicate handlers
    assert logger1 is logger2
    assert len(logger1.handlers) == len(logger2.handlers)
