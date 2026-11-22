from datetime import datetime

from sqlalchemy import Column, Computed, ForeignKey, Index, String, Table, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin
from backend.app.models.enums import TicketPriority, TicketStatus
from backend.app.models.user import User, enum_column

# Pure association table for the many-to-many Ticket <-> Tag relationship.
ticket_tags = Table(
    "ticket_tags",
    Base.metadata,
    Column("ticket_id", ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)

    tickets: Mapped[list["Ticket"]] = relationship(secondary=ticket_tags, back_populates="tags")


class Ticket(Base, TimestampMixin):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[TicketStatus] = mapped_column(
        enum_column(TicketStatus, "status"),
        default=TicketStatus.OPEN,
        server_default=TicketStatus.OPEN.value,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        enum_column(TicketPriority, "priority"),
        default=TicketPriority.MEDIUM,
        server_default=TicketPriority.MEDIUM.value,
    )
    # RESTRICT: you cannot delete a user who still has tickets. SET NULL: deleting an agent unassigns.
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    # Postgres *generated column*: the DB keeps this full-text vector in sync automatically.
    # deferred=True => it is NOT loaded with every ticket, only when we query it.
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', title || ' ' || description)", persisted=True),
        deferred=True,
    )

    requester: Mapped[User] = relationship(foreign_keys=[requester_id])
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id])
    tags: Mapped[list[Tag]] = relationship(
        secondary=ticket_tags, back_populates="tickets", lazy="selectin", order_by=Tag.name
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", order_by="Comment.id"
    )

    __table_args__ = (
        Index("ix_tickets_status_priority", "status", "priority"),  # composite index for dashboards
        Index("ix_tickets_search_vector", "search_vector", postgresql_using="gin"),  # fast full-text
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    ticket: Mapped[Ticket] = relationship(back_populates="comments")
    author: Mapped[User] = relationship()
