"""Storage module for storing flight search results in database"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from open_webui.models.flight_pricing import (
    AirlinesTable,
    AutoSearchAirlineModel,
    AutoSearchAirlinesTable,
    AutoSearchModel,
    AutoSearchTable,
    FlightRoutesTable,
    PricesTable,
)

log = logging.getLogger(__name__)


class FlightStorage:
    """Handles storage of flight search results in the database"""

    def __init__(self):
        self.auto_search_table = AutoSearchTable()
        self.routes_table = FlightRoutesTable()
        self.airlines_table = AirlinesTable()
        self.auto_search_airlines_table = AutoSearchAirlinesTable()
        self.prices_table = PricesTable()

    def store_flights(
        self,
        flights: List[Dict[str, Any]],
        auto_search_id: str,
        departure_code: str,
        arrival_code: str,
    ) -> int:
        """
        Store flight search results in the database.

        Args:
            flights: List of flight data dictionaries from Google Flight Search API
            auto_search_id: The auto_search_id to associate flights with
            departure_code: Departure airport code
            arrival_code: Arrival airport code

        Returns:
            Number of flights successfully stored
        """
        log.info(
            "Storing flights: count=%d, auto_search_id=%s, route=%s->%s",
            len(flights),
            auto_search_id,
            departure_code,
            arrival_code,
        )
        
        if not flights:
            log.warning("No flights provided to store_flights")
            return 0

        # Get the auto search configuration
        auto_search = self.auto_search_table.get(auto_search_id)
        if not auto_search:
            log.error("Auto search %s not found, cannot store flights", auto_search_id)
            return 0
        
        log.debug("Found auto_search: %s (class=%d, direct=%s)", auto_search_id, auto_search.travel_class, auto_search.direct_flight)

        # Get routes
        departure_route = self.routes_table.get_by_places(departure_code, arrival_code)
        if not departure_route:
            departure_route = self.routes_table.create(departure_code, arrival_code)

        return_route = self.routes_table.get_by_places(arrival_code, departure_code)
        if not return_route:
            return_route = self.routes_table.create(arrival_code, departure_code)

        stored_count = 0
        skipped_count = 0
        error_count = 0

        # Group flights by airline and route
        log.debug("Processing %d flights for storage", len(flights))
        for idx, flight in enumerate(flights):
            try:
                flight_segments = flight.get("flights", [])
                if not flight_segments:
                    log.debug("Flight %d: skipping (no segments)", idx)
                    skipped_count += 1
                    continue

                first_segment = flight_segments[0]
                airline_name = first_segment.get("airline", "")
                flight_number = first_segment.get("flight_number", "")
                log.debug("Flight %d: airline=%s, flight_number=%s", idx, airline_name, flight_number)

                # Extract airline code from flight number
                airline_code = ""
                if flight_number and " " in flight_number:
                    airline_code = flight_number.split()[0].upper()
                elif airline_name:
                    # Try to get airline by name
                    airline = self.airlines_table.get_by_name(airline_name)
                    if airline and airline.code:
                        airline_code = airline.code
                    else:
                        # Create airline if doesn't exist
                        airline = self.airlines_table.get_or_create_by_code(airline_code or airline_name[:2].upper())
                        airline_code = airline.code or airline_name[:2].upper()

                if not airline_code:
                    log.warning("Could not determine airline code for flight: %s", flight_number)
                    continue

                # Get or create airline
                airline = self.airlines_table.get_or_create_by_code(airline_code)

                # Get or create auto_search_airline link for departure route
                auto_search_airline = self.auto_search_airlines_table.get_or_create(
                    auto_search_id=auto_search_id,
                    airline_id=airline.airline_id,
                    route_id=departure_route.route_id,
                )

                # Extract price
                price = flight.get("price")
                if not price:
                    # Try alternative price fields
                    price = flight.get("total_price") or flight.get("cost") or 0

                if not price or price <= 0:
                    log.debug("Flight %d: skipping (invalid price: %s)", idx, price)
                    skipped_count += 1
                    continue

                # Extract departure date
                dep_datetime_str = first_segment.get("departure_airport", {}).get("time", "")
                if not dep_datetime_str:
                    log.debug("Flight %d: skipping (no departure time)", idx)
                    skipped_count += 1
                    continue
                
                log.debug(
                    "Flight %d: price=%d HKD, departure=%s, airline_code=%s",
                    idx,
                    price,
                    dep_datetime_str,
                    airline_code,
                )

                # Parse date (format: "YYYY-MM-DD HH:MM" or similar)
                try:
                    dep_date = datetime.strptime(dep_datetime_str.split()[0], "%Y-%m-%d")
                except (ValueError, IndexError):
                    log.warning("Could not parse departure date: %s", dep_datetime_str)
                    continue

                # Store price
                price_model = self.prices_table.create(
                    auto_search_airline_id=auto_search_airline.auto_search_airline_id,
                    departure_date=dep_date,
                    price=int(price),
                    is_lowest_price=False,  # Could be determined by comparing with other prices
                )
                
                log.debug(
                    "Stored price: price_id=%s, date=%s, price=%d HKD, airline=%s",
                    price_model.price_id,
                    dep_date.isoformat(),
                    price,
                    airline_code,
                )

                stored_count += 1

            except Exception as e:
                log.exception("Error storing flight %d (flight_number=%s): %s", idx, flight_number, e)
                error_count += 1
                continue

        log.info(
            "Flight storage completed: stored=%d, skipped=%d, errors=%d, total=%d (auto_search_id=%s)",
            stored_count,
            skipped_count,
            error_count,
            len(flights),
            auto_search_id,
        )
        return stored_count

