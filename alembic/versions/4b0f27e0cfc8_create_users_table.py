"""create users table

Revision ID: 4b0f27e0cfc8
Revises:
Create Date: 2026-04-01 04:25:28.308825

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b0f27e0cfc8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "users" not in inspector.get_table_names():
        op.create_table(
            "users",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("login", sa.String(), nullable=False),
            sa.Column("password", sa.String(), nullable=False),
            sa.Column("project_id", sa.Uuid(), nullable=False),
            sa.Column("env", sa.String(), nullable=False),
            sa.Column("domain", sa.String(), nullable=False),
            sa.Column("locktime", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("login"),
        )


def downgrade() -> None:
    op.drop_table("users")
