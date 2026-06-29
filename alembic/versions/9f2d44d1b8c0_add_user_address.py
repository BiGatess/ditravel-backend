"""Add user address

Revision ID: 9f2d44d1b8c0
Revises: 771b9d69d705
Create Date: 2026-06-29 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "9f2d44d1b8c0"
down_revision: Union[str, Sequence[str], None] = "771b9d69d705"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("users")}
    if "address" not in columns:
        op.add_column("users", sa.Column("address", sa.String(length=255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("users")}
    if "address" in columns:
        op.drop_column("users", "address")
