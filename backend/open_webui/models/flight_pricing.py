import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    Column,
    DateTime,
    String,
    Text,
)

from open_webui.internal.db import Base, get_db


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Airport(Base):
    __tablename__ = "airport"

    airport_id = Column(String, primary_key=True, default=generate_uuid)
    iata = Column(String, nullable=False)
    airport_name = Column(Text, nullable=False)
    place_name = Column(Text, nullable=False)
    display_name = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Airline(Base):
    __tablename__ = "airline"

    airline_id = Column(String, primary_key=True, default=generate_uuid)
    code = Column(String(10), nullable=True)
    name = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AirportModel(BaseModel):
    airport_id: str = Field(default_factory=generate_uuid)
    iata: str
    airport_name: str
    place_name: str
    display_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class AirlineModel(BaseModel):
    airline_id: str = Field(default_factory=generate_uuid)
    code: Optional[str] = None
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)




class AirlinesTable:
    def _normalize_name(self, name: str) -> str:
        return name.strip()

    def _normalize_code(self, code: Optional[str]) -> Optional[str]:
        return code.strip().upper() if code else None

    def create(self, name: str, code: Optional[str] = None) -> AirlineModel:
        with get_db() as db:
            record = Airline(
                name=self._normalize_name(name),
                code=self._normalize_code(code),
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return AirlineModel.model_validate(record)

    def get(self, airline_id: str) -> Optional[AirlineModel]:
        with get_db() as db:
            record = db.query(Airline).filter_by(airline_id=airline_id).first()
            return AirlineModel.model_validate(record) if record else None

    def get_by_name(self, name: str) -> Optional[AirlineModel]:
        normalized = self._normalize_name(name)
        with get_db() as db:
            record = db.query(Airline).filter(Airline.name == normalized).first()
            return AirlineModel.model_validate(record) if record else None

    def get_by_code(self, code: str) -> Optional[AirlineModel]:
        normalized = self._normalize_code(code)
        if not normalized:
            return None
        with get_db() as db:
            record = db.query(Airline).filter(Airline.code == normalized).first()
            return AirlineModel.model_validate(record) if record else None

    def get_or_create(self, name: str, code: Optional[str] = None) -> AirlineModel:
        existing = None
        if code:
            existing = self.get_by_code(code)
        if not existing:
            existing = self.get_by_name(name)
        if existing:
            return existing
        return self.create(name, code)

    def get_or_create_by_code(
        self, code: str, fallback_name: Optional[str] = None
    ) -> AirlineModel:
        normalized_code = self._normalize_code(code)
        existing = self.get_by_code(normalized_code)
        if existing:
            return existing
        name = fallback_name.strip() if fallback_name else normalized_code
        return self.create(name=name, code=normalized_code)

    def list(self) -> List[AirlineModel]:
        with get_db() as db:
            records = db.query(Airline).order_by(Airline.name.asc()).all()
            return [AirlineModel.model_validate(record) for record in records]

    def update(
        self, airline_id: str, name: Optional[str] = None, code: Optional[str] = None
    ) -> Optional[AirlineModel]:
        with get_db() as db:
            record = db.query(Airline).filter_by(airline_id=airline_id).first()
            if not record:
                return None
            if name is not None:
                record.name = self._normalize_name(name)
            if code is not None:
                record.code = self._normalize_code(code)
            db.commit()
            db.refresh(record)
            return AirlineModel.model_validate(record)

    def delete(self, airline_id: str) -> bool:
        with get_db() as db:
            result = db.query(Airline).filter_by(airline_id=airline_id).delete()
            db.commit()
            return result > 0

