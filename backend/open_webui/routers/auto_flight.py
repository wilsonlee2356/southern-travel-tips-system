import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

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
    PriceModel,
    PricesTable,
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
TRAVEL_CLASS_LABELS = {
    0: "economy",
    1: "premium_economy",
    2: "business",
    3: "first",
}


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
    prices: List[PriceModel] = Field(default_factory=list)
    message: str = "Auto flight search initiated."


def _build_date_range() -> tuple[str, str]:
    tomorrow = datetime.utcnow().date() + timedelta(days=1)
    six_months_later = tomorrow + timedelta(days=SIX_MONTHS_IN_DAYS)
    start = tomorrow.strftime("%Y-%m-%d")
    end = six_months_later.strftime("%Y-%m-%d")
    return start, end


def _parse_calendar_date(value: str) -> datetime | None:
    if not value:
        return None
    candidate = str(value)[:10]
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        try:
            parsed = datetime.strptime(candidate, "%Y-%m-%d")
        except ValueError:
            return None
    return parsed.replace(hour=0, minute=0, second=0, microsecond=0)


def _normalize_price(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(round(value))
    if isinstance(value, str):
        cleaned = re.sub(r"[^\d.]", "", value)
        if not cleaned:
            return None
        try:
            return int(round(float(cleaned)))
        except ValueError:
            return None
    if isinstance(value, dict):
        for key in ("raw", "value", "amount", "price"):
            if key in value:
                normalized = _normalize_price(value[key])
                if normalized is not None:
                    return normalized
    return None


DATE_KEY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _extract_calendar_prices(data: dict | None) -> List[Tuple[datetime, int]]:
    if not isinstance(data, dict):
        return []
    calendar = data.get("calendar")
    if calendar is None:
        return []

    entries: List[dict] = []
    stack = [calendar]
    direct_entries: List[Tuple[datetime, int]] = []
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            # handle dicts keyed by date strings (e.g. {"2025-01-01": {"price": {...}}})
            for key, value in current.items():
                if isinstance(key, str) and DATE_KEY_PATTERN.match(key):
                    parsed_date = _parse_calendar_date(key)
                    if not parsed_date:
                        continue
                    price_source = value
                    if isinstance(value, dict):
                        price_source = (
                            value.get("price")
                            or value.get("lowest_price")
                            or value.get("min_price")
                            or value.get("amount")
                            or value
                        )
                    price_int = _normalize_price(price_source)
                    if price_int is not None:
                        direct_entries.append((parsed_date, price_int))
                # continue traversing nested structures for additional price info
                if isinstance(value, (list, dict)):
                    stack.append(value)

            has_date = any(
                key in current
                for key in (
                    "date",
                    "departure_date",
                    "outbound_date",
                    "departure",
                    "day",
                )
            )
            has_price = any(
                key in current
                for key in ("price", "lowest_price", "min_price", "amount")
            )
            if has_date and has_price:
                entries.append(current)
        elif isinstance(current, list):
            stack.extend(current)

    results: List[Tuple[datetime, int]] = list(direct_entries)
    for entry in entries:
        date_value = (
            entry.get("date")
            or entry.get("departure_date")
            or entry.get("outbound_date")
            or entry.get("departure")
            or entry.get("day")
        )
        parsed_date = _parse_calendar_date(date_value)
        if not parsed_date:
            continue

        price_value = (
            entry.get("price")
            or entry.get("lowest_price")
            or entry.get("min_price")
            or entry.get("amount")
        )
        price_int = _normalize_price(price_value)
        if price_int is None:
            continue

        results.append((parsed_date, price_int))

    return results


def _aggregate_calendar_prices(
    entries: List[Tuple[datetime, int]]
) -> List[Tuple[datetime, int, bool]]:
    if not entries:
        return []

    aggregated: dict[datetime, int] = {}
    for date_value, price in entries:
        if date_value not in aggregated or price < aggregated[date_value]:
            aggregated[date_value] = price

    if not aggregated:
        return []

    lowest_price = min(aggregated.values())
    ordered = sorted(aggregated.items(), key=lambda item: item[0])
    return [
        (date_value, price, price == lowest_price) for date_value, price in ordered
    ]


def _summarize_calendar_payload(payload: dict | None, limit: int = 3) -> dict:
    if not isinstance(payload, dict):
        return {"type": type(payload).__name__}

    calendar = payload.get("calendar")
    summary: dict[str, Any] = {
        "calendar_type": type(calendar).__name__,
        "calendar_len": len(calendar) if isinstance(calendar, list) else None,
    }

    samples: list[dict[str, Any]] = []
    if isinstance(calendar, list):
        for entry in calendar[:limit]:
            if isinstance(entry, dict):
                sample: dict[str, Any] = {"keys": list(entry.keys())}
                for key in ("date", "departure_date", "outbound_date"):
                    if key in entry:
                        sample[key] = entry[key]
                price_field = (
                    entry.get("price")
                    or entry.get("lowest_price")
                    or entry.get("min_price")
                    or entry.get("amount")
                )
                if price_field is not None:
                    sample["price"] = price_field
                samples.append(sample)
            else:
                samples.append({"type": type(entry).__name__})
    summary["samples"] = samples
    return summary


def _collect_calendar_prices_for_airlines(
    route: FlightRouteModel,
    return_route: FlightRouteModel,
    airline_codes: List[str],
    travel_class: int,
    direct_flight: bool,
) -> Dict[str, List[Tuple[datetime, int, bool]]]:
    outbound_start, outbound_end = _build_date_range()
    travel_class_label = TRAVEL_CLASS_LABELS.get(travel_class)
    raw_entries_per_airline: Dict[str, List[Tuple[datetime, int]]] = defaultdict(list)

    for code in airline_codes:
        airline_code = code.strip().upper()
        if not airline_code:
            continue

        try:
            log.debug(
                "Fetching outbound calendar for airline %s: %s -> %s",
                airline_code,
                route.from_place,
                route.to_place,
            )
            outbound_payload = fetch_calendar(
                departure_id=route.from_place,
                arrival_id=route.to_place,
                outbound_date=outbound_start,
                outbound_date_start=outbound_start,
                outbound_date_end=outbound_end,
                flight_type="one_way",
                travel_class=travel_class_label,
                non_stop=direct_flight,
                airline=airline_code,
            )
            log.info(
                "Outbound calendar summary for %s (%s -> %s): %s",
                airline_code,
                route.from_place,
                route.to_place,
                _summarize_calendar_payload(outbound_payload),
            )
            raw_entries_per_airline[airline_code].extend(
                _extract_calendar_prices(outbound_payload)
            )
        except FlightCalendarError as exc:
            log.warning(
                "Outbound calendar fetch failed for airline %s: %s",
                airline_code,
                exc,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            log.exception(
                "Unexpected outbound calendar error for airline %s: %s",
                airline_code,
                exc,
            )

        try:
            log.debug(
                "Fetching inbound calendar for airline %s: %s -> %s",
                airline_code,
                return_route.from_place,
                return_route.to_place,
            )
            inbound_payload = fetch_calendar(
                departure_id=return_route.from_place,
                arrival_id=return_route.to_place,
                outbound_date=outbound_start,
                outbound_date_start=outbound_start,
                outbound_date_end=outbound_end,
                flight_type="one_way",
                travel_class=travel_class_label,
                non_stop=direct_flight,
                airline=airline_code,
            )
            log.info(
                "Inbound calendar summary for %s (%s -> %s): %s",
                airline_code,
                return_route.from_place,
                return_route.to_place,
                _summarize_calendar_payload(inbound_payload),
            )
            raw_entries_per_airline[airline_code].extend(
                _extract_calendar_prices(inbound_payload)
            )
        except FlightCalendarError as exc:
            log.warning(
                "Inbound calendar fetch failed for airline %s: %s",
                airline_code,
                exc,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            log.exception(
                "Unexpected inbound calendar error for airline %s: %s",
                airline_code,
                exc,
            )

    aggregated: Dict[str, List[Tuple[datetime, int, bool]]] = {}
    for airline_code, entries in raw_entries_per_airline.items():
        aggregated_entries = _aggregate_calendar_prices(entries)
        if aggregated_entries:
            aggregated[airline_code] = aggregated_entries

    return aggregated


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
    prices_table = PricesTable()

    airline_codes: List[str] = []
    for item in payload.airlines:
        normalized = item.strip()
        if not normalized:
            continue
        upper = normalized.upper()
        by_code = airlines_table.get_by_code(upper)
        if by_code:
            airline_codes.append(by_code.code)
            continue
        by_name = airlines_table.get_by_name(normalized)
        if by_name and by_name.code:
            airline_codes.append(by_name.code)
            continue
        if len(upper) in (2, 3):
            airline_codes.append(upper)
            continue
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unrecognized airline identifier: {normalized}",
        )

    if len(airline_codes) < MIN_AIRLINES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provide at least {MIN_AIRLINES} airline codes.",
        )

    airline_codes = list(dict.fromkeys(airline_codes))

    (
        auto_search_model,
        route,
        return_route,
        airline_models,
        auto_search_airline_models,
    ) = auto_search_table.create_configuration(
        departure_code=payload.from_place,
        destination_code=payload.to_place,
        travel_class=payload.travel_class,
        direct_flight=payload.direct_flight,
        airline_codes=airline_codes,
    )

    aggregated_price_map = _collect_calendar_prices_for_airlines(
        route=route,
        return_route=return_route,
        airline_codes=airline_codes,
        travel_class=payload.travel_class,
        direct_flight=payload.direct_flight,
    )

    price_models: List[PriceModel] = []
    if aggregated_price_map:
        prices_table.delete_for_auto_search(auto_search_model.auto_search_id)

        airline_by_id = {airline.airline_id: airline for airline in airline_models}
        link_by_code: Dict[str, AutoSearchAirlineModel] = {}
        for link in auto_search_airline_models:
            airline = airline_by_id.get(link.airline_id)
            if airline and airline.code:
                link_by_code[airline.code.upper()] = link

        total_inserted = 0
        for code, entries in aggregated_price_map.items():
            link = link_by_code.get(code.upper())
            if not link:
                log.warning(
                    "Skipping price entries for airline code %s; no matching auto_search_airline link",
                    code,
                )
                continue
            inserted = prices_table.bulk_insert(link.auto_search_airline_id, entries)
            price_models.extend(inserted)
            total_inserted += len(inserted)

        if total_inserted:
            log.info(
                "Stored %d price points across %d airlines for auto_search %s",
                total_inserted,
                len(aggregated_price_map),
                auto_search_model.auto_search_id,
            )
        else:
            log.warning(
                "No price entries inserted for auto_search %s after aggregation.",
                auto_search_model.auto_search_id,
            )
    else:
        log.warning(
            "No price entries aggregated for auto_search %s. Calendar responses may be empty.",
            auto_search_model.auto_search_id,
        )

    outbound_start, outbound_end = _build_date_range()

    response_payload = AutoFlightSearchResponse(
        route=route,
        return_route=return_route,
        airlines=airline_models,
        auto_search=auto_search_model,
        auto_search_airlines=auto_search_airline_models,
        travel_class=payload.travel_class,
        direct_flight=payload.direct_flight,
        outbound_departure=outbound_start,
        outbound_end=outbound_end,
        inbound_departure=outbound_start,
        inbound_end=outbound_end,
        prices=sorted(price_models, key=lambda price: price.departure_date),
    )

    log.debug(
        "Auto flight search response for user %s: %s",
        user.id,
        response_payload.model_dump(),
    )

    return response_payload


@router.post(
    "/auto-search/{auto_search_id}/refresh",
    response_model=AutoFlightSearchResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh_auto_flight_search(
    auto_search_id: str, user=Depends(get_verified_user)
):
    auto_search_table = AutoSearchTable()
    routes_table = FlightRoutesTable()
    airlines_table = AirlinesTable()
    auto_search_airlines_table = AutoSearchAirlinesTable()
    prices_table = PricesTable()

    auto_search_model = auto_search_table.get(auto_search_id)
    if not auto_search_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auto search {auto_search_id} not found.",
        )

    route = routes_table.get(auto_search_model.departure_route_id)
    if not route:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Departure route is missing for this auto search.",
        )

    return_route: FlightRouteModel | None = None
    if auto_search_model.return_route_id:
        return_route = routes_table.get(auto_search_model.return_route_id)
    if not return_route:
        return_route = routes_table.get_or_create(route.to_place, route.from_place)

    auto_search_airline_models = auto_search_airlines_table.list_for_auto_search(
        auto_search_id
    )
    if not auto_search_airline_models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This auto search does not have any airlines configured.",
        )

    airline_models: List[AirlineModel] = []
    airline_codes: List[str] = []
    missing_codes: List[str] = []

    for link in auto_search_airline_models:
        airline = airlines_table.get(link.airline_id)
        if not airline:
            log.warning(
                "Auto search %s references missing airline %s",
                auto_search_id,
                link.airline_id,
            )
            continue
        airline_models.append(airline)
        if airline.code:
            airline_codes.append(airline.code)
        else:
            missing_codes.append(airline.airline_id)

    if missing_codes:
        log.warning(
            "Auto search %s has airlines without codes and will be skipped: %s",
            auto_search_id,
            missing_codes,
        )

    if len(airline_codes) < MIN_AIRLINES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"At least {MIN_AIRLINES} airlines with codes are required to refresh.",
        )

    aggregated_price_map = _collect_calendar_prices_for_airlines(
        route=route,
        return_route=return_route,
        airline_codes=airline_codes,
        travel_class=auto_search_model.travel_class,
        direct_flight=auto_search_model.direct_flight,
    )

    prices_table.delete_for_auto_search(auto_search_model.auto_search_id)

    price_models: List[PriceModel] = []
    if aggregated_price_map:
        airline_by_id = {airline.airline_id: airline for airline in airline_models}
        link_by_code: Dict[str, AutoSearchAirlineModel] = {}
        for link in auto_search_airline_models:
            airline = airline_by_id.get(link.airline_id)
            if airline and airline.code:
                link_by_code[airline.code.upper()] = link

        total_inserted = 0
        for code, entries in aggregated_price_map.items():
            link = link_by_code.get(code.upper())
            if not link:
                log.warning(
                    "Skipping price entries for airline code %s; no matching auto_search_airline link",
                    code,
                )
                continue
            inserted = prices_table.bulk_insert(link.auto_search_airline_id, entries)
            price_models.extend(inserted)
            total_inserted += len(inserted)

        if total_inserted:
            log.info(
                "Refreshed %d price points across %d airlines for auto_search %s",
                total_inserted,
                len(aggregated_price_map),
                auto_search_model.auto_search_id,
            )
        else:
            log.warning(
                "No price entries inserted for auto_search %s during refresh.",
                auto_search_model.auto_search_id,
            )
    else:
        log.warning(
            "No price entries aggregated for auto_search %s during refresh.",
            auto_search_model.auto_search_id,
        )

    outbound_start, outbound_end = _build_date_range()

    response_payload = AutoFlightSearchResponse(
        route=route,
        return_route=return_route,
        airlines=airline_models,
        auto_search=auto_search_model,
        auto_search_airlines=auto_search_airline_models,
        travel_class=auto_search_model.travel_class,
        direct_flight=auto_search_model.direct_flight,
        outbound_departure=outbound_start,
        outbound_end=outbound_end,
        inbound_departure=outbound_start,
        inbound_end=outbound_end,
        prices=sorted(price_models, key=lambda price: price.departure_date),
        message="Auto flight search refreshed.",
    )

    log.debug(
        "Auto flight search refresh response for user %s: %s",
        user.id,
        response_payload.model_dump(),
    )

    return response_payload

