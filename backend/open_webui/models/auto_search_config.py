import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from open_webui.internal.db import Base, get_db


def generate_uuid() -> str:
    return str(uuid.uuid4())


class AutoSearchConfig(Base):
    """Stores auto search configuration (departure, destination, travel class, etc.)"""
    __tablename__ = "auto_search_config"

    auto_search_id = Column(Integer, primary_key=True, autoincrement=True)
    departure_id = Column(String, nullable=False)  # Airport code
    arrival_id = Column(String, nullable=False)  # Airport code
    travel_class = Column(Integer, nullable=False, default=0)  # 0=economy, 1=premium_economy, 2=business, 3=first
    is_direct = Column(Boolean, nullable=False, default=False)
    return_trip_duration = Column(Integer, nullable=False, default=7)  # Days
    n8n_status = Column(String, nullable=False, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    airlines = relationship("AutoSearchAirline", back_populates="auto_search", cascade="all, delete-orphan")


class AutoSearchAirline(Base):
    """Junction table linking auto_search_config to airline (many-to-many)"""
    __tablename__ = "auto_search_airline"
    __table_args__ = (
        UniqueConstraint("auto_search_id", "airline_id", name="uq_auto_search_airline"),
    )

    auto_search_airline_id = Column(Integer, primary_key=True, autoincrement=True)
    auto_search_id = Column(Integer, ForeignKey("auto_search_config.auto_search_id", ondelete="CASCADE"), nullable=False, index=True)
    airline_id = Column(String, ForeignKey("airline.airline_id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    auto_search = relationship("AutoSearchConfig", back_populates="airlines")
    airline = relationship("Airline", foreign_keys=[airline_id])
    searches = relationship("Search", back_populates="auto_search_airline", cascade="all, delete-orphan")


# Pydantic Models for API responses

class AutoSearchConfigModel(BaseModel):
    auto_search_id: Optional[int] = None
    departure_id: str
    arrival_id: str
    travel_class: int = 0
    is_direct: bool = False
    return_trip_duration: int = 7
    n8n_status: str = "pending"  # pending, processing, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class AutoSearchAirlineModel(BaseModel):
    auto_search_airline_id: Optional[int] = None
    auto_search_id: int
    airline_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)

