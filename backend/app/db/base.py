"""in base.py we define all the database models (Python class) that map directly to the tables in RDBMS"""

from datetime import datetime 
from sqlalchemy import DateTime, MetaData, func
# 
# MetaData stores the definitions of tables, columns, data types and constraints 
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column 
# DeclarativeBase is the parent class that translates python classes to db tables
# Mapped tells what kind of data a db columns holds when you define your db tables as Python classes.
# mapped_column defines a db column inside a Python class

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {datetime: DateTime(timezone=True)}

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())