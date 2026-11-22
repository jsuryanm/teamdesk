from sqlalchemy import Boolean, Enum, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin
from backend.app.models.enums import Role


def enum_column(enum_cls: type, name: str) -> Enum:
    """Store enums as VARCHAR + CHECK constraint (not a native PG ENUM).

    Native enums are painful to change in migrations; VARCHAR+CHECK is easy to evolve.
    `values_callable` stores 'admin' (the value), not 'ADMIN' (the member name).
    """
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        length=20,
        create_constraint=True,
        values_callable=lambda e: [m.value for m in e],
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)  # UNIQUE also creates an index
    full_name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(
        enum_column(Role, "role"), default=Role.REQUESTER, server_default=Role.REQUESTER.value
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email} {self.role}>"
