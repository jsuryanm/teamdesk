"""Enums shared by the database models AND the Pydantic schemas (single source of truth)."""

import enum


class Role(enum.StrEnum):
    ADMIN = "admin"
    AGENT = "agent"
    REQUESTER = "requester"


class TicketStatus(enum.StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
