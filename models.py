from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

class Founder(Base):
    __tablename__ = "founders"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    company: Mapped[str | None] = mapped_column(
       String(255),
       nullable=True,
    )

    role: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    profile_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    source_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    evidence: Mapped[str | None] = mapped_column(
        Text,
        nullable=False,
    )

    review_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=False,
        default="needs_review",
    )


    outreach_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="not_contacted",
    )

    outreach_draft: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
