import uuid
from datetime import datetime, date, time
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    VARCHAR,
)
from sqlalchemy.orm import relationship

from open_webui.internal.db import Base, get_db


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Search(Base):
    """Stores search parameters for each flight search query"""
    __tablename__ = "searches"

    search_id = Column(Integer, primary_key=True, autoincrement=True)
    auto_search_airline_id = Column(Integer, ForeignKey("auto_search_airline.auto_search_airline_id", ondelete="SET NULL"), nullable=True, index=True)
    engine = Column(String, nullable=False)
    departure_id = Column(String, nullable=False)
    arrival_id = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    hl = Column(String, nullable=True)
    gl = Column(String, nullable=True)
    outbound_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)
    flight_type = Column(String, nullable=False)
    travel_class = Column(String, nullable=False)
    stops = Column(String, nullable=True)
    adults = Column(Integer, default=1)
    children = Column(Integer, default=0)
    infants_in_seat = Column(Integer, default=0)
    infants_on_lap = Column(Integer, default=0)
    included_airlines = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    auto_search_airline = relationship("AutoSearchAirline", foreign_keys=[auto_search_airline_id], back_populates="searches")
    flight_options = relationship("FlightOption", back_populates="search", cascade="all, delete-orphan")
    price_insight = relationship("PriceInsight", back_populates="search", uselist=False, cascade="all, delete-orphan")
    search_airports = relationship("SearchAirport", back_populates="search", cascade="all, delete-orphan")


class FlightOption(Base):
    """Stores flight options (both best_flights and other_flights)"""
    __tablename__ = "flight_options"

    option_id = Column(Integer, primary_key=True, autoincrement=True)
    search_id = Column(Integer, ForeignKey("searches.search_id", ondelete="CASCADE"), nullable=False, index=True)
    is_best_flight = Column(Boolean, nullable=False, default=False)
    total_duration = Column(Integer, nullable=True)
    price = Column(Integer, nullable=False)
    type = Column(String, nullable=True)
    airline_logo = Column(String, nullable=True)
    departure_token = Column(String, nullable=True)
    carbon_emission_this_flight = Column(Integer, nullable=True)
    carbon_emission_typical = Column(Integer, nullable=True)
    carbon_emission_difference_percent = Column(Float, nullable=True)
    carbon_emission_lowest_route = Column(Integer, nullable=True)

    # Relationships
    search = relationship("Search", back_populates="flight_options")
    flight_segments = relationship("FlightSegment", back_populates="flight_option", cascade="all, delete-orphan", order_by="FlightSegment.segment_order")
    layovers = relationship("Layover", back_populates="flight_option", cascade="all, delete-orphan", order_by="Layover.layover_order")
    option_extensions = relationship("OptionExtension", back_populates="flight_option", cascade="all, delete-orphan")


class FlightSegment(Base):
    """Stores individual flight segments within a flight option"""
    __tablename__ = "flight_segments"

    segment_id = Column(Integer, primary_key=True, autoincrement=True)
    option_id = Column(Integer, ForeignKey("flight_options.option_id", ondelete="CASCADE"), nullable=False, index=True)
    segment_order = Column(Integer, nullable=False)
    departure_airport_iata = Column(VARCHAR, ForeignKey("airport_auto.iata", ondelete="RESTRICT"), nullable=False)
    departure_airport_name = Column(Text, nullable=False)
    departure_date = Column(Date, nullable=False)
    departure_time = Column(Time, nullable=False)
    arrival_airport_iata = Column(VARCHAR, ForeignKey("airport_auto.iata", ondelete="RESTRICT"), nullable=False)
    arrival_airport_name = Column(Text, nullable=False)
    arrival_date = Column(Date, nullable=False)
    arrival_time = Column(Time, nullable=False)
    duration = Column(Integer, nullable=False)
    airplane = Column(String, nullable=True)
    airline_id = Column(VARCHAR, ForeignKey("airline_auto.airline_id", ondelete="SET NULL"), nullable=True)
    airline = Column(String, nullable=True)
    airline_logo = Column(String, nullable=True)
    travel_class = Column(String, nullable=True)
    flight_number = Column(String, nullable=False)
    is_overnight = Column(Boolean, default=False)
    # Detected extensions fields
    has_in_seat_usb_outlet = Column(Boolean, nullable=True)
    has_power_and_usb_outlets = Column(Boolean, nullable=True)
    has_on_demand_video = Column(Boolean, nullable=True)
    wifi = Column(String, nullable=True)
    seat_type = Column(String, nullable=True)
    legroom_short = Column(String, nullable=True)
    legroom_long = Column(String, nullable=True)
    carbon_emission = Column(Float, nullable=True)

    # Relationships
    flight_option = relationship("FlightOption", back_populates="flight_segments")
    flight_extensions = relationship("FlightExtension", back_populates="flight_segment", cascade="all, delete-orphan")
    departure_airport = relationship("AirportAuto", foreign_keys=[departure_airport_iata], back_populates="departure_segments")
    arrival_airport = relationship("AirportAuto", foreign_keys=[arrival_airport_iata], back_populates="arrival_segments")
    airline_ref = relationship("AirlineAuto", foreign_keys=[airline_id])


