import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, time
from typing import Any, Dict, List, Optional, Tuple
import threading

from fastapi import APIRouter, Depends, HTTPException, Request, status
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

MIN_AIRLINES = 1
MAX_AIRLINES = 10
SIX_MONTHS_IN_DAYS = 180
TRAVEL_CLASS_LABELS = {
    0: "economy",
    1: "premium_economy",
    2: "business",
    3: "first",
}

# --- Auto search daily refresh scheduler (in‑process) ---

# Default daily refresh time (local server time)
_AUTO_SEARCH_REFRESH_TIME: time = time(hour=3, minute=0)
_refresh_scheduler_lock = threading.Lock()
_refresh_scheduler_timer: Optional[threading.Timer] = None


class AutoSearchScheduleModel(BaseModel):
    """Simple model to represent the daily auto-search refresh time (HH:MM, 24h)."""

    time: str = Field(
        ...,
        description="Daily refresh time in HH:MM 24-hour format, e.g. '03:00' or '18:30'",
        examples=["03:00", "18:30"],
    )


def _parse_time_string(value: str) -> time:
    """Parse 'HH:MM' into a time object, raising HTTPException on error."""
    try:
        parts = value.split(":", 1)
        if len(parts) != 2:
            raise ValueError
        hour = int(parts[0])
        minute = int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        return time(hour=hour, minute=minute)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Time must be in 'HH:MM' 24-hour format.",
        ) from exc


def _run_all_auto_search_refresh_sync() -> None:
    """
    Refresh all existing auto searches synchronously.

    This uses the same internal logic as the /auto-search/{id}/refresh endpoint,
    but runs without HTTP context so it can be called from a background timer.
    """
    auto_search_table = AutoSearchTable()
    searches = auto_search_table.list_all()
    if not searches:
        log.info("Scheduled auto-search refresh: no auto searches to refresh.")
        return

    log.info("Scheduled auto-search refresh started for %d auto searches", len(searches))

    for search in searches:
        try:
            # Reuse the same sync logic as the HTTP refresh endpoint
            _refresh_auto_flight_search_sync(search.auto_search_id)
        except Exception:  # pragma: no cover - defensive logging
            log.exception(
                "Scheduled auto-search refresh failed for auto_search_id=%s",
                search.auto_search_id,
            )

    log.info("Scheduled auto-search refresh completed.")


def _schedule_next_auto_search_refresh() -> None:
    """Schedule the next daily refresh based on _AUTO_SEARCH_REFRESH_TIME."""
    global _refresh_scheduler_timer
    with _refresh_scheduler_lock:
        if _refresh_scheduler_timer is not None:
            _refresh_scheduler_timer.cancel()

        now = datetime.now()
        target = datetime.combine(now.date(), _AUTO_SEARCH_REFRESH_TIME)
        if target <= now:
            target += timedelta(days=1)
        delay = (target - now).total_seconds()

        def _timer_callback() -> None:
            try:
                _run_all_auto_search_refresh_sync()
            finally:
                # Always schedule the next run
                _schedule_next_auto_search_refresh()

        _refresh_scheduler_timer = threading.Timer(delay, _timer_callback)
        _refresh_scheduler_timer.daemon = True
        _refresh_scheduler_timer.start()

        log.info(
            "Scheduled daily auto-search refresh at %s (in %.0f seconds)",
            _AUTO_SEARCH_REFRESH_TIME.strftime("%H:%M"),
            delay,
        )

# Start the scheduler with the default time when this module is first imported
try:  # pragma: no cover - defensive
    _schedule_next_auto_search_refresh()
except Exception:
    # If scheduling fails at import time, log but do not prevent app startup
    log.exception("Failed to start auto-search refresh scheduler on import")


