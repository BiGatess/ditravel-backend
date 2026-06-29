"""Add user profile details

Revision ID: 2ad6f90d23b2
Revises: 9f2d44d1b8c0
Create Date: 2026-06-29 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "2ad6f90d23b2"
down_revision: Union[str, Sequence[str], None] = "9f2d44d1b8c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("users")}
    if "gender" not in columns:
        op.add_column("users", sa.Column("gender", sa.String(length=20), nullable=True))
    if "birth_date" not in columns:
        op.add_column("users", sa.Column("birth_date", sa.Date(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("users")}
    if "birth_date" in columns:
        op.drop_column("users", "birth_date")
    if "gender" in columns:
        op.drop_column("users", "gender")