class FlightExtension(Base):
    """Stores extension strings for flight segments (many-to-many relationship)"""
    __tablename__ = "flight_extensions"

    extension_id = Column(Integer, primary_key=True, autoincrement=True)
    segment_id = Column(Integer, ForeignKey("flight_segments.segment_id", ondelete="CASCADE"), nullable=False, index=True)
    extension_text = Column(Text, nullable=False)

    # Relationships
    flight_segment = relationship("FlightSegment", back_populates="flight_extensions")


class OptionExtension(Base):
    """Stores extension strings for flight options"""
    __tablename__ = "option_extensions"

    extension_id = Column(Integer, primary_key=True, autoincrement=True)
    option_id = Column(Integer, ForeignKey("flight_options.option_id", ondelete="CASCADE"), nullable=False, index=True)
    extension_text = Column(Text, nullable=False)

    # Relationships
    flight_option = relationship("FlightOption", back_populates="option_extensions")


class Layover(Base):
    """Stores layover information for multi-segment flights"""
    __tablename__ = "layovers"

    layover_id = Column(Integer, primary_key=True, autoincrement=True)
    option_id = Column(Integer, ForeignKey("flight_options.option_id", ondelete="CASCADE"), nullable=False, index=True)
    layover_order = Column(Integer, nullable=False)
    airport_iata = Column(VARCHAR, ForeignKey("airport_auto.iata", ondelete="RESTRICT"), nullable=False)
    airport_name = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)

    # Relationships
    flight_option = relationship("FlightOption", back_populates="layovers")
    airport = relationship("AirportAuto", foreign_keys=[airport_iata], back_populates="layovers")