class AutoFlightSearchRequest(BaseModel):
    from_place: str = Field(..., min_length=3, max_length=10, description="Origin airport code")
    to_place: str = Field(..., min_length=3, max_length=10, description="Destination airport code")
    airlines: List[str] = Field(..., description="Airline names to track (1-10 airlines)")
    travel_class: int = Field(0, ge=0, le=3, description="0=economy, 1=premium_economy, 2=business, 3=first_class")
    direct_flight: bool = Field(False, description="Track direct flights only")

    @validator("airlines")
    def validate_airlines(cls, value: List[str]) -> List[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        unique = list(dict.fromkeys(cleaned))
        if len(unique) < MIN_AIRLINES:
            raise ValueError(f"Provide at least {MIN_AIRLINES} unique airline names.")
        if len(unique) > MAX_AIRLINES:
            raise ValueError(f"Select no more than {MAX_AIRLINES} airlines.")
        return unique


class AirlinePriceDataPoint(BaseModel):
    departure_date: datetime
    price: int
    is_lowest_price: bool = False


class AirlinePriceSeries(BaseModel):
    airline_id: Optional[str] = None
    airline_code: Optional[str] = None
    airline_name: Optional[str] = None
    route_id: Optional[str] = None
    route_from: Optional[str] = None
    route_to: Optional[str] = None
    direction: Optional[str] = None
    prices: List[AirlinePriceDataPoint] = Field(default_factory=list)


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
    prices: List[AirlinePriceSeries] = Field(default_factory=list)
    message: str = "Auto flight search initiated."


class AutoFlightDeleteResponse(BaseModel):
    auto_search_id: str
    prices_deleted: int
    message: str = "Auto flight search deleted."


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
) -> Dict[Tuple[str, str], List[Tuple[datetime, int, bool]]]:
    outbound_start, outbound_end = _build_date_range()
    travel_class_label = TRAVEL_CLASS_LABELS.get(travel_class)
    raw_entries_per_pair: Dict[Tuple[str, str], List[Tuple[datetime, int]]] = defaultdict(list)

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
                included_airlines=airline_code,
            )
            log.info(
                "Outbound calendar summary for %s (%s -> %s): %s",
                airline_code,
                route.from_place,
                route.to_place,
                _summarize_calendar_payload(outbound_payload),
            )
            raw_entries_per_pair[(airline_code, route.route_id)].extend(
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
                included_airlines=airline_code,
            )
            log.info(
                "Inbound calendar summary for %s (%s -> %s): %s",
                airline_code,
                return_route.from_place,
                return_route.to_place,
                _summarize_calendar_payload(inbound_payload),
            )
            raw_entries_per_pair[(airline_code, return_route.route_id)].extend(
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

    aggregated: Dict[Tuple[str, str], List[Tuple[datetime, int, bool]]] = {}
    for key, entries in raw_entries_per_pair.items():
        aggregated_entries = _aggregate_calendar_prices(entries)
        if aggregated_entries:
            aggregated[key] = aggregated_entries

    return aggregated


def _compose_auto_search_response(
    *,
    auto_search: AutoSearchModel,
    route: FlightRouteModel | None,
    return_route: FlightRouteModel | None,
    airlines: List[AirlineModel],
    auto_search_airlines: List[AutoSearchAirlineModel],
    prices: List[PriceModel],
    travel_class: int,
    direct_flight: bool,
    message: str,
) -> AutoFlightSearchResponse:
    if route is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auto search is missing its departure route.",
        )

    if return_route is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auto search is missing its return route.",
        )

    outbound_start, outbound_end = _build_date_range()
    sorted_prices = sorted(prices, key=lambda price: price.departure_date)
    airline_series_map: Dict[str, AirlinePriceSeries] = {}

    airline_lookup: Dict[str, str] = {
        airline.airline_id: (airline.code or airline.airline_id)
        for airline in airlines
    }
    airline_name_lookup: Dict[str, str] = {
        airline.airline_id: airline.name or airline.code or airline.airline_id
        for airline in airlines
    }
    link_code_lookup: Dict[str, str] = {}
    link_name_lookup: Dict[str, str] = {}
    link_route_lookup: Dict[str, str] = {}
    link_by_id: Dict[str, AutoSearchAirlineModel] = {}
    for link in auto_search_airlines:
        airline_id = link.airline_id
        airline_code = airline_lookup.get(
            airline_id, airline_id or link.auto_search_airline_id
        )
        airline_name = airline_name_lookup.get(airline_id, airline_code)
        link_code_lookup[link.auto_search_airline_id] = airline_code
        link_name_lookup[link.auto_search_airline_id] = airline_name
        link_route_lookup[link.auto_search_airline_id] = link.route_id
        link_by_id[link.auto_search_airline_id] = link

    route_map: Dict[str, FlightRouteModel] = {}
    if route:
        route_map[route.route_id] = route
    if return_route:
        route_map[return_route.route_id] = return_route

    for price in sorted_prices:
        link = link_by_id.get(price.auto_search_airline_id)
        airline_id: Optional[str] = link.airline_id if link else None

        if link:
            airline_code = airline_lookup.get(airline_id, airline_id or "UNKNOWN")
            airline_name = airline_name_lookup.get(airline_id, airline_code)
        else:
            airline_code = link_code_lookup.get(price.auto_search_airline_id, "UNKNOWN")
            airline_name = link_name_lookup.get(price.auto_search_airline_id, airline_code)

        route_id = link_route_lookup.get(price.auto_search_airline_id)
        route_obj = route_map.get(route_id) if route_id else None

        key = (
            f"{airline_code or airline_id or price.auto_search_airline_id or 'UNKNOWN'}::{route_id or 'UNKNOWN'}"
        )
        direction = None
        if route_obj:
            if return_route and route_obj.route_id == return_route.route_id:
                direction = "return"
            elif route and route_obj.route_id == route.route_id:
                direction = "departure"

        series = airline_series_map.get(key)
        if not series:
            series = AirlinePriceSeries(
                airline_id=airline_id,
                airline_code=airline_code or key,
                airline_name=airline_name or airline_code or key,
                route_id=route_id,
                route_from=route_obj.from_place if route_obj else None,
                route_to=route_obj.to_place if route_obj else None,
                direction=direction,
                prices=[],
            )
            airline_series_map[key] = series
        else:
            if direction:
                series.direction = direction
            if route_obj and not series.route_from:
                series.route_from = route_obj.from_place
            if route_obj and not series.route_to:
                series.route_to = route_obj.to_place

        series.prices.append(
            AirlinePriceDataPoint(
                departure_date=price.departure_date,
                price=price.price,
                is_lowest_price=price.is_lowest_price,
            )
        )

    for series in airline_series_map.values():
        series.prices.sort(key=lambda item: item.departure_date)

    return AutoFlightSearchResponse(
        route=route,
        return_route=return_route,
        airlines=airlines,
        auto_search=auto_search,
        auto_search_airlines=auto_search_airlines,
        travel_class=travel_class,
        direct_flight=direct_flight,
        outbound_departure=outbound_start,
        outbound_end=outbound_end,
        inbound_departure=outbound_start,
        inbound_end=outbound_end,
        prices=list(airline_series_map.values()),
        message=message,
    )


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
    if len(airline_codes) > MAX_AIRLINES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provide no more than {MAX_AIRLINES} airline codes.",
        )

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
        link_by_pair: Dict[Tuple[str, str], AutoSearchAirlineModel] = {}
        for link in auto_search_airline_models:
            airline = airline_by_id.get(link.airline_id)
            code_key = (
                airline.code.upper()
                if airline and airline.code
                else airline.airline_id
                if airline
                else link.auto_search_airline_id
            )
            link_by_pair[(code_key, link.route_id)] = link

        total_inserted = 0
        for (code, route_id), entries in aggregated_price_map.items():
            key = (code.upper(), route_id)
            link = link_by_pair.get(key)
            if not link:
                log.warning(
                    "Skipping price entries for airline code %s route %s; no matching auto_search_airline link",
                    code,
                    route_id,
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

    response_payload = _compose_auto_search_response(
        auto_search=auto_search_model,
        route=route,
        return_route=return_route,
        airlines=airline_models,
        auto_search_airlines=auto_search_airline_models,
        prices=price_models,
        travel_class=payload.travel_class,
        direct_flight=payload.direct_flight,
        message="Auto flight search initiated.",
    )

    log.debug(
        "Auto flight search response for user %s: %s",
        user.id,
        response_payload.model_dump(),
    )

    return response_payload


@router.get(
    "/auto-search",
    response_model=List[AutoFlightSearchResponse],
    status_code=status.HTTP_200_OK,
)
async def list_auto_flight_searches(user=Depends(get_verified_user)):
    auto_search_table = AutoSearchTable()
    routes_table = FlightRoutesTable()
    airlines_table = AirlinesTable()
    auto_search_airlines_table = AutoSearchAirlinesTable()
    prices_table = PricesTable()

    auto_search_models = auto_search_table.list_all()
    responses: List[AutoFlightSearchResponse] = []

    for auto_search_model in auto_search_models:
        route = routes_table.get(auto_search_model.departure_route_id)
        if not route:
            log.warning(
                "Auto search %s skipped during listing; missing departure route %s",
                auto_search_model.auto_search_id,
                auto_search_model.departure_route_id,
            )
            continue

        return_route: FlightRouteModel | None = None
        if auto_search_model.return_route_id:
            return_route = routes_table.get(auto_search_model.return_route_id)
        if not return_route:
            return_route = routes_table.get_or_create(route.to_place, route.from_place)

        auto_search_airline_models = auto_search_airlines_table.list_for_auto_search(
            auto_search_model.auto_search_id
        )

        airline_models: List[AirlineModel] = []
        for link in auto_search_airline_models:
            airline = airlines_table.get(link.airline_id)
            if airline:
                airline_models.append(airline)
            else:
                log.warning(
                    "Auto search %s references missing airline %s during listing",
                    auto_search_model.auto_search_id,
                    link.airline_id,
                )

        price_models = prices_table.list_by_auto_search(auto_search_model.auto_search_id)

        try:
            responses.append(
                _compose_auto_search_response(
                    auto_search=auto_search_model,
                    route=route,
                    return_route=return_route,
                    airlines=airline_models,
                    auto_search_airlines=auto_search_airline_models,
                    prices=price_models,
                    travel_class=auto_search_model.travel_class,
                    direct_flight=auto_search_model.direct_flight,
                    message="Auto flight search loaded.",
                )
            )
        except HTTPException as exc:
            log.warning(
                "Failed to compose auto search %s: %s",
                auto_search_model.auto_search_id,
                exc.detail if isinstance(exc.detail, str) else exc.detail,
            )

    log.debug("Listed %d auto flight searches for user %s", len(responses), user.id)
    return responses


@router.post(
    "/auto-search/refresh-all",
    response_model=List[AutoFlightSearchResponse],
    status_code=status.HTTP_200_OK,
)
async def refresh_all_auto_flight_searches(user=Depends(get_verified_user)):
    """
    Manually trigger a refresh for all saved auto searches.

    This mirrors the effect of pressing the refresh button on every saved search
    card in the frontend.
    """
    auto_search_table = AutoSearchTable()
    auto_search_models = auto_search_table.list_all()

    responses: List[AutoFlightSearchResponse] = []
    for auto_search_model in auto_search_models:
        try:
            responses.append(
                _refresh_auto_flight_search_sync(auto_search_model.auto_search_id)
            )
        except HTTPException as exc:
            log.warning(
                "Failed to refresh auto search %s via /refresh-all: %s",
                auto_search_model.auto_search_id,
                exc.detail if isinstance(exc.detail, str) else exc.detail,
            )
        except Exception:
            log.exception(
                "Unexpected error refreshing auto search %s via /refresh-all",
                auto_search_model.auto_search_id,
            )

    log.info(
        "Manual /auto-search/refresh-all completed: %d of %d auto searches refreshed",
        len(responses),
        len(auto_search_models),
    )
    return responses


@router.get(
    "/auto-search/schedule",
    response_model=AutoSearchScheduleModel,
    status_code=status.HTTP_200_OK,
)
async def get_auto_search_schedule(user=Depends(get_verified_user)):
    """
    Return the current daily auto-search refresh time.
    """
    return AutoSearchScheduleModel(time=_AUTO_SEARCH_REFRESH_TIME.strftime("%H:%M"))


@router.post(
    "/auto-search/schedule",
    response_model=AutoSearchScheduleModel,
    status_code=status.HTTP_200_OK,
)
async def set_auto_search_schedule(
    payload: AutoSearchScheduleModel, user=Depends(get_verified_user)
):
    """
    Update the daily auto-search refresh time (HH:MM 24-hour format).

    This immediately reschedules the in-process timer.
    """
    global _AUTO_SEARCH_REFRESH_TIME

    new_time = _parse_time_string(payload.time)
    _AUTO_SEARCH_REFRESH_TIME = new_time
    _schedule_next_auto_search_refresh()

    log.info(
        "Updated auto-search refresh schedule to %s by user %s",
        payload.time,
        getattr(user, "id", "unknown"),
    )

    return AutoSearchScheduleModel(time=_AUTO_SEARCH_REFRESH_TIME.strftime("%H:%M"))


def _refresh_auto_flight_search_sync(auto_search_id: str) -> AutoFlightSearchResponse:
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

    unique_airline_codes = list(dict.fromkeys(code.upper() for code in airline_codes))

    if len(unique_airline_codes) < MIN_AIRLINES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"At least {MIN_AIRLINES} airlines with codes are required to refresh.",
        )
    if len(unique_airline_codes) > MAX_AIRLINES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provide no more than {MAX_AIRLINES} airline codes.",
        )

    expected_pairs: set[tuple[str, str]] = set()
    for airline in airline_models:
        dep_link = auto_search_airlines_table.get_or_create(
            auto_search_id=auto_search_model.auto_search_id,
            airline_id=airline.airline_id,
            route_id=route.route_id,
        )
        expected_pairs.add((dep_link.airline_id, dep_link.route_id))
        if return_route and return_route.route_id:
            ret_link = auto_search_airlines_table.get_or_create(
                auto_search_id=auto_search_model.auto_search_id,
                airline_id=airline.airline_id,
                route_id=return_route.route_id,
            )
            expected_pairs.add((ret_link.airline_id, ret_link.route_id))

    auto_search_airline_models = auto_search_airlines_table.list_for_auto_search(
        auto_search_id
    )

    aggregated_price_map = _collect_calendar_prices_for_airlines(
        route=route,
        return_route=return_route,
        airline_codes=unique_airline_codes,
        travel_class=auto_search_model.travel_class,
        direct_flight=auto_search_model.direct_flight,
    )

    prices_table.delete_for_auto_search(auto_search_model.auto_search_id)

    price_models: List[PriceModel] = []
    if aggregated_price_map:
        airline_by_id = {airline.airline_id: airline for airline in airline_models}
        link_by_pair: Dict[Tuple[str, str], AutoSearchAirlineModel] = {}
        for link in auto_search_airline_models:
            airline = airline_by_id.get(link.airline_id)
            code_key = (
                airline.code.upper()
                if airline and airline.code
                else airline.airline_id
                if airline
                else link.auto_search_airline_id
            )
            link_by_pair[(code_key, link.route_id)] = link

        total_inserted = 0
        for (code, route_id), entries in aggregated_price_map.items():
            key = (code.upper(), route_id)
            link = link_by_pair.get(key)
            if not link:
                log.warning(
                    "Skipping price entries for airline code %s route %s; no matching auto_search_airline link",
                    code,
                    route_id,
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

    response_payload = _compose_auto_search_response(
        auto_search=auto_search_model,
        route=route,
        return_route=return_route,
        airlines=airline_models,
        auto_search_airlines=auto_search_airline_models,
        prices=price_models,
        travel_class=auto_search_model.travel_class,
        direct_flight=auto_search_model.direct_flight,
        message="Auto flight search refreshed.",
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
    """
    HTTP endpoint wrapper that delegates to the synchronous core logic.
    """
    response_payload = _refresh_auto_flight_search_sync(auto_search_id)

    log.debug(
        "Auto flight search refresh response for user %s: %s",
        user.id,
        response_payload.model_dump(),
    )

    return response_payload


@router.delete(
    "/auto-search/{auto_search_id}",
    response_model=AutoFlightDeleteResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_auto_flight_search(
    auto_search_id: str, user=Depends(get_verified_user)
):
    auto_search_table = AutoSearchTable()
    routes_table = FlightRoutesTable()
    auto_search_airlines_table = AutoSearchAirlinesTable()
    prices_table = PricesTable()

    auto_search_model = auto_search_table.get(auto_search_id)
    if not auto_search_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auto search {auto_search_id} not found.",
        )

    departure_route_id = auto_search_model.departure_route_id
    return_route_id = auto_search_model.return_route_id

    prices_deleted = prices_table.delete_for_auto_search(auto_search_id)
    auto_search_airlines_table.delete(auto_search_id)
    auto_search_table.delete(auto_search_id)

    for route_id in {departure_route_id, return_route_id}:
        if not route_id:
            continue
        remaining = auto_search_table.list_by_route(route_id)
        if not remaining:
            deleted = routes_table.delete(route_id)
            if deleted:
                log.info(
                    "Deleted unused flight route %s after removing auto_search %s",
                    route_id,
                    auto_search_id,
                )

    log.info(
        "Deleted auto_search %s (prices=%d)", auto_search_id, prices_deleted
    )

    return AutoFlightDeleteResponse(
        auto_search_id=auto_search_id,
        prices_deleted=prices_deleted,
        message="Auto flight search deleted.",
    )


class MCPFlightSearchRequest(BaseModel):
    """Request model for MCP flight search"""

    departure: str = Field(..., min_length=3, max_length=10, description="Origin airport code")
    destination: str = Field(..., min_length=3, max_length=10, description="Destination airport code")
    airlines: List[str] = Field(..., description="Airline codes to search (1-10 airlines)")
    return_trip_days: Optional[int] = Field(None, ge=1, le=365, description="Number of days for return trip")
    travel_class: int = Field(0, ge=0, le=3, description="0=economy, 1=premium_economy, 2=business, 3=first_class")
    direct_flight: bool = Field(False, description="Search direct flights only")
    model_id: str = Field(..., description="Model ID to use (Gemini, Ollama, or OpenAI)")


class MCPFlightSearchResponse(BaseModel):
    """Response model for MCP flight search"""

    success: bool
    message: str
    saved_flight_count: int = 0
    tool_calls_count: int = 0
    auto_search_id: Optional[str] = None
    error: Optional[str] = None


@router.post(
    "/mcp-search",
    response_model=MCPFlightSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="AI-powered flight search using MCP",
)
async def mcp_flight_search(
    request: Request,
    payload: MCPFlightSearchRequest,
    user=Depends(get_verified_user),
):
    """
    Run AI-powered flight search using MCP (Model Context Protocol).

    The AI will:
    1. Use Google AI Mode to get initial insights about cheap periods
    2. Use Google Flight Calendar to verify prices
    3. Use Google Flight Search to get detailed flight data and store in database

    Only Google Flight Search results are stored in the database.
    """
    from open_webui.ai_auto.context import MCPRequest
    from open_webui.ai_auto.workflow import run_mcp_workflow

    # Validate airlines
    if len(payload.airlines) < MIN_AIRLINES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provide at least {MIN_AIRLINES} airline codes.",
        )

    if len(payload.airlines) > MAX_AIRLINES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provide no more than {MAX_AIRLINES} airline codes.",
        )

    # Normalize airline codes
    airlines_table = AirlinesTable()
    normalized_airlines = []
    for airline_input in payload.airlines:
        normalized = airline_input.strip().upper()
        airline = airlines_table.get_by_code(normalized)
        if airline and airline.code:
            normalized_airlines.append(airline.code)
        else:
            # Try by name
            airline = airlines_table.get_by_name(normalized)
            if airline and airline.code:
                normalized_airlines.append(airline.code)
            elif len(normalized) in (2, 3):
                normalized_airlines.append(normalized)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unrecognized airline: {normalized}",
                )

    normalized_airlines = list(dict.fromkeys(normalized_airlines))

    # Create MCP request
    mcp_request = MCPRequest(
        departure=payload.departure.upper(),
        destination=payload.destination.upper(),
        airlines=normalized_airlines,
        return_trip_days=payload.return_trip_days,
        travel_class=payload.travel_class,
        direct_flight=payload.direct_flight,
        model_id=payload.model_id,
        user_id=user.id,
    )

    # Run workflow
    log.info(
        "MCP flight search request from user %s: %s -> %s, airlines=%s, model=%s",
        user.id,
        payload.departure,
        payload.destination,
        normalized_airlines,
        payload.model_id,
    )
    
    try:
        mcp_response = await run_mcp_workflow(request, mcp_request, user)
        log.info(
            "MCP workflow completed for user %s: success=%s, flights=%d, tool_calls=%d",
            user.id,
            mcp_response.success,
            mcp_response.saved_flight_count,
            len(mcp_response.tool_calls),
        )

        # Extract auto_search_id from workflow state
        auto_search_id = None
        if mcp_response.workflow_state:
            auto_search_id = mcp_response.workflow_state.auto_search_id

        return MCPFlightSearchResponse(
            success=mcp_response.success,
            message=mcp_response.message,
            saved_flight_count=mcp_response.saved_flight_count,
            tool_calls_count=len(mcp_response.tool_calls),
            auto_search_id=auto_search_id,
            error=mcp_response.error,
        )

    except Exception as e:
        log.exception("MCP flight search failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MCP flight search failed: {str(e)}",
        )