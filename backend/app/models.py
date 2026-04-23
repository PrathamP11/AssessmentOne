from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class InteractionRecord(Base):
    __tablename__ = "interaction_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hcp_name: Mapped[str] = mapped_column(String(255), index=True)
    interaction_type: Mapped[str] = mapped_column(String(100), default="Meeting")
    interaction_date: Mapped[str] = mapped_column(String(20))
    interaction_time: Mapped[str] = mapped_column(String(20))
    attendees: Mapped[str] = mapped_column(Text, default="")
    topics_discussed: Mapped[str] = mapped_column(Text, default="")
    materials_shared: Mapped[str] = mapped_column(Text, default="")
    sentiment: Mapped[str] = mapped_column(String(20), default="neutral")
    outcomes: Mapped[str] = mapped_column(Text, default="")
    follow_up_actions: Mapped[str] = mapped_column(Text, default="")
    ai_suggested_follow_ups: Mapped[str] = mapped_column(Text, default="")
    compliance_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    samples: Mapped[list["SampleDistribution"]] = relationship(
        back_populates="interaction",
        cascade="all, delete-orphan",
    )


class SampleDistribution(Base):
    __tablename__ = "sample_distributions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interaction_id: Mapped[int] = mapped_column(ForeignKey("interaction_records.id"))
    sample_name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[str] = mapped_column(String(50), default="1 unit")

    interaction: Mapped[InteractionRecord] = relationship(back_populates="samples")
