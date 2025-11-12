import logging
import os
from typing import Any, Dict, Optional

import requests

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

CALENDAR_ENDPOINT = "https://www.searchapi.io/api/v1/search"
DEFAULT_ENGINE = "google_flights_calendar"


class FlightCalendarError(RuntimeError):
    pass


def _get_api_key(explicit: Optional[str] = None) -> str:
    api_key = explicit or os.environ.get("GOOGLE_FLIGHTS_API_KEY")
    if not api_key:
        raise FlightCalendarError(
            "Missing SearchAPI key. Set GOOGLE_FLIGHTS_API_KEY environment variable."
        )
    return api_key


def fetch_calendar(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    outbound_date_start: str,
    outbound_date_end: str,
    *,
    flight_type: str = "one_way",
    travel_class: Optional[str] = None,
    non_stop: Optional[bool] = None,
    airline: Optional[str] = None,
    return_date: Optional[str] = None,
    return_date_start: Optional[str] = None,
    return_date_end: Optional[str] = None,
    engine: str = DEFAULT_ENGINE,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call the Google Flights calendar API via SearchAPI.io and return the JSON payload.
    Raises FlightCalendarError on failure.
    """

    resolved_key = _get_api_key(api_key)

    params: Dict[str, Any] = {
        "engine": engine,
        "flight_type": flight_type,
        "departure_id": departure_id,
        "arrival_id": arrival_id,
        "outbound_date": outbound_date,
        "outbound_date_start": outbound_date_start,
        "outbound_date_end": outbound_date_end,
        "api_key": resolved_key,
    }

    if travel_class:
        params["travel_class"] = travel_class
    if non_stop is True:
        params["non_stop"] = "true"
    elif non_stop is False:
        params["non_stop"] = "false"
    if airline:
        params["airline"] = airline

    if flight_type == "round_trip":
        if not return_date:
            raise FlightCalendarError("return_date is required for round_trip calendar searches")
        params["return_date"] = return_date
        if return_date_start:
            params["return_date_start"] = return_date_start
        if return_date_end:
            params["return_date_end"] = return_date_end
    else:
        # allow optional return params for one-way only when explicitly passed
        if return_date:
            params["return_date"] = return_date
        if return_date_start:
            params["return_date_start"] = return_date_start
        if return_date_end:
            params["return_date_end"] = return_date_end

    log.debug("Requesting flight calendar with params: %s", {**params, "api_key": "***"})

    response = requests.get(CALENDAR_ENDPOINT, params=params, timeout=60)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:  # pragma: no cover - pass context through
        detail = exc.response.text if exc.response else str(exc)
        raise FlightCalendarError(f"Calendar request failed: {detail}") from exc

    data: Dict[str, Any] = response.json()
    log.info(
        "Fetched calendar data for %s -> %s (%s entries)",
        departure_id,
        arrival_id,
        len(data.get("calendar", [])),
    )
    return data

