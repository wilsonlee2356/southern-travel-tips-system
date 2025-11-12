import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from open_webui.internal.db import Base, get_db


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Airline(Base):
    __tablename__ = "airline"

    airline_id = Column(String, primary_key=True, default=generate_uuid)
    code = Column(String(10), nullable=True)
    name = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    auto_searches = relationship(
        "AutoSearch", back_populates="airline", cascade="all, delete-orphan"
    )


class FlightRoute(Base):
    __tablename__ = "flight_route"

    route_id = Column(String, primary_key=True, default=generate_uuid)
    from_place = Column(String(10), nullable=False)
    to_place = Column(String(10), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    auto_searches = relationship(
        "AutoSearch", back_populates="route", cascade="all, delete-orphan"
    )


class AutoSearch(Base):
    __tablename__ = "auto_search"

    auto_search_id = Column(String, primary_key=True, default=generate_uuid)
    route_id = Column(
        String, ForeignKey("flight_route.route_id"), nullable=False, index=True
    )
    airline_id = Column(
        String, ForeignKey("airline.airline_id"), nullable=False, index=True
    )
    travel_class = Column(Integer, nullable=False, default=0)
    direct_flight = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    route = relationship("FlightRoute", back_populates="auto_searches")
    airline = relationship("Airline", back_populates="auto_searches")
    prices = relationship("Price", back_populates="auto_search", cascade="all, delete-orphan")


class Price(Base):
    __tablename__ = "price"

    price_id = Column(String, primary_key=True, default=generate_uuid)
    auto_search_id = Column(
        String, ForeignKey("auto_search.auto_search_id"), nullable=False, index=True
    )
    departure_date = Column(DateTime, nullable=False)
    price = Column(Integer, nullable=False)
    is_lowest_price = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    auto_search = relationship("AutoSearch", back_populates="prices")

    @property
    def route(self):
        return self.auto_search.route if self.auto_search else None

    @property
    def airline(self):
        return self.auto_search.airline if self.auto_search else None


class AirlineModel(BaseModel):
    airline_id: str = Field(default_factory=generate_uuid)
    code: Optional[str] = None
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class FlightRouteModel(BaseModel):
    route_id: str = Field(default_factory=generate_uuid)
    from_place: str
    to_place: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class PriceModel(BaseModel):
    price_id: str = Field(default_factory=generate_uuid)
    auto_search_id: str
    departure_date: datetime
    price: int
    is_lowest_price: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class AutoSearchModel(BaseModel):
    auto_search_id: str = Field(default_factory=generate_uuid)
    route_id: str
    airline_id: str
    travel_class: int = 0
    direct_flight: bool = False
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


class FlightRoutesTable:
    def _normalize_code(self, value: str) -> str:
        return value.strip().upper()

    def create(self, from_place: str, to_place: str) -> FlightRouteModel:
        with get_db() as db:
            record = FlightRoute(
                from_place=self._normalize_code(from_place),
                to_place=self._normalize_code(to_place),
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return FlightRouteModel.model_validate(record)

    def get(self, route_id: str) -> Optional[FlightRouteModel]:
        with get_db() as db:
            record = db.query(FlightRoute).filter_by(route_id=route_id).first()
            return FlightRouteModel.model_validate(record) if record else None

    def get_by_places(self, from_place: str, to_place: str) -> Optional[FlightRouteModel]:
        with get_db() as db:
            record = (
                db.query(FlightRoute)
                .filter(
                    FlightRoute.from_place == self._normalize_code(from_place),
                    FlightRoute.to_place == self._normalize_code(to_place),
                )
                .first()
            )
            return FlightRouteModel.model_validate(record) if record else None

    def get_or_create(self, from_place: str, to_place: str) -> FlightRouteModel:
        existing = self.get_by_places(from_place, to_place)
        if existing:
            return existing
        return self.create(from_place, to_place)

    def list(self) -> List[FlightRouteModel]:
        with get_db() as db:
            records = db.query(FlightRoute).order_by(FlightRoute.created_at.desc()).all()
            return [FlightRouteModel.model_validate(record) for record in records]

    def update(self, route_id: str, from_place: str, to_place: str) -> Optional[FlightRouteModel]:
        with get_db() as db:
            record = db.query(FlightRoute).filter_by(route_id=route_id).first()
            if not record:
                return None
            record.from_place = from_place
            record.to_place = to_place
            db.commit()
            db.refresh(record)
            return FlightRouteModel.model_validate(record)

    def delete(self, route_id: str) -> bool:
        with get_db() as db:
            result = db.query(FlightRoute).filter_by(route_id=route_id).delete()
            db.commit()
            return result > 0


class PricesTable:
    def create(
        self,
        auto_search_id: str,
        departure_date: datetime,
        price: int,
        is_lowest_price: bool = False,
    ) -> PriceModel:
        with get_db() as db:
            record = Price(
                auto_search_id=auto_search_id,
                departure_date=departure_date,
                price=price,
                is_lowest_price=is_lowest_price,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return PriceModel.model_validate(record)

    def get(self, price_id: str) -> Optional[PriceModel]:
        with get_db() as db:
            record = db.query(Price).filter_by(price_id=price_id).first()
            return PriceModel.model_validate(record) if record else None

    def list_by_auto_search(self, auto_search_id: str) -> List[PriceModel]:
        with get_db() as db:
            records = (
                db.query(Price)
                .filter_by(auto_search_id=auto_search_id)
                .order_by(Price.departure_date.asc())
                .all()
            )
            return [PriceModel.model_validate(record) for record in records]

    def update(
        self,
        price_id: str,
        *,
        price: Optional[int] = None,
        is_lowest_price: Optional[bool] = None,
    ) -> Optional[PriceModel]:
        with get_db() as db:
            record = db.query(Price).filter_by(price_id=price_id).first()
            if not record:
                return None
            if price is not None:
                record.price = price
            if is_lowest_price is not None:
                record.is_lowest_price = is_lowest_price
            db.commit()
            db.refresh(record)
            return PriceModel.model_validate(record)

    def delete(self, price_id: str) -> bool:
        with get_db() as db:
            result = db.query(Price).filter_by(price_id=price_id).delete()
            db.commit()
            return result > 0


class AutoSearchTable:
    def get(self, auto_search_id: str) -> Optional[AutoSearchModel]:
        with get_db() as db:
            record = (
                db.query(AutoSearch).filter_by(auto_search_id=auto_search_id).first()
            )
            return AutoSearchModel.model_validate(record) if record else None

    def get_by_route_and_airline(
        self, route_id: str, airline_id: str, travel_class: int, direct_flight: bool
    ) -> Optional[AutoSearchModel]:
        with get_db() as db:
            record = (
                db.query(AutoSearch)
                .filter(
                    AutoSearch.route_id == route_id,
                    AutoSearch.airline_id == airline_id,
                    AutoSearch.travel_class == travel_class,
                    AutoSearch.direct_flight == direct_flight,
                )
                .first()
            )
            return AutoSearchModel.model_validate(record) if record else None

    def create(
        self, route_id: str, airline_id: str, travel_class: int, direct_flight: bool
    ) -> AutoSearchModel:
        with get_db() as db:
            record = AutoSearch(
                route_id=route_id,
                airline_id=airline_id,
                travel_class=travel_class,
                direct_flight=direct_flight,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return AutoSearchModel.model_validate(record)

    def get_or_create(
        self, route_id: str, airline_id: str, travel_class: int, direct_flight: bool
    ) -> AutoSearchModel:
        existing = self.get_by_route_and_airline(
            route_id, airline_id, travel_class, direct_flight
        )
        if existing:
            return existing
        return self.create(route_id, airline_id, travel_class, direct_flight)

    def list_by_route(self, route_id: str) -> List[AutoSearchModel]:
        with get_db() as db:
            records = (
                db.query(AutoSearch)
                .filter_by(route_id=route_id)
                .order_by(AutoSearch.created_at.asc())
                .all()
            )
            return [AutoSearchModel.model_validate(record) for record in records]

    def delete(self, auto_search_id: str) -> bool:
        with get_db() as db:
            result = (
                db.query(AutoSearch).filter_by(auto_search_id=auto_search_id).delete()
            )
            db.commit()
            return result > 0

