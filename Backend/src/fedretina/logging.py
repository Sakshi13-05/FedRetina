"""Structured JSON logging configuration.

Every log record is emitted as a single-line JSON object with a consistent
schema. This makes logs queryable by any log aggregation system without
regex parsing.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from pythonjsonlogger.jsonlogger import JsonFormatter

from fedretina.config import get_settings


class _ContextFilter(logging.Filter):
    """Injects request-scoped context into every log record.

    Context is populated by middleware (request_id) and API dependencies
    (actor_id, actor_email, hospital_node). Missing fields default to None.
    """

    _CONTEXT_KEYS = (
        "request_id",
        "actor_id",
        "actor_email",
        "hospital_node",
        "client_ip",
        "http_method",
        "http_path",
        "http_status",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        from fedretina.api.context import (
            get_actor_email,
            get_actor_id,
            get_hospital_node,
        )
        from fedretina.middleware.request_id import get_request_id

        if not hasattr(record, "request_id"):
            record.request_id = get_request_id()  # type: ignore[attr-defined]
        if not hasattr(record, "actor_id"):
            record.actor_id = get_actor_id()  # type: ignore[attr-defined]
        if not hasattr(record, "actor_email"):
            record.actor_email = get_actor_email()  # type: ignore[attr-defined]
        if not hasattr(record, "hospital_node"):
            record.hospital_node = get_hospital_node()  # type: ignore[attr-defined]

        for key in ("client_ip", "http_method", "http_path", "http_status"):
            if not hasattr(record, key):
                setattr(record, key, None)
        return True


class _OrjsonFormatter(JsonFormatter):
    """JSON formatter that emits keys in a stable order."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        # Rename standard fields for consistency
        log_record["timestamp"] = log_record.pop("asctime", None)
        log_record["level"] = log_record.pop("levelname", None)
        log_record["logger"] = log_record.pop("name", None)
        log_record["message"] = log_record.pop("message", None)
        # Drop uninteresting stdlib fields
        for noisy in ("exc_info", "stack_info", "taskName"):
            log_record.pop(noisy, None)


def configure_logging() -> None:
    """Idempotently configure the root logger.

    Called once at process startup (in the FastAPI lifespan).
    """
    settings = get_settings()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        _OrjsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
            timestamp=True,
        ),
    )
    handler.addFilter(_ContextFilter())

    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(settings.log_level)

    for noisy in ("uvicorn.access", "httpx", "httpcore", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger. Prefer this over ``logging.getLogger``."""
    return logging.getLogger(f"fedretina.{name}")