import enum
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text


class Base(DeclarativeBase):
    pass


class Status(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Doctor(Base):
    __tablename__ = "doctors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    specialty: Mapped[str] = mapped_column(String(50), nullable=False)

    appointments: Mapped[List["AppointmentRegister"]] = relationship(back_populates="doctor")

class AppointmentRegister(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_name: Mapped[str] = mapped_column(String(100), nullable=False)
    appointment_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[Status] = mapped_column(SQLEnum(Status), default=Status.SCHEDULED)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.id"), nullable=False)
    doctor: Mapped["Doctor"] = relationship(back_populates="appointments")
