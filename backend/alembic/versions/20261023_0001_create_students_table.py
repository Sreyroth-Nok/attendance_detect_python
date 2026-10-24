"""create students table

Revision ID: 0001
Revises:
Create Date: 2026-10-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("student_id", sa.String(length=20), nullable=False),
        sa.Column("full_name_khmer", sa.String(length=150), nullable=True),
        sa.Column("full_name_latin", sa.String(length=150), nullable=False),
        sa.Column("gender", sa.String(length=10), nullable=False),
        sa.Column("program", sa.String(length=100), nullable=True),
        sa.Column("major", sa.String(length=150), nullable=True),
        sa.Column("academic_year", sa.SmallInteger(), nullable=True),
        sa.Column("semester", sa.SmallInteger(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="Active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_students"),
        sa.UniqueConstraint("student_id", name="uq_students_student_id"),
        sa.CheckConstraint("gender IN ('Male', 'Female', 'Other')", name=op.f("ck_students_gender_valid")),
        sa.CheckConstraint("semester IS NULL OR semester IN (1, 2)", name=op.f("ck_students_semester_valid")),
        sa.CheckConstraint("status IN ('Active', 'Inactive')", name=op.f("ck_students_status_valid")),
        sa.CheckConstraint(
            "academic_year IS NULL OR academic_year > 0", name=op.f("ck_students_academic_year_positive")
        ),
        sa.CheckConstraint(
            "char_length(btrim(student_id)) > 0", name=op.f("ck_students_student_id_not_blank")
        ),
        sa.CheckConstraint(
            "char_length(btrim(full_name_latin)) > 0", name=op.f("ck_students_full_name_latin_not_blank")
        ),
    )
    op.create_index("ix_students_status", "students", ["status"])
    op.create_index("ix_students_major", "students", ["major"])
    op.create_index("ix_students_full_name_latin", "students", ["full_name_latin"])


def downgrade() -> None:
    op.drop_index("ix_students_full_name_latin", table_name="students")
    op.drop_index("ix_students_major", table_name="students")
    op.drop_index("ix_students_status", table_name="students")
    op.drop_table("students")
