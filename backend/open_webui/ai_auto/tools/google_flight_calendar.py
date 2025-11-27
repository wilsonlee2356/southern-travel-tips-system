"""Google Flight Calendar Tool for MCP"""

import logging
from typing import Any, Dict, Optional

from open_webui.utils.flight_calendar import fetch_calendar, FlightCalendarError

log = logging.getLogger(__name__)


class GoogleFlightCalendarTool:
    """Tool for querying Google Flight Calendar API to get price overviews"""

    def call(
        self,
        departure_id: str,
        arrival_id: str,
        outbound_date: str,
        outbound_date_start: str,
        outbound_date_end: str,
        flight_type: str = "round_trip",
        travel_class: Optional[str] = None,
        non_stop: Optional[bool] = None,
        included_airlines: Optional[str] = None,
        return_date: Optional[str] = None,
        return_date_start: Optional[str] = None,
        return_date_end: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call Google Flight Calendar API to get price overview for a date range.

        Args:
            departure_id: Departure airport code
            arrival_id: Arrival airport code
            outbound_date: Anchor date for outbound (YYYY-MM-DD)
            outbound_date_start: Start of outbound date range (YYYY-MM-DD)
            outbound_date_end: End of outbound date range (YYYY-MM-DD)
            flight_type: "one_way" or "round_trip"
            travel_class: Optional travel class (economy, premium_economy, business, first)
            non_stop: Optional boolean for direct flights only
            included_airlines: Optional comma-separated airline codes
            return_date: Optional anchor date for return (YYYY-MM-DD)
            return_date_start: Optional start of return date range (YYYY-MM-DD)
            return_date_end: Optional end of return date range (YYYY-MM-DD)

        Returns:
            Dict containing calendar data with price information
        """
        log.info(
            "Calling Google Flight Calendar API: %s -> %s, dates=%s to %s, flight_type=%s, airlines=%s",
            departure_id,
            arrival_id,
            outbound_date_start,
            outbound_date_end,
            flight_type,
            included_airlines or "all",
        )
        log.debug(
            "Google Flight Calendar params: travel_class=%s, non_stop=%s, return_date=%s",
            travel_class,
            non_stop,
            return_date,
        )

        try:
            data = fetch_calendar(
                departure_id=departure_id,
                arrival_id=arrival_id,
                outbound_date=outbound_date,
                outbound_date_start=outbound_date_start,
                outbound_date_end=outbound_date_end,
                flight_type=flight_type,
                travel_class=travel_class,
                non_stop=non_stop,
                included_airlines=included_airlines,
                return_date=return_date,
                return_date_start=return_date_start,
                return_date_end=return_date_end,
            )

            calendar_entries = data.get("calendar", [])
            log.info(
                "Google Flight Calendar response: %d entries for %s -> %s",
                len(calendar_entries),
                departure_id,
                arrival_id,
            )

            return data

        except FlightCalendarError as e:
            log.error("Google Flight Calendar error: %s", e)
            raise RuntimeError(f"Google Flight Calendar request failed: {str(e)}") from e

