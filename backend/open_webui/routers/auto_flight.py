import logging
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.flight_pricing import (
    AirlinesTable,
    AirlineModel,
    AutoSearchAirlineModel,
    AutoSearchAirlinesTable,
    AutoSearchModel,
    AutoSearchTable,
    FlightRouteModel,
    FlightRoutesTable,
)
from open_webui.utils.auth import get_verified_user
from open_webui.utils.flight_calendar import fetch_calendar, FlightCalendarError

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()

MIN_AIRLINES = 10
SIX_MONTHS_IN_DAYS = 180


class AutoFlightSearchRequest(BaseModel):
    from_place: str = Field(..., min_length=3, max_length=10, description="Origin airport code")
    to_place: str = Field(..., min_length=3, max_length=10, description="Destination airport code")
    airlines: List[str] = Field(..., description="Airline names to track (must include at least 10)")
    travel_class: int = Field(0, ge=0, le=3, description="0=economy, 1=premium_economy, 2=business, 3=first_class")
    direct_flight: bool = Field(False, description="Track direct flights only")

    @validator("airlines")
    def validate_airlines(cls, value: List[str]) -> List[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        unique = list(dict.fromkeys(cleaned))
        if len(unique) < MIN_AIRLINES:
            raise ValueError(f"Provide at least {MIN_AIRLINES} unique airline names.")
        return unique


class AutoFlightSearchResponse(BaseModel):
    route: FlightRouteModel
    return_route: FlightRouteModel
    airlines: List[AirlineModel]
    auto_search: AutoSearchModel
    auto_search_airlines: List[AutoSearchAirlineModel]
    travel_class: int
    direct_flight: bool
    outbound_departure: str
    outbound_end: str
    inbound_departure: str
    inbound_end: str
    message: str = "Auto flight search initiated."


class AutoSearchSetupRequest(BaseModel):
    departure: str = Field(..., min_length=3, max_length=10, description="Origin airport code")
    destination: str = Field(..., min_length=3, max_length=10, description="Destination airport code")
    travel_class: int = Field(..., ge=0, le=3, description="0=economy, 1=premium_economy, 2=business, 3=first_class")
    airline_codes: List[str] = Field(..., min_items=10, max_items=10, description="Exactly 10 airline codes")
    direct_flight: bool = Field(False, description="Track direct flights only")

    @validator("airline_codes")
    def validate_airline_codes(cls, value: List[str]) -> List[str]:
        cleaned = [item.strip().upper() for item in value if item and item.strip()]
        if len(cleaned) != 10:
            raise ValueError("Provide exactly 10 airline codes.")
        if len(set(cleaned)) != 10:
            raise ValueError("Airline codes must be unique.")
        return cleaned


class AutoSearchSetupResponse(BaseModel):
    route: FlightRouteModel
    return_route: FlightRouteModel
    auto_search: AutoSearchModel
    airlines: List[AirlineModel]
    auto_search_airlines: List[AutoSearchAirlineModel]
    travel_class: int
    direct_flight: bool
    message: str = "Auto search configuration saved."


def _build_date_range() -> tuple[str, str]:
    tomorrow = datetime.utcnow().date() + timedelta(days=1)
    six_months_later = tomorrow + timedelta(days=SIX_MONTHS_IN_DAYS)
    start = tomorrow.strftime("%Y-%m-%d")
    end = six_months_later.strftime("%Y-%m-%d")
    return start, end


@router.get(
    "/airlines",
    response_model=List[AirlineModel],
    summary="List all airlines",
)
async def list_airlines(user=Depends(get_verified_user)):
    table = AirlinesTable()
    airlines = table.list()
    log.debug("Fetched %d airlines for user %s", len(airlines), user.id)
    return airlines


@router.post(
    "/auto-search",
    response_model=AutoFlightSearchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_auto_flight_search(
    payload: AutoFlightSearchRequest, user=Depends(get_verified_user)
):
    routes_table = FlightRoutesTable()
    airlines_table = AirlinesTable()
    auto_search_table = AutoSearchTable()
    auto_search_airlines_table = AutoSearchAirlinesTable()

    route = routes_table.get_or_create(payload.from_place, payload.to_place)
    return_route = routes_table.get_or_create(payload.to_place, payload.from_place)
    airline_models = [airlines_table.get_or_create(name) for name in payload.airlines]
    auto_search_model = auto_search_table.get_or_create(
        departure_route_id=route.route_id,
        travel_class=payload.travel_class,
        direct_flight=payload.direct_flight,
        return_route_id=return_route.route_id,
    )
    auto_search_airline_models = [
        auto_search_airlines_table.get_or_create(
            auto_search_id=auto_search_model.auto_search_id,
            airline_id=airline.airline_id,
        )
        for airline in airline_models
    ]

    from_code = route.from_place
    to_code = route.to_place

    outbound_start, outbound_end = _build_date_range()
    inbound_start, inbound_end = outbound_start, outbound_end

    try:
        outbound_data = fetch_calendar(
            departure_id=from_code,
            arrival_id=to_code,
            outbound_date=outbound_start,
            outbound_date_start=outbound_start,
            outbound_date_end=outbound_end,
            flight_type="one_way",
        )
        inbound_data = fetch_calendar(
            departure_id=to_code,
            arrival_id=from_code,
            outbound_date=inbound_start,
            outbound_date_start=inbound_start,
            outbound_date_end=inbound_end,
            flight_type="one_way",
        )
    except FlightCalendarError as exc:
        log.error("Flight calendar request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch calendar data from SearchAPI.",
        ) from exc

    log.info(
        "Auto flight search outbound %s -> %s: %s entries",
        payload.from_place,
        payload.to_place,
        len(outbound_data.get("calendar", [])),
    )
    log.debug("Outbound calendar raw data: %s", outbound_data)

    log.info(
        "Auto flight search inbound %s -> %s: %s entries",
        payload.to_place,
        payload.from_place,
        len(inbound_data.get("calendar", [])),
    )
    log.debug("Inbound calendar raw data: %s", inbound_data)

    return AutoFlightSearchResponse(
        route=route,
        return_route=return_route,
        airlines=airline_models,
        auto_search=auto_search_model,
        auto_search_airlines=auto_search_airline_models,
        travel_class=payload.travel_class,
        direct_flight=payload.direct_flight,
        outbound_departure=outbound_start,
        outbound_end=outbound_end,
        inbound_departure=inbound_start,
        inbound_end=inbound_end,
    )


@router.post(
    "/auto-search/setup",
    response_model=AutoSearchSetupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def setup_auto_search(
    payload: AutoSearchSetupRequest, user=Depends(get_verified_user)
):
    auto_search_table = AutoSearchTable()

    (
        auto_search,
        route,
        return_route,
        airline_models,
        auto_search_airline_models,
    ) = auto_search_table.create_configuration(
        departure_code=payload.departure,
        destination_code=payload.destination,
        travel_class=payload.travel_class,
        direct_flight=payload.direct_flight,
        airline_codes=payload.airline_codes,
    )

    log.info(
        "Auto search configured by %s: %s -> %s with %d airlines",
        user.id,
        payload.departure,
        payload.destination,
        len(auto_search_airline_models),
    )

    return AutoSearchSetupResponse(
        route=route,
        return_route=return_route,
        auto_search=auto_search,
        airlines=airline_models,
        auto_search_airlines=auto_search_airline_models,
        travel_class=payload.travel_class,
        direct_flight=payload.direct_flight,
    )

