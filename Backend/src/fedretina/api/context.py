"""Request-scoped context.

Contextvars are populated by:
    - RequestIDMiddleware   → request_id
    - get_current_user      → actor_id, actor_email, hospital_node
    - RequestIDMiddleware   → client_ip, http_method, http_path

The logger reads from these in its filter. This is how every log line gets
actor attribution without passing Context around manually.
"""

from __future__ import annotations

from contextvars import ContextVar

# ---------------------------------------------------------------------------
# Context variables
# ---------------------------------------------------------------------------
_actor_id: ContextVar[str | None] = ContextVar("actor_id", default=None)
_actor_email: ContextVar[str | None] = ContextVar("actor_email", default=None)
_hospital_node: ContextVar[str | None] = ContextVar("hospital_node", default=None)


# ---------------------------------------------------------------------------
# Readers — used by the logging filter
# ---------------------------------------------------------------------------
def get_actor_id() -> str | None:
    return _actor_id.get()


def get_actor_email() -> str | None:
    return _actor_email.get()


def get_hospital_node() -> str | None:
    return _hospital_node.get()


# ---------------------------------------------------------------------------
# Writer — used by the auth dependency
# ---------------------------------------------------------------------------
def bind_request_context(
    *,
    actor_id: str | None = None,
    actor_email: str | None = None,
    hospital_node: str | None = None,
) -> None:
    """Bind actor identity to the current request context.

    Called once per request by get_current_user, after successful auth.
    Middleware resets these at request boundaries.
    """
    if actor_id is not None:
        _actor_id.set(actor_id)
    if actor_email is not None:
        _actor_email.set(actor_email)
    if hospital_node is not None:
        _hospital_node.set(hospital_node)


def clear_request_context() -> None:
    """Reset all context variables. Called by middleware on request exit."""
    _actor_id.set(None)
    _actor_email.set(None)
    _hospital_node.set(None)