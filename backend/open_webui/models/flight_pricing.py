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
    Text,
    UniqueConstraint,
    or_,
)
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

    auto_search_airlines = relationship(
        "AutoSearchAirline",
        back_populates="airline",
        cascade="all, delete-orphan",
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

    departure_auto_searches = relationship(
        "AutoSearch",
        foreign_keys="AutoSearch.departure_route_id",
        back_populates="departure_route",
        cascade="all, delete-orphan",
    )
    return_auto_searches = relationship(
        "AutoSearch",
        foreign_keys="AutoSearch.return_route_id",
        back_populates="return_route",
        cascade="all, delete-orphan",
    )


class AutoSearch(Base):
    __tablename__ = "auto_search"

    auto_search_id = Column(String, primary_key=True, default=generate_uuid)
    departure_route_id = Column(
        String, ForeignKey("flight_route.route_id"), nullable=False, index=True
    )
    return_route_id = Column(
        String, ForeignKey("flight_route.route_id"), nullable=True, index=True
    )
    travel_class = Column(Integer, nullable=False, default=0)
    direct_flight = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    departure_route = relationship(
        "FlightRoute",
        foreign_keys=[departure_route_id],
        back_populates="departure_auto_searches",
    )
    return_route = relationship(
        "FlightRoute",
        foreign_keys=[return_route_id],
        back_populates="return_auto_searches",
    )
    airlines = relationship(
        "AutoSearchAirline",
        back_populates="auto_search",
        cascade="all, delete-orphan",
    )


class AutoSearchAirline(Base):
    __tablename__ = "auto_search_airline"
    __table_args__ = (
        UniqueConstraint(
            "auto_search_id",
            "airline_id",
            "route_id",
            name="uq_auto_search_airline_triplet",
        ),
    )

    auto_search_airline_id = Column(
        String, primary_key=True, default=generate_uuid
    )
    auto_search_id = Column(
        String, ForeignKey("auto_search.auto_search_id"), nullable=False, index=True
    )
    airline_id = Column(
        String, ForeignKey("airline.airline_id"), nullable=False, index=True
    )
    route_id = Column(
        String, ForeignKey("flight_route.route_id"), nullable=False, index=True
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    auto_search = relationship("AutoSearch", back_populates="airlines")
    airline = relationship("Airline", back_populates="auto_search_airlines")
    route = relationship("FlightRoute")
    prices = relationship(
        "Price", back_populates="auto_search_airline", cascade="all, delete-orphan"
    )


class Price(Base):
    __tablename__ = "price"

    price_id = Column(String, primary_key=True, default=generate_uuid)
    auto_search_airline_id = Column(
        String,
        ForeignKey("auto_search_airline.auto_search_airline_id"),
        nullable=False,
        index=True,
    )
    departure_date = Column(DateTime, nullable=False)
    price = Column(Integer, nullable=False)
    is_lowest_price = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    auto_search_airline = relationship(
        "AutoSearchAirline", back_populates="prices", lazy="joined"
    )

    @property
    def auto_search(self):
        return self.auto_search_airline.auto_search if self.auto_search_airline else None

    @property
    def route(self):
        if not self.auto_search_airline:
            return None
        return self.auto_search_airline.route

    @property
    def airlines(self):
        if not self.auto_search_airline or not self.auto_search_airline.airline:
            return []
        return [self.auto_search_airline.airline]

    @property
    def airline(self):
        if not self.auto_search_airline:
            return None
        return self.auto_search_airline.airline

    @property
    def auto_search_id(self):
        auto_search = self.auto_search
        return auto_search.auto_search_id if auto_search else None


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
    auto_search_airline_id: str
    departure_date: datetime
    price: int
    is_lowest_price: bool = False
    auto_search_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class AutoSearchModel(BaseModel):
    auto_search_id: str = Field(default_factory=generate_uuid)
    departure_route_id: str
    return_route_id: Optional[str] = None
    travel_class: int = 0
    direct_flight: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class AutoSearchAirlineModel(BaseModel):
    auto_search_airline_id: str = Field(default_factory=generate_uuid)
    auto_search_id: str
    airline_id: str
    route_id: str
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
        auto_search_airline_id: str,
        departure_date: datetime,
        price: int,
        is_lowest_price: bool = False,
    ) -> PriceModel:
        with get_db() as db:
            record = Price(
                auto_search_airline_id=auto_search_airline_id,
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
                .join(
                    AutoSearchAirline,
                    Price.auto_search_airline_id
                    == AutoSearchAirline.auto_search_airline_id,
                )
                .filter(AutoSearchAirline.auto_search_id == auto_search_id)
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

    def delete_for_auto_search(self, auto_search_id: str) -> int:
        with get_db() as db:
            airline_rows = (
                db.query(AutoSearchAirline.auto_search_airline_id)
                .filter(AutoSearchAirline.auto_search_id == auto_search_id)
                .all()
            )
            airline_ids = [row.auto_search_airline_id for row in airline_rows]
            if not airline_ids:
                return 0
            result = (
                db.query(Price)
                .filter(Price.auto_search_airline_id.in_(airline_ids))
                .delete(synchronize_session=False)
            )
            db.commit()
            return result

    def bulk_insert(
        self,
        auto_search_airline_id: str,
        entries: List[tuple[datetime, int, bool]],
    ) -> List[PriceModel]:
        if not entries:
            return []
        with get_db() as db:
            records = []
            for departure_date, price, is_lowest in entries:
                record = Price(
                    auto_search_airline_id=auto_search_airline_id,
                    departure_date=departure_date,
                    price=price,
                    is_lowest_price=is_lowest,
                )
                db.add(record)
                records.append(record)
            db.commit()
            return [PriceModel.model_validate(record) for record in records]


class AutoSearchTable:
    def get(self, auto_search_id: str) -> Optional[AutoSearchModel]:
        with get_db() as db:
            record = (
                db.query(AutoSearch).filter_by(auto_search_id=auto_search_id).first()
            )
            return AutoSearchModel.model_validate(record) if record else None

    def get_existing(
        self,
        departure_route_id: str,
        travel_class: int,
        direct_flight: bool,
        return_route_id: Optional[str] = None,
    ) -> Optional[AutoSearchModel]:
        with get_db() as db:
            record = (
                db.query(AutoSearch)
                .filter(
                    AutoSearch.departure_route_id == departure_route_id,
                    AutoSearch.return_route_id == return_route_id,
                    AutoSearch.travel_class == travel_class,
                    AutoSearch.direct_flight == direct_flight,
                )
                .first()
            )
            return AutoSearchModel.model_validate(record) if record else None

    def create(
        self,
        departure_route_id: str,
        travel_class: int,
        direct_flight: bool,
        return_route_id: Optional[str] = None,
    ) -> AutoSearchModel:
        with get_db() as db:
            record = AutoSearch(
                departure_route_id=departure_route_id,
                return_route_id=return_route_id,
                travel_class=travel_class,
                direct_flight=direct_flight,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return AutoSearchModel.model_validate(record)

    def get_or_create(
        self,
        departure_route_id: str,
        travel_class: int,
        direct_flight: bool,
        return_route_id: Optional[str] = None,
    ) -> AutoSearchModel:
        existing = self.get_existing(
            departure_route_id, travel_class, direct_flight, return_route_id
        )
        if existing:
            return existing
        return self.create(
            departure_route_id, travel_class, direct_flight, return_route_id
        )

    def list_by_route(self, route_id: str) -> List[AutoSearchModel]:
        with get_db() as db:
            records = (
                db.query(AutoSearch)
                .filter(
                    or_(
                        AutoSearch.departure_route_id == route_id,
                        AutoSearch.return_route_id == route_id,
                    )
                )
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

    def create_configuration(
        self,
        departure_code: str,
        destination_code: str,
        travel_class: int,
        direct_flight: bool,
        airline_codes: List[str],
    ) -> tuple[
        AutoSearchModel,
        FlightRouteModel,
        FlightRouteModel,
        List[AirlineModel],
        List[AutoSearchAirlineModel],
    ]:
        routes_table = FlightRoutesTable()
        airlines_table = AirlinesTable()
        auto_search_airlines_table = AutoSearchAirlinesTable()

        departure_route = routes_table.get_or_create(departure_code, destination_code)
        return_route = routes_table.get_or_create(destination_code, departure_code)

        auto_search = self.create(
            departure_route_id=departure_route.route_id,
            travel_class=travel_class,
            direct_flight=direct_flight,
            return_route_id=return_route.route_id,
        )

        airline_models: List[AirlineModel] = []
        expected_pairs: set[tuple[str, str]] = set()

        for code in airline_codes:
            airline_model = airlines_table.get_or_create_by_code(code)
            airline_models.append(airline_model)

            departure_link = auto_search_airlines_table.get_or_create(
                auto_search_id=auto_search.auto_search_id,
                airline_id=airline_model.airline_id,
                route_id=departure_route.route_id,
            )
            expected_pairs.add((departure_link.airline_id, departure_link.route_id))

            if return_route and return_route.route_id:
                return_link = auto_search_airlines_table.get_or_create(
                    auto_search_id=auto_search.auto_search_id,
                    airline_id=airline_model.airline_id,
                    route_id=return_route.route_id,
                )
                expected_pairs.add((return_link.airline_id, return_link.route_id))

        # Remove any stale airline links not in current list/route combinations
        with get_db() as db:
            records = (
                db.query(AutoSearchAirline)
                .filter(AutoSearchAirline.auto_search_id == auto_search.auto_search_id)
                .all()
            )
            for record in records:
                key = (record.airline_id, record.route_id)
                if key not in expected_pairs:
                    db.delete(record)
            db.commit()

        auto_search_airline_models = auto_search_airlines_table.list_for_auto_search(
            auto_search.auto_search_id
        )

        return (
            auto_search,
            departure_route,
            return_route,
            airline_models,
            auto_search_airline_models,
        )

    def list_all(self) -> List[AutoSearchModel]:
        with get_db() as db:
            records = (
                db.query(AutoSearch)
                .order_by(AutoSearch.created_at.desc())
                .all()
            )
            return [AutoSearchModel.model_validate(record) for record in records]


class AutoSearchAirlinesTable:
    def create(self, auto_search_id: str, airline_id: str, route_id: str) -> AutoSearchAirlineModel:
        with get_db() as db:
            record = AutoSearchAirline(
                auto_search_id=auto_search_id,
                airline_id=airline_id,
                route_id=route_id,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return AutoSearchAirlineModel.model_validate(record)

    def get(self, auto_search_airline_id: str) -> Optional[AutoSearchAirlineModel]:
        with get_db() as db:
            record = (
                db.query(AutoSearchAirline)
                .filter_by(auto_search_airline_id=auto_search_airline_id)
                .first()
            )
            return AutoSearchAirlineModel.model_validate(record) if record else None

    def get_by_auto_search_and_airline(
        self, auto_search_id: str, airline_id: str, route_id: str
    ) -> Optional[AutoSearchAirlineModel]:
        with get_db() as db:
            record = (
                db.query(AutoSearchAirline)
                .filter_by(
                    auto_search_id=auto_search_id,
                    airline_id=airline_id,
                    route_id=route_id,
                )
                .first()
            )
            return AutoSearchAirlineModel.model_validate(record) if record else None

    def get_or_create(
        self, auto_search_id: str, airline_id: str, route_id: str
    ) -> AutoSearchAirlineModel:
        existing = self.get_by_auto_search_and_airline(
            auto_search_id, airline_id, route_id
        )
        if existing:
            return existing
        return self.create(auto_search_id, airline_id, route_id)

    def list_for_auto_search(self, auto_search_id: str) -> List[AutoSearchAirlineModel]:
        with get_db() as db:
            records = (
                db.query(AutoSearchAirline)
                .filter_by(auto_search_id=auto_search_id)
                .order_by(AutoSearchAirline.created_at.asc())
                .all()
            )
            return [AutoSearchAirlineModel.model_validate(record) for record in records]

    def delete(
        self, auto_search_id: str, airline_id: Optional[str] = None
    ) -> bool:
        with get_db() as db:
            query = db.query(AutoSearchAirline).filter_by(auto_search_id=auto_search_id)
            if airline_id is not None:
                query = query.filter_by(airline_id=airline_id)
            result = query.delete()
            db.commit()
            return result > 0

