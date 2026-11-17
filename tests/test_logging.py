import io
import logging

from app.core.logging import get_logger


def test_get_logger_returns_logger_with_name():
    logger = get_logger("app.test.logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "app.test.logger"


def test_get_logger_respects_log_level_env(monkeypatch):
    import app.core.logging as core_logging

    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    core_logging._configured = False
    logger = get_logger("app.test.level")
    assert logger.level == logging.DEBUG
    assert logging.getLogger().level == logging.DEBUG

    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    core_logging._configured = False
    logger = get_logger("app.test.level2")
    assert logger.level == logging.WARNING


def test_get_logger_default_level_info(monkeypatch):
    import app.core.logging as core_logging

    monkeypatch.delenv("LOG_LEVEL", raising=False)
    core_logging._configured = False
    logger = get_logger("app.test.default")
    assert logger.level == logging.INFO


def test_logging_output(monkeypatch):
    import app.core.logging as core_logging

    monkeypatch.setenv("LOG_LEVEL", "INFO")
    core_logging._configured = False
    logger = get_logger("app.test.output")

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(handler)
    try:
        logger.info("hello %s", "world")
    finally:
        logger.removeHandler(handler)

    output = stream.getvalue()
    assert "hello world" in output
    assert "app.test.output" in output
    assert "INFO" in output
