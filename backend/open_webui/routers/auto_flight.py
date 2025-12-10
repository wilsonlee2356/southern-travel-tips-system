import logging
from datetime import datetime, date, time
from typing import List, Optional, Dict, Any

import requests

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, validator

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.flight_pricing import (
    AirlinesTable,
    AirlineModel,
    Airline,
)
from open_webui.models.auto_search_config import (
    AutoSearchConfig,
    AutoSearchAirline,
    AutoSearchConfigModel,
)
from open_webui.models.flight_search import (
    Search,
    FlightOption,
    FlightSegment,
    FlightExtension,
    OptionExtension,
    Layover,
    PriceInsight,
    PriceHistory,
    AirlineAuto,
    AirportAuto,
    SearchAirport,
)
from open_webui.utils.auth import get_verified_user
from open_webui.internal.db import get_db

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()

MIN_AIRLINES = 1
MAX_AIRLINES = 10


class AutoFlightSearchRequest(BaseModel):
    from_place: str = Field(..., min_length=3, max_length=10, description="Origin airport code")
    to_place: str = Field(..., min_length=3, max_length=10, description="Destination airport code")
    airlines: List[str] = Field(..., description="Airline names to track (1-10 airlines)")
    travel_class: int = Field(0, ge=0, le=3, description="0=economy, 1=premium_economy, 2=business, 3=first_class")
    direct_flight: bool = Field(False, description="Track direct flights only")
    return_trip_duration: int = Field(..., ge=1, le=365, description="Number of days for the return trip")

    @validator("airlines")
    def validate_airlines(cls, value: List[str]) -> List[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        unique = list(dict.fromkeys(cleaned))
        if len(unique) < MIN_AIRLINES:
            raise ValueError(f"Provide at least {MIN_AIRLINES} unique airline names.")
        if len(unique) > MAX_AIRLINES:
            raise ValueError(f"Select no more than {MAX_AIRLINES} airlines.")
        return unique


class AutoFlightSearchResponse(BaseModel):
    """Simple response for auto flight search creation"""
    success: bool = True
    message: str = "Auto flight search initiated. n8n workflow will handle the search."
    airlines: List[AirlineModel] = Field(default_factory=list)
    auto_search_id: Optional[int] = None


class AutoSearchListResponse(BaseModel):
    """Response for listing auto searches"""
    auto_search_id: int
    departure_id: str
    arrival_id: str
    travel_class: int
    is_direct: bool
    return_trip_duration: int
    created_at: datetime
    updated_at: datetime
    airlines: List[AirlineModel] = Field(default_factory=list)


class N8nWebhookData(BaseModel):
    """Data structure for n8n webhook response"""
    search_parameters: Dict[str, Any]
    best_flights: Optional[List[Dict[str, Any]]] = None
    other_flights: Optional[List[Dict[str, Any]]] = None
    price_insights: Optional[Dict[str, Any]] = None
    price_history: Optional[List[Dict[str, Any]]] = None


def _call_n8n_webhook_for_airlines(
    departure_id: str,
    arrival_id: str,
    is_direct: bool,
    airline_codes: List[str],
    trip_duration: int,
) -> None:
    """
    Call n8n webhook API for each airline when a new auto search is created.
    
    URL format: https://n8n.ssl-labs.ai/webhook/f56d4963-08b0-4c21-97c7-be28249e32d8/auto_search/{departure_id}/{arrival_id}/{is_direct}/{airline}/{trip_duration}
    
    Args:
        departure_id: Departure airport code (e.g., HKG)
        arrival_id: Arrival airport code (e.g., KIX)
        is_direct: Whether to search for direct flights only
        airline_codes: List of airline codes to call webhook for
        trip_duration: Trip duration in days (required, 1-365)
    """
    base_url = "https://n8n.ssl-labs.ai/webhook/f56d4963-08b0-4c21-97c7-be28249e32d8/auto_search"
    
    # Convert boolean to string for URL
    is_direct_str = "true" if is_direct else "false"
    
    for airline_code in airline_codes:
        airline_code_upper = airline_code.upper().strip()
        if not airline_code_upper:
                        continue
            
        # Build the webhook URL
        webhook_url = f"{base_url}/{departure_id}/{arrival_id}/{is_direct_str}/{airline_code_upper}/{trip_duration}"
        
        try:
            log.info(
                "Calling n8n webhook for airline %s: %s -> %s, direct=%s, duration=%d days",
                airline_code_upper,
                departure_id,
                arrival_id,
                is_direct_str,
                trip_duration,
            )
            
            response = requests.get(webhook_url, timeout=3600)  # 1 hour timeout
            response.raise_for_status()
            
            # Log the response
            log.info(
                "n8n webhook response for airline %s: status=%d, response=%s",
                airline_code_upper,
                response.status_code,
                response.text[:500] if response.text else "No response body",
            )
            
            # Parse and store the flight data if present
            if response.text:
                try:
                    flight_data = response.json()
                    # Handle both single object and list
                    if isinstance(flight_data, dict):
                        data_list = [flight_data]
                    elif isinstance(flight_data, list):
                        data_list = flight_data
                    else:
                        log.warning("Unexpected data format from n8n: %s", type(flight_data))
                        continue

                    # Store the data in database
                    with get_db() as db:
                        try:
                            # Find the auto_search_airline_id
                            auto_search_airline = db.query(AutoSearchAirline).join(AutoSearchConfig).filter(
                                AutoSearchConfig.departure_id == departure_id.upper(),
                                AutoSearchConfig.arrival_id == arrival_id.upper(),
                            ).join(Airline).filter(
                                Airline.code == airline_code_upper
                            ).first()
                            
                            auto_search_airline_id = auto_search_airline.auto_search_airline_id if auto_search_airline else None
                            
                            if auto_search_airline_id is None:
                                log.warning(
                                    "No matching auto_search_airline found for %s -> %s, airline=%s. Storing without link.",
                                    departure_id,
                                    arrival_id,
                                    airline_code_upper,
                                )
                            
                            search_ids = []
                            for search_data in data_list:
                                try:
                                    log.info("Processing search data from n8n response for airline %s", airline_code_upper)
                                    search_id = _store_flight_search_data(db, search_data, auto_search_airline_id)
                                    search_ids.append(search_id)
                                    log.info("Successfully stored search with ID: %d", search_id)
                                except Exception as e:
                                    log.exception("Failed to store search data item: %s", str(e))
                                    continue

                            if search_ids:
                                db.commit()
                                log.info(
                                    "Stored %d flight searches from n8n response for %s -> %s, airline=%s",
                                    len(search_ids),
                                    departure_id,
                                    arrival_id,
                                    airline_code_upper,
                                )
                            else:
                                log.warning("No search records were successfully stored from n8n response")
                                db.rollback()
                        except Exception as e:
                            db.rollback()
                            log.exception("Failed to store n8n response data: %s", str(e))
                except ValueError as e:
                    log.warning("Failed to parse JSON from n8n response: %s", str(e))
                except Exception as e:
                    log.exception("Unexpected error processing n8n response: %s", str(e))
            
        except requests.RequestException as e:
            log.error(
                "n8n webhook call failed for airline %s: %s",
                airline_code_upper,
                str(e),
            )
        except Exception as e:
            log.exception(
                "Unexpected error calling n8n webhook for airline %s: %s",
                airline_code_upper,
                str(e),
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
    """
    Create a new auto flight search and trigger n8n webhook for each airline.
    
    This endpoint validates the request and calls the n8n webhook for each airline.
    The n8n workflow will handle the actual flight search and data storage.
    """
    airlines_table = AirlinesTable()

    airline_codes: List[str] = []
    airline_models: List[AirlineModel] = []
    
    for item in payload.airlines:
        normalized = item.strip()
        if not normalized:
            continue
        upper = normalized.upper()
        by_code = airlines_table.get_by_code(upper)
        if by_code:
            airline_codes.append(by_code.code)
            airline_models.append(by_code)
            continue
        by_name = airlines_table.get_by_name(normalized)
        if by_name and by_name.code:
            airline_codes.append(by_name.code)
            airline_models.append(by_name)
            continue
        if len(upper) in (2, 3):
            # Create airline if it doesn't exist
            airline_model = airlines_table.get_or_create_by_code(upper)
            airline_codes.append(airline_model.code or upper)
            airline_models.append(airline_model)
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

    # Store auto search config in database
    auto_search_id = None
    with get_db() as db:
        try:
            auto_search_config = AutoSearchConfig(
                departure_id=payload.from_place.upper(),
                arrival_id=payload.to_place.upper(),
        travel_class=payload.travel_class,
                is_direct=payload.direct_flight,
                return_trip_duration=payload.return_trip_duration,
            )
            db.add(auto_search_config)
            db.commit()
            db.refresh(auto_search_config)
            auto_search_id = auto_search_config.auto_search_id
            
            # Link airlines to the auto search config
            for airline_model in airline_models:
                auto_search_airline = AutoSearchAirline(
                    auto_search_id=auto_search_config.auto_search_id,
                    airline_id=airline_model.airline_id,
                )
                db.add(auto_search_airline)
            db.commit()
            
            log.info(
                "Auto flight search config stored: id=%d, %s -> %s, airlines=%s",
                auto_search_config.auto_search_id,
                payload.from_place,
                payload.to_place,
                airline_codes,
            )
        except Exception as e:
            db.rollback()
            log.error("Failed to store auto search config: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store auto search configuration",
            )

    # Call n8n webhook for each airline
    _call_n8n_webhook_for_airlines(
        departure_id=payload.from_place.upper(),
        arrival_id=payload.to_place.upper(),
        is_direct=payload.direct_flight,
        airline_codes=airline_codes,
        trip_duration=payload.return_trip_duration,
    )

    log.info(
        "Auto flight search created for user %s: %s -> %s, airlines=%s",
        user.id,
        payload.from_place,
        payload.to_place,
        airline_codes,
    )

    return AutoFlightSearchResponse(
        success=True,
        message="Auto flight search initiated. n8n workflow will handle the search.",
        airlines=airline_models,
        auto_search_id=auto_search_id,
    )


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse date string in YYYY-MM-DD format"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        log.warning("Failed to parse date: %s", date_str)
        return None


def _parse_time(time_str: Optional[str]) -> Optional[time]:
    """Parse time string in HH:MM format"""
    if not time_str:
        return None
    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except (ValueError, TypeError):
        log.warning("Failed to parse time: %s", time_str)
        return None


def _get_or_create_airline_auto(db, airline_name: str, airline_code: Optional[str] = None, airline_logo: Optional[str] = None) -> AirlineAuto:
    """Get or create an airline in airline_auto table"""
    airline_id = airline_code.upper() if airline_code else airline_name.upper()[:10]
    
    airline = db.query(AirlineAuto).filter(AirlineAuto.airline_id == airline_id).first()
    if not airline:
        airline = AirlineAuto(
            airline_id=airline_id,
            code=airline_code.upper() if airline_code else None,
            name=airline_name,
            airline_logo=airline_logo,
        )
        db.add(airline)
        db.flush()
    return airline


def _get_or_create_airport_auto(db, airport_iata: str, airport_name: str) -> AirportAuto:
    """Get or create an airport in airport_auto table"""
    airport = db.query(AirportAuto).filter(AirportAuto.iata == airport_iata.upper()).first()
    if not airport:
        airport = AirportAuto(
            airport_id=airport_iata.upper(),
            iata=airport_iata.upper(),
            airport_name=airport_name,
        )
        db.add(airport)
        db.flush()
    return airport


def _store_flight_search_data(db, search_data: Dict[str, Any], auto_search_airline_id: Optional[int] = None) -> int:
    """Store flight search data from n8n webhook response"""
    log.info("Storing flight search data: has_search_params=%s, has_best_flights=%s, has_other_flights=%s",
             "search_parameters" in search_data,
             "best_flights" in search_data,
             "other_flights" in search_data)
    
    search_params = search_data.get("search_parameters", {})
    if not search_params:
        log.error("Missing search_parameters in search_data: %s", list(search_data.keys()))
        raise ValueError("Missing search_parameters in search data")
    
    # Create or get search record
    outbound_date = _parse_date(search_params.get("outbound_date"))
    if not outbound_date:
        log.error("Invalid or missing outbound_date: %s", search_params.get("outbound_date"))
        raise ValueError(f"Invalid or missing outbound_date: {search_params.get('outbound_date')}")
    
    search = Search(
        auto_search_airline_id=auto_search_airline_id,
        engine=search_params.get("engine", "google_flights"),
        departure_id=search_params.get("departure_id", ""),
        arrival_id=search_params.get("arrival_id", ""),
        currency=search_params.get("currency", "HKD"),
        hl=search_params.get("hl"),
        gl=search_params.get("gl"),
        outbound_date=outbound_date,
        return_date=_parse_date(search_params.get("return_date")),
        flight_type=search_params.get("flight_type", "round_trip"),
        travel_class=search_params.get("travel_class", "economy"),
        stops=search_params.get("stops"),
        adults=int(search_params.get("adults", "1")),
        children=int(search_params.get("children", "0")),
        infants_in_seat=int(search_params.get("infants_in_seat", "0")),
        infants_on_lap=int(search_params.get("infants_on_lap", "0")),
        included_airlines=search_params.get("included_airlines"),
    )
    db.add(search)
    db.flush()
    
    # Store airports
    departure_airport = _get_or_create_airport_auto(db, search.departure_id, f"Airport {search.departure_id}")
    arrival_airport = _get_or_create_airport_auto(db, search.arrival_id, f"Airport {search.arrival_id}")
    
    search_airport_dep = SearchAirport(
        search_id=search.search_id,
        airport_iata=departure_airport.iata,
        is_departure=True,
    )
    search_airport_arr = SearchAirport(
        search_id=search.search_id,
        airport_iata=arrival_airport.iata,
        is_departure=False,
    )
    db.add(search_airport_dep)
    db.add(search_airport_arr)
    
    # Store best flights
    best_flights = search_data.get("best_flights", [])
    for flight_option_data in best_flights:
        _store_flight_option(db, search.search_id, flight_option_data, is_best=True)
    
    # Store other flights
    other_flights = search_data.get("other_flights", [])
    for flight_option_data in other_flights:
        _store_flight_option(db, search.search_id, flight_option_data, is_best=False)
    
    # Store price insights
    price_insights_data = search_data.get("price_insights")
    if price_insights_data:
        # Handle nested typical_price_range structure
        typical_range = price_insights_data.get("typical_price_range", {})
        typical_low = typical_range.get("low_price") if typical_range else price_insights_data.get("typical_low_price")
        typical_high = typical_range.get("high_price") if typical_range else price_insights_data.get("typical_high_price")
        
        price_insight = PriceInsight(
            search_id=search.search_id,
            lowest_price=price_insights_data.get("lowest_price"),
            price_level=price_insights_data.get("price_level"),
            typical_low_price=typical_low,
            typical_high_price=typical_high,
        )
        db.add(price_insight)
        db.flush()
        
        # Store price history
        price_history_data = price_insights_data.get("price_history", [])
        for history_item in price_history_data:
            try:
                iso_date_str = history_item.get("iso_date")
                if iso_date_str:
                    # Handle both ISO format strings and datetime objects
                    if isinstance(iso_date_str, str):
                        iso_date = datetime.fromisoformat(iso_date_str.replace("Z", "+00:00"))
                    else:
                        iso_date = iso_date_str
                    
                    history = PriceHistory(
                        insight_id=price_insight.insight_id,
                        price=history_item.get("price"),
                        iso_date=iso_date,
                    )
                    db.add(history)
            except Exception as e:
                log.warning("Failed to parse price history item: %s, error: %s", history_item, str(e))
                continue
    
    return search.search_id


def _store_flight_option(db, search_id: int, flight_option_data: Dict[str, Any], is_best: bool):
    """Store a flight option (best or other)"""
    carbon_emissions = flight_option_data.get("carbon_emissions", {})
    
    flight_option = FlightOption(
        search_id=search_id,
        is_best_flight=is_best,
        total_duration=flight_option_data.get("total_duration"),
        price=flight_option_data.get("price", 0),
        type=flight_option_data.get("type"),
        airline_logo=flight_option_data.get("airline_logo"),
        departure_token=flight_option_data.get("departure_token"),
        carbon_emission_this_flight=carbon_emissions.get("this_flight"),
        carbon_emission_typical=carbon_emissions.get("typical_for_this_route"),
        carbon_emission_difference_percent=carbon_emissions.get("difference_percent"),
        carbon_emission_lowest_route=carbon_emissions.get("lowest_route"),
    )
    db.add(flight_option)
    db.flush()
    
    # Store option extensions
    extensions = flight_option_data.get("extensions", [])
    for ext_text in extensions:
        if ext_text:
            ext = OptionExtension(
                option_id=flight_option.option_id,
                extension_text=ext_text,
            )
            db.add(ext)
    
    # Store flight segments
    flights = flight_option_data.get("flights", [])
    for idx, flight_segment_data in enumerate(flights):
        departure_airport_data = flight_segment_data.get("departure_airport", {})
        arrival_airport_data = flight_segment_data.get("arrival_airport", {})
        
        departure_airport = _get_or_create_airport_auto(
            db,
            departure_airport_data.get("id", ""),
            departure_airport_data.get("name", ""),
        )
        arrival_airport = _get_or_create_airport_auto(
            db,
            arrival_airport_data.get("id", ""),
            arrival_airport_data.get("name", ""),
        )
        
        detected_extensions = flight_segment_data.get("detected_extensions", {})
        airline_name = flight_segment_data.get("airline", "")
        airline_code = flight_segment_data.get("flight_number", "").split()[0] if flight_segment_data.get("flight_number") else None
        
        airline_auto = _get_or_create_airline_auto(
            db,
            airline_name,
            airline_code,
            flight_segment_data.get("airline_logo"),
        )
        
        departure_date = _parse_date(departure_airport_data.get("date"))
        arrival_date = _parse_date(arrival_airport_data.get("date"))
        departure_time = _parse_time(departure_airport_data.get("time"))
        arrival_time = _parse_time(arrival_airport_data.get("time"))
        
        if departure_time is None:
            departure_time = time(0, 0)
        if arrival_time is None:
            arrival_time = time(0, 0)
        
        if not departure_date or not arrival_date:
            log.warning("Skipping flight segment with invalid dates: %s", flight_segment_data)
            continue
        
        flight_segment = FlightSegment(
            option_id=flight_option.option_id,
            segment_order=idx + 1,  # 1-based ordering like the Python script
            departure_airport_iata=departure_airport.iata,
            departure_airport_name=departure_airport_data.get("name", ""),
            departure_date=departure_date,
            departure_time=departure_time,
            arrival_airport_iata=arrival_airport.iata,
            arrival_airport_name=arrival_airport_data.get("name", ""),
            arrival_date=arrival_date,
            arrival_time=arrival_time,
            duration=flight_segment_data.get("duration", 0),
            airplane=flight_segment_data.get("airplane"),
            airline_id=airline_auto.airline_id,
            airline=airline_name,
            airline_logo=flight_segment_data.get("airline_logo"),
            travel_class=flight_segment_data.get("travel_class"),
            flight_number=flight_segment_data.get("flight_number", ""),
            has_in_seat_usb_outlet=detected_extensions.get("has_in_seat_usb_outlet"),
            has_power_and_usb_outlets=detected_extensions.get("has_power_and_usb_outlets"),
            has_on_demand_video=detected_extensions.get("has_on_demand_video"),
            wifi=detected_extensions.get("wifi"),
            seat_type=detected_extensions.get("seat_type"),
            legroom_short=detected_extensions.get("legroom_short"),
            legroom_long=detected_extensions.get("legroom_long"),
            carbon_emission=detected_extensions.get("carbon_emission"),
        )
        db.add(flight_segment)
        db.flush()
        
        # Store segment extensions
        segment_extensions = flight_segment_data.get("extensions", [])
        for ext_text in segment_extensions:
            if ext_text:
                ext = FlightExtension(
                    segment_id=flight_segment.segment_id,
                    extension_text=ext_text,
                )
                db.add(ext)
    
    # Store layovers
    layovers_data = flight_option_data.get("layovers", [])
    for idx, layover_data in enumerate(layovers_data):
        layover_airport_iata = layover_data.get("id") or layover_data.get("airport_iata")
        layover_airport_name = layover_data.get("name") or layover_data.get("airport_name")
        
        if layover_airport_iata:
            # Ensure airport exists
            layover_airport = _get_or_create_airport_auto(
                db,
                layover_airport_iata,
                layover_airport_name or f"Airport {layover_airport_iata}",
            )
            
            layover = Layover(
                option_id=flight_option.option_id,
                layover_order=idx + 1,  # 1-based ordering
                airport_iata=layover_airport.iata,
                airport_name=layover_airport_name or layover_airport.airport_name,
                duration=layover_data.get("duration", 0),
            )
            db.add(layover)


@router.post(
    "/n8n-webhook",
    status_code=status.HTTP_201_CREATED,
    summary="Receive flight search data from n8n webhook",
)
async def receive_n8n_webhook_data(
    request: Request,
    departure_id: str = Query(..., description="Departure airport code"),
    arrival_id: str = Query(..., description="Arrival airport code"),
    airline: str = Query(..., description="Airline code"),
):
    """
    Receive flight search data from n8n webhook and store it in the database.
    
    This endpoint is called by the n8n workflow after it completes a flight search.
    No authentication required as it's called by n8n.
    
    Expected request format:
    POST /n8n-webhook?departure_id=HKG&arrival_id=KIX&airline=CX
    Body: [{"search_parameters": {...}, "best_flights": [...], ...}, ...]
    """
    try:
        # Parse request body
        body = await request.json()
        log.info(
            "Received n8n webhook data: departure_id=%s, arrival_id=%s, airline=%s, data_type=%s, data_length=%s",
            departure_id,
            arrival_id,
            airline,
            type(body).__name__,
            len(body) if isinstance(body, (list, dict)) else "N/A",
        )
        
        # Handle both list and single object
        if isinstance(body, dict):
            data = [body]
        elif isinstance(body, list):
            data = body
        else:
            log.error("Invalid data format received from n8n: %s", type(body))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data must be a list or object",
        )
        
        log.info("Processing %d search data items", len(data))
    except Exception as e:
        log.exception("Failed to parse n8n webhook request body: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse request body: {str(e)}",
        )
    
    with get_db() as db:
        try:
            # Find the auto_search_airline_id based on departure, arrival, and airline
            airline_upper = airline.upper()
            auto_search_airline = db.query(AutoSearchAirline).join(AutoSearchConfig).filter(
                AutoSearchConfig.departure_id == departure_id.upper(),
                AutoSearchConfig.arrival_id == arrival_id.upper(),
            ).join(Airline).filter(
                Airline.code == airline_upper
            ).first()
            
            auto_search_airline_id = auto_search_airline.auto_search_airline_id if auto_search_airline else None
            
            if auto_search_airline_id is None:
                log.warning(
                    "No matching auto_search_airline found for %s -> %s, airline=%s. Storing without link.",
                    departure_id,
                    arrival_id,
                    airline,
                )
            
            search_ids = []
            for idx, search_data in enumerate(data):
                try:
                    log.info("Processing search data item %d/%d", idx + 1, len(data))
                    search_id = _store_flight_search_data(db, search_data, auto_search_airline_id)
                    search_ids.append(search_id)
                    log.info("Successfully stored search with ID: %d", search_id)
                except Exception as e:
                    log.exception("Failed to store search data item %d: %s", idx + 1, str(e))
                    # Continue with other items even if one fails
                continue
            
            if search_ids:
                db.commit()
                log.info("Committed %d search records to database", len(search_ids))
            else:
                log.warning("No search records were successfully stored")
                db.rollback()
            
            log.info(
                "Stored %d flight searches from n8n webhook for %s -> %s, airline=%s",
                len(search_ids),
                departure_id,
                arrival_id,
                airline,
            )
            
            return {"success": True, "search_ids": search_ids, "count": len(search_ids)}
        except Exception as e:
            db.rollback()
            log.exception("Failed to store n8n webhook data: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store flight search data: {str(e)}",
            )


@router.get(
    "/auto-search",
    response_model=List[AutoSearchListResponse],
    summary="List all auto flight searches",
)
async def list_auto_flight_searches(user=Depends(get_verified_user)):
    """List all auto flight searches for the current user"""
    with get_db() as db:
        try:
            auto_searches = db.query(AutoSearchConfig).order_by(AutoSearchConfig.created_at.desc()).all()
            
            results = []
            for auto_search in auto_searches:
                # Get associated airlines
                auto_search_airlines = db.query(AutoSearchAirline).filter(
                    AutoSearchAirline.auto_search_id == auto_search.auto_search_id
                ).all()
                
                # Get airline models directly from database
                airline_models = []
                for asa in auto_search_airlines:
                    airline_record = db.query(Airline).filter(Airline.airline_id == asa.airline_id).first()
                    if airline_record:
                        airline_models.append(AirlineModel.model_validate(airline_record))
                
                results.append(AutoSearchListResponse(
                    auto_search_id=auto_search.auto_search_id,
                    departure_id=auto_search.departure_id,
                    arrival_id=auto_search.arrival_id,
                    travel_class=auto_search.travel_class,
                    is_direct=auto_search.is_direct,
                    return_trip_duration=auto_search.return_trip_duration,
                    created_at=auto_search.created_at,
                    updated_at=auto_search.updated_at,
                    airlines=airline_models,
                ))
            
            return results
        except Exception as e:
            log.exception("Failed to list auto flight searches: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list auto flight searches: {str(e)}",
            )


@router.delete(
    "/auto-search/{auto_search_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an auto flight search",
)
async def delete_auto_flight_search(
    auto_search_id: int,
    user=Depends(get_verified_user),
):
    """
    Delete an auto flight search and all associated data.
    
    This will delete:
    - auto_search_config record
    - auto_search_airline records (cascade)
    - searches linked to those auto_search_airline records
    - flight_options, flight_segments, layovers, extensions (cascade from searches)
    - price_insights and price_history (cascade from searches)
    - search_airports (cascade from searches)
    """
    with get_db() as db:
        try:
            auto_search = db.query(AutoSearchConfig).filter(
                AutoSearchConfig.auto_search_id == auto_search_id
            ).first()
            
            if not auto_search:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Auto flight search not found",
                )
            
            # Get all auto_search_airline records for this auto_search
            auto_search_airlines = db.query(AutoSearchAirline).filter(
                AutoSearchAirline.auto_search_id == auto_search_id
            ).all()
            
            # Get all search_ids linked to these auto_search_airline records
            auto_search_airline_ids = [asa.auto_search_airline_id for asa in auto_search_airlines]
            search_ids = []
            
            if auto_search_airline_ids:
                # Find all searches linked to these auto_search_airline records
                searches_to_delete = db.query(Search).filter(
                    Search.auto_search_airline_id.in_(auto_search_airline_ids)
                ).all()
                
                search_ids = [s.search_id for s in searches_to_delete]
                
                if search_ids:
                    log.info(
                        "Deleting %d searches and related data for auto search %d",
                        len(search_ids),
                        auto_search_id,
                    )
                    
                    # Delete searches (cascades will handle related data):
                    # - flight_options (CASCADE)
                    # - flight_segments (CASCADE from flight_options)
                    # - layovers (CASCADE from flight_options)
                    # - option_extensions (CASCADE from flight_options)
                    # - flight_extensions (CASCADE from flight_segments)
                    # - price_insights (CASCADE)
                    # - price_history (CASCADE from price_insights)
                    # - search_airports (CASCADE)
                    for search in searches_to_delete:
                        db.delete(search)
            
            # Delete auto_search_config (this will cascade delete auto_search_airline records)
            db.delete(auto_search)
            db.commit()
            
            log.info(
                "Deleted auto flight search %d and all associated data (%d searches, %d airlines)",
                auto_search_id,
                len(search_ids) if auto_search_airline_ids else 0,
                len(auto_search_airlines),
            )
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            log.exception("Failed to delete auto flight search %d: %s", auto_search_id, str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete auto flight search",
            )