class PriceInsight(Base):
    """Stores price insights for each search"""
    __tablename__ = "price_insights"

    insight_id = Column(Integer, primary_key=True, autoincrement=True)
    search_id = Column(Integer, ForeignKey("searches.search_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    lowest_price = Column(Integer, nullable=True)
    price_level = Column(String, nullable=True)
    typical_low_price = Column(Integer, nullable=True)
    typical_high_price = Column(Integer, nullable=True)

    # Relationships
    search = relationship("Search", back_populates="price_insight")
    price_history = relationship("PriceHistory", back_populates="price_insight", cascade="all, delete-orphan")


class PriceHistory(Base):
    """Stores historical price data for searches"""
    __tablename__ = "price_history"

    history_id = Column(Integer, primary_key=True, autoincrement=True)
    insight_id = Column(Integer, ForeignKey("price_insights.insight_id", ondelete="CASCADE"), nullable=False, index=True)
    price = Column(Integer, nullable=False)
    iso_date = Column(DateTime, nullable=False, index=True)

    # Relationships
    price_insight = relationship("PriceInsight", back_populates="price_history")


class AirlineAuto(Base):
    """Stores airline information from flight search data"""
    __tablename__ = "airline_auto"

    airline_id = Column(VARCHAR, primary_key=True)
    code = Column(VARCHAR(10), nullable=True, index=True)
    name = Column(Text, nullable=False)
    airline_logo = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    flight_segments = relationship("FlightSegment", foreign_keys="FlightSegment.airline_id", back_populates="airline_ref")


class AirportAuto(Base):
    """Stores airport information from flight search data"""
    __tablename__ = "airport_auto"

    airport_id = Column(VARCHAR, primary_key=True)
    iata = Column(VARCHAR, nullable=False, unique=True, index=True)
    airport_name = Column(Text, nullable=False)
    city = Column(String, nullable=True)
    country = Column(String, nullable=True)
    country_code = Column(VARCHAR(2), nullable=True)
    image_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    departure_segments = relationship("FlightSegment", foreign_keys="FlightSegment.departure_airport_iata", back_populates="departure_airport")
    arrival_segments = relationship("FlightSegment", foreign_keys="FlightSegment.arrival_airport_iata", back_populates="arrival_airport")
    layovers = relationship("Layover", foreign_keys="Layover.airport_iata", back_populates="airport")
    search_airports = relationship("SearchAirport", foreign_keys="SearchAirport.airport_iata", back_populates="airport")


class SearchAirport(Base):
    """Links searches to airports (for departure/arrival airport info)"""
    __tablename__ = "search_airports"

    search_airport_id = Column(Integer, primary_key=True, autoincrement=True)
    search_id = Column(Integer, ForeignKey("searches.search_id", ondelete="CASCADE"), nullable=False, index=True)
    airport_iata = Column(VARCHAR, ForeignKey("airport_auto.iata", ondelete="RESTRICT"), nullable=False, index=True)
    is_departure = Column(Boolean, nullable=False)

    # Relationships
    search = relationship("Search", back_populates="search_airports")
    airport = relationship("AirportAuto", foreign_keys=[airport_iata], back_populates="search_airports")


# Pydantic Models for API responses

class SearchModel(BaseModel):
    search_id: Optional[int] = None
    engine: str
    departure_id: str
    arrival_id: str
    currency: str
    hl: Optional[str] = None
    gl: Optional[str] = None
    outbound_date: date
    return_date: Optional[date] = None
    flight_type: str
    travel_class: str
    stops: Optional[str] = None
    adults: int = 1
    children: int = 0
    infants_in_seat: int = 0
    infants_on_lap: int = 0
    included_airlines: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class FlightOptionModel(BaseModel):
    option_id: Optional[int] = None
    search_id: int
    is_best_flight: bool = False
    total_duration: Optional[int] = None
    price: int
    type: Optional[str] = None
    airline_logo: Optional[str] = None
    departure_token: Optional[str] = None
    carbon_emission_this_flight: Optional[int] = None
    carbon_emission_typical: Optional[int] = None
    carbon_emission_difference_percent: Optional[float] = None
    carbon_emission_lowest_route: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class FlightSegmentModel(BaseModel):
    segment_id: Optional[int] = None
    option_id: int
    segment_order: int
    departure_airport_iata: str
    departure_airport_name: str
    departure_date: date
    departure_time: time
    arrival_airport_iata: str
    arrival_airport_name: str
    arrival_date: date
    arrival_time: time
    duration: int
    airplane: Optional[str] = None
    airline_id: Optional[str] = None
    airline: Optional[str] = None
    airline_logo: Optional[str] = None
    travel_class: Optional[str] = None
    flight_number: str
    is_overnight: bool = False
    has_in_seat_usb_outlet: Optional[bool] = None
    has_power_and_usb_outlets: Optional[bool] = None
    has_on_demand_video: Optional[bool] = None
    wifi: Optional[str] = None
    seat_type: Optional[str] = None
    legroom_short: Optional[str] = None
    legroom_long: Optional[str] = None
    carbon_emission: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class FlightExtensionModel(BaseModel):
    extension_id: Optional[int] = None
    segment_id: int
    extension_text: str

    model_config = ConfigDict(from_attributes=True)


class OptionExtensionModel(BaseModel):
    extension_id: Optional[int] = None
    option_id: int
    extension_text: str

    model_config = ConfigDict(from_attributes=True)


class LayoverModel(BaseModel):
    layover_id: Optional[int] = None
    option_id: int
    layover_order: int
    airport_iata: str
    airport_name: str
    duration: int

    model_config = ConfigDict(from_attributes=True)


class PriceInsightModel(BaseModel):
    insight_id: Optional[int] = None
    search_id: int
    lowest_price: Optional[int] = None
    price_level: Optional[str] = None
    typical_low_price: Optional[int] = None
    typical_high_price: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PriceHistoryModel(BaseModel):
    history_id: Optional[int] = None
    insight_id: int
    price: int
    iso_date: datetime

    model_config = ConfigDict(from_attributes=True)


class AirlineAutoModel(BaseModel):
    airline_id: str
    code: Optional[str] = None
    name: str
    airline_logo: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class AirportAutoModel(BaseModel):
    airport_id: str
    iata: str
    airport_name: str
    city: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class SearchAirportModel(BaseModel):
    search_airport_id: Optional[int] = None
    search_id: int
    airport_iata: str
    is_departure: bool

    model_config = ConfigDict(from_attributes=True)

