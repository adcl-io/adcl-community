# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Structured logging for ADCL backend.

Provides JSON-formatted logging for easy parsing and analysis.
Follows ADCL principle: Structured output for machine readability.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Optional, Any
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs log records as JSON for easy parsing by log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName",
                "relativeCreated", "thread", "threadName", "exc_info",
                "exc_text", "stack_info"
            ]:
                log_data[key] = value

        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Simple text formatter for human-readable logs."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def get_logger(
    name: str,
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[Path] = None
) -> logging.Logger:
    """
    Get configured logger instance.

    Args:
        name: Logger name (usually __name__)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type (json or text)
        log_file: Optional log file path

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Choose formatter
    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def log_event(
    logger: logging.Logger,
    event: str,
    level: str = "INFO",
    **kwargs: Any
) -> None:
    """
    Log structured event with additional fields.

    Args:
        logger: Logger instance
        event: Event name
        level: Log level
        **kwargs: Additional fields to include in log
    """
    log_func = getattr(logger, level.lower())
    log_func(event, extra=kwargs)


# Pre-configured loggers
def get_api_logger() -> logging.Logger:
    """Get logger for API routes."""
    from app.core.config import settings
    return get_logger(
        "adcl.api",
        log_level=settings.log_level,
        log_format=settings.log_format
    )


def get_service_logger(service_name: str) -> logging.Logger:
    """Get logger for service layer."""
    from app.core.config import settings
    return get_logger(
        f"adcl.service.{service_name}",
        log_level=settings.log_level,
        log_format=settings.log_format
    )


def get_audit_logger() -> logging.Logger:
    """
    Get logger for audit trail.

    Audit logs go to separate file for compliance.
    """
    from app.core.config import settings
    from datetime import date

    log_file = settings.logs_dir / f"audit-{date.today().isoformat()}.log"
    return get_logger(
        "adcl.audit",
        log_level="INFO",
        log_format="json",
        log_file=log_file
    )
