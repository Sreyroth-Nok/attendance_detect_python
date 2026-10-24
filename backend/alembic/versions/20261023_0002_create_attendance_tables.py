"""create subjects, class_sessions and attendance_records tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_subjects"),
        sa.UniqueConstraint("code", name="uq_subjects_code"),
        sa.CheckConstraint("char_length(btrim(code)) > 0", name=op.f("ck_subjects_code_not_blank")),
    )
    op.create_table(
        "class_sessions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("subject_id", sa.BigInteger(), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("session_number", sa.SmallInteger(), nullable=False),
        sa.Column("week", sa.SmallInteger(), nullable=True),
        sa.Column("room", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_class_sessions"),
        sa.ForeignKeyConstraint(
            ["subject_id"], ["subjects.id"], name="fk_class_sessions_subject_id_subjects", ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "subject_id", "session_date", "session_number", name="uq_class_sessions_subject_date_number"
        ),
        sa.CheckConstraint(
            "session_number BETWEEN 1 AND 4", name=op.f("ck_class_sessions_session_number_valid")
        ),
        sa.CheckConstraint("week IS NULL OR week > 0", name=op.f("ck_class_sessions_week_positive")),
    )
    op.create_table(
        "attendance_records",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("class_session_id", sa.BigInteger(), nullable=False),
        sa.Column("student_id", sa.BigInteger(), nullable=False),
        sa.Column("is_present", sa.Boolean(), nullable=False),
        sa.Column("raw_mark", sa.String(length=10), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_attendance_records"),
        sa.ForeignKeyConstraint(
            ["class_session_id"], ["class_sessions.id"],
            name="fk_attendance_records_class_session_id_class_sessions", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"],
            name="fk_attendance_records_student_id_students", ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("class_session_id", "student_id", name="uq_attendance_records_session_student"),
    )
    op.create_index("ix_attendance_records_student_id", "attendance_records", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_attendance_records_student_id", table_name="attendance_records")
    op.drop_table("attendance_records")
    op.drop_table("class_sessions")
    op.drop_table("subjects")
