"""Google Flight Search Tool for MCP"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from open_webui.ai_auto.storage import FlightStorage

log = logging.getLogger(__name__)

GOOGLE_FLIGHTS_ENDPOINT = "https://www.searchapi.io/api/v1/search"
DEFAULT_ENGINE = "google_flights"


class GoogleFlightSearchTool:
    """Tool for querying Google Flight Search API and storing results in database"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GOOGLE_FLIGHTS_API_KEY") or os.environ.get("SEARCHAPI_KEY")
        if not self.api_key:
            raise ValueError(
                "Missing SearchAPI key. Set GOOGLE_FLIGHTS_API_KEY or SEARCHAPI_KEY environment variable."
            )
        self.storage = FlightStorage()

    def call(
        self,
        departure_id: str,
        arrival_id: str,
        outbound_date: str,
        return_date: Optional[str] = None,
        travel_class: str = "economy",
        included_airlines: Optional[str] = None,
        excluded_airlines: Optional[str] = None,
        non_stop: Optional[bool] = None,
        adults: int = 1,
        children: int = 0,
        store_results: bool = True,
        auto_search_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call Google Flight Search API to get detailed flight data.

        Args:
            departure_id: Departure airport code
            arrival_id: Arrival airport code
            outbound_date: Outbound date (YYYY-MM-DD)
            return_date: Optional return date (YYYY-MM-DD)
            travel_class: Travel class (economy, premium_economy, business, first)
            included_airlines: Optional comma-separated airline codes
            excluded_airlines: Optional comma-separated airline codes
            non_stop: Optional boolean for direct flights only
            adults: Number of adults
            children: Number of children
            store_results: Whether to store results in database
            auto_search_id: Optional auto_search_id to associate stored flights with

        Returns:
            Dict containing flight search results and storage info
        """
        params: Dict[str, Any] = {
            "engine": DEFAULT_ENGINE,
            "api_key": self.api_key,
            "departure_id": departure_id,
            "arrival_id": arrival_id,
            "outbound_date": outbound_date,
            "flight_type": "round_trip" if return_date else "one_way",
            "travel_class": travel_class,
            "adults": adults,
            "currency": "HKD",
            "gl": "HK",
            "hl": "en",
        }

        if return_date:
            params["return_date"] = return_date

        if included_airlines:
            params["included_airlines"] = included_airlines

        if excluded_airlines:
            params["excluded_airlines"] = excluded_airlines

        if non_stop is True:
            params["stops"] = "0"
        elif non_stop is False:
            params["stops"] = "1"

        if children > 0:
            params["children"] = children

        log.info(
            "Calling Google Flight Search API: %s -> %s, outbound=%s, return=%s, class=%s, airlines=%s, store=%s",
            departure_id,
            arrival_id,
            outbound_date,
            return_date or "none",
            travel_class,
            included_airlines or "all",
            store_results,
        )
        log.debug(
            "Google Flight Search params: non_stop=%s, adults=%d, children=%d, excluded_airlines=%s",
            non_stop,
            adults,
            children,
            excluded_airlines or "none",
        )

        try:
            response = requests.get(GOOGLE_FLIGHTS_ENDPOINT, params=params, timeout=120)
            response.raise_for_status()
            data: Dict[str, Any] = response.json()

            flights = data.get("flights", [])
            best_flights = data.get("best_flights", [])
            other_flights = data.get("other_flights", [])

            all_flights = []
            if best_flights:
                all_flights.extend(best_flights)
            if other_flights:
                all_flights.extend(other_flights)
            if flights:
                all_flights.extend(flights)

            log.info(
                "Google Flight Search response: %d total flights (%d best, %d other)",
                len(all_flights),
                len(best_flights) if best_flights else 0,
                len(other_flights) if other_flights else 0,
            )
            
            if all_flights:
                # Log price range if available
                prices = [f.get("price", 0) for f in all_flights if f.get("price")]
                if prices:
                    log.debug(
                        "Flight price range: min=%d, max=%d, avg=%.0f HKD",
                        min(prices),
                        max(prices),
                        sum(prices) / len(prices),
                    )

            stored_count = 0
            if store_results and all_flights and auto_search_id:
                log.debug("Filtering and storing flights for auto_search_id=%s", auto_search_id)
                # Filter and store only relevant flights
                relevant_flights = self._filter_relevant_flights(
                    all_flights, included_airlines, departure_id, arrival_id
                )
                log.debug(
                    "Filtered flights: %d relevant out of %d total",
                    len(relevant_flights),
                    len(all_flights),
                )
                stored_count = self.storage.store_flights(
                    relevant_flights, auto_search_id, departure_id, arrival_id
                )
                log.info(
                    "Stored %d relevant flights in database (auto_search_id=%s)",
                    stored_count,
                    auto_search_id,
                )
            elif store_results:
                if not all_flights:
                    log.warning("No flights to store (empty response)")
                if not auto_search_id:
                    log.warning("Cannot store flights: missing auto_search_id")

            return {
                "flights": all_flights,
                "best_flights": best_flights,
                "other_flights": other_flights,
                "stored_count": stored_count,
                "total_count": len(all_flights),
            }

        except requests.RequestException as e:
            log.error("Google Flight Search request failed: %s", e)
            raise RuntimeError(f"Google Flight Search request failed: {str(e)}") from e

    def _filter_relevant_flights(
        self, flights: List[Dict[str, Any]], included_airlines: Optional[str], departure: str, arrival: str
    ) -> List[Dict[str, Any]]:
        """
        Filter flights to keep only relevant ones (matching airlines, route, etc.)
        Skip irrelevant tickets.
        """
        if not flights:
            return []

        relevant = []
        airline_codes = set()
        if included_airlines:
            airline_codes = {code.strip().upper() for code in included_airlines.split(",")}
            log.debug("Filtering by airlines: %s", airline_codes)
        else:
            log.debug("No airline filter specified, accepting all airlines")

        route_mismatch_count = 0
        airline_mismatch_count = 0
        
        for idx, flight in enumerate(flights):
            # Extract airline code from flight
            flight_segments = flight.get("flights", [])
            if not flight_segments:
                log.debug("Flight %d: skipping (no segments)", idx)
                continue

            # Check if flight matches the route
            first_segment = flight_segments[0]
            last_segment = flight_segments[-1]

            dep_code = (
                first_segment.get("departure_airport", {}).get("id")
                or first_segment.get("departure_airport", {}).get("code")
                or ""
            )
            arr_code = (
                last_segment.get("arrival_airport", {}).get("id")
                or last_segment.get("arrival_airport", {}).get("code")
                or ""
            )

            if dep_code.upper() != departure.upper() or arr_code.upper() != arrival.upper():
                log.debug(
                    "Flight %d: route mismatch (got %s->%s, expected %s->%s)",
                    idx,
                    dep_code,
                    arr_code,
                    departure,
                    arrival,
                )
                route_mismatch_count += 1
                continue

            # Check airline if specified
            if airline_codes:
                flight_airline = first_segment.get("airline", "")
                flight_number = first_segment.get("flight_number", "")
                # Extract airline code from flight number (e.g., "CX 123" -> "CX")
                if flight_number:
                    flight_airline_code = flight_number.split()[0].upper() if " " in flight_number else ""
                else:
                    flight_airline_code = ""

                # Check if airline matches
                if flight_airline_code not in airline_codes and flight_airline.upper() not in airline_codes:
                    # Try to match by partial airline name
                    matched = False
                    for code in airline_codes:
                        if code in flight_airline.upper() or flight_airline.upper() in code:
                            matched = True
                            log.debug(
                                "Flight %d: matched airline by partial name (%s contains %s)",
                                idx,
                                flight_airline,
                                code,
                            )
                            break
                    if not matched:
                        log.debug(
                            "Flight %d: airline mismatch (got %s/%s, expected %s)",
                            idx,
                            flight_airline_code,
                            flight_airline,
                            airline_codes,
                        )
                        airline_mismatch_count += 1
                        continue

            relevant.append(flight)
            log.debug(
                "Flight %d: accepted (route=%s->%s, airline=%s/%s)",
                idx,
                dep_code,
                arr_code,
                flight_airline_code or "unknown",
                flight_airline,
            )

        log.info(
            "Filtered flights: %d relevant out of %d total (route=%s->%s, airlines=%s)",
            len(relevant),
            len(flights),
            departure,
            arrival,
            included_airlines or "all",
        )
        
        if len(relevant) < len(flights):
            skipped_total = len(flights) - len(relevant)
            log.info(
                "Skipped %d flights: route_mismatch=%d, airline_mismatch=%d, other=%d",
                skipped_total,
                route_mismatch_count,
                airline_mismatch_count,
                skipped_total - route_mismatch_count - airline_mismatch_count,
            )
        
        return relevant

