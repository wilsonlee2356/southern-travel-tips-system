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
    """Response for auto flight search creation and refresh"""
    success: bool = True
    message: str = "Auto flight search initiated. n8n workflow will handle the search."
    airlines: List[AirlineModel] = Field(default_factory=list)
    auto_search_id: Optional[int] = None
    departure_id: Optional[str] = None
    arrival_id: Optional[str] = None
    travel_class: Optional[int] = None
    is_direct: Optional[bool] = None
    direct_flight: Optional[bool] = None  # Alias for is_direct for frontend compatibility
    return_trip_duration: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


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
    auto_search_id: Optional[int] = None,
) -> None:
    """
    Call n8n webhook API for each airline when a new auto search is created or refreshed.
    
    URL format: https://n8n.ssl-labs.ai/webhook/f56d4963-08b0-4c21-97c7-be28249e32d8/auto_search/{departure_id}/{arrival_id}/{is_direct}/{airline}/{trip_duration}
    
    Args:
        departure_id: Departure airport code (e.g., HKG)
        arrival_id: Arrival airport code (e.g., KIX)
        is_direct: Whether to search for direct flights only
        airline_codes: List of airline codes to call webhook for
        trip_duration: Trip duration in days (required, 1-365)
        auto_search_id: Optional auto_search_id to use for finding auto_search_airline_id
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
            
            # Log the response status and body
            response_text = response.text if response.text else ""
            response_length = len(response_text)
            log.info(
                "n8n webhook response for airline %s: status=%d, response_length=%d",
                airline_code_upper,
                response.status_code,
                response_length,
            )
            
            # Log first and last part of response to verify it's complete
            if response_length > 0:
                preview_start = response_text[:200] if len(response_text) > 200 else response_text
                preview_end = response_text[-200:] if len(response_text) > 200 else ""
                log.debug(
                    "n8n response preview (first 200 chars): %s",
                    preview_start,
                )
                if preview_end:
                    log.debug(
                        "n8n response preview (last 200 chars): %s",
                        preview_end,
                    )
            
            # Check for HTTP errors
            try:
                response.raise_for_status()
            except requests.HTTPError as http_err:
                log.error(
                    "n8n webhook returned HTTP error for airline %s: status=%d, response=%s",
                    airline_code_upper,
                    response.status_code,
                    response_text[:1000] if response_text else "No response body",
                )
                log.exception("HTTP error details: %s", str(http_err))
                continue
            
            # Check if response is empty
            if not response_text or not response_text.strip():
                log.error(
                    "n8n webhook returned empty response for airline %s: %s -> %s",
                    airline_code_upper,
                    departure_id,
                    arrival_id,
                )
                continue
            
            # Parse and store the flight data if present
            try:
                # Check response format before parsing
                if response_length > 0:
                    first_char = response_text.strip()[0] if response_text.strip() else ""
                    last_char = response_text.strip()[-1] if response_text.strip() else ""
                    opening_brackets = response_text.count('[')
                    closing_brackets = response_text.count(']')
                    log.info(
                        "n8n response format check for airline %s: first_char='%s', last_char='%s', brackets: [=%d, ]=%d",
                        airline_code_upper,
                        first_char,
                        last_char,
                        opening_brackets,
                        closing_brackets,
                    )
                
                flight_data = response.json()
                log.info(
                    "Parsed JSON from n8n for airline %s: type=%s, is_list=%s",
                    airline_code_upper,
                    type(flight_data).__name__,
                    isinstance(flight_data, list),
                )
                
                # Handle both single object and list
                if isinstance(flight_data, dict):
                    data_list = [flight_data]
                    log.warning(
                        "n8n returned a single dict object for airline %s (expected list). Converting to list with 1 item. Response length was %d chars.",
                        airline_code_upper,
                        response_length,
                    )
                elif isinstance(flight_data, list):
                    data_list = flight_data
                    log.info(
                        "n8n returned a list with %d items for airline %s (response_length=%d chars)",
                        len(flight_data),
                        airline_code_upper,
                        response_length,
                    )
                    # Log first few items to verify we got them all
                    for idx in range(min(3, len(flight_data))):
                        item = flight_data[idx]
                        if isinstance(item, dict):
                            sp = item.get("search_parameters", {})
                            log.debug(
                                "  List item %d/%d: %s -> %s, dates: %s / %s",
                                idx + 1,
                                len(flight_data),
                                sp.get("departure_id", "N/A"),
                                sp.get("arrival_id", "N/A"),
                                sp.get("outbound_date", "N/A"),
                                sp.get("return_date", "N/A"),
                            )
                else:
                    log.error(
                        "Unexpected data format from n8n for airline %s: expected dict or list, got %s. Response preview: %s",
                        airline_code_upper,
                        type(flight_data).__name__,
                        str(flight_data)[:500],
                    )
                    continue

                log.info(
                    "Parsed n8n response for airline %s: received %d search items to process",
                    airline_code_upper,
                    len(data_list),
                )

                # Validate and log data structure for each item
                for idx, search_data in enumerate(data_list):
                    if not isinstance(search_data, dict):
                        log.error(
                            "Invalid search_data item %d for airline %s: expected dict, got %s",
                            idx,
                            airline_code_upper,
                            type(search_data).__name__,
                        )
                        continue
                    
                    # Check for missing or null critical fields
                    search_params = search_data.get("search_parameters")
                    best_flights = search_data.get("best_flights")
                    other_flights = search_data.get("other_flights")
                    
                    if not search_params:
                        log.error(
                            "Missing search_parameters in n8n response for airline %s (item %d). Available keys: %s",
                            airline_code_upper,
                            idx,
                            list(search_data.keys()),
                        )
                        continue
                    
                    # Log warnings for missing flight data
                    if not best_flights and not other_flights:
                        log.warning(
                            "No flight data returned from n8n for airline %s (item %d): best_flights=%s, other_flights=%s. Search params: %s",
                            airline_code_upper,
                            idx,
                            best_flights,
                            other_flights,
                            search_params,
                        )
                    elif best_flights is None and other_flights is None:
                        log.warning(
                            "best_flights and other_flights are both None (not empty list) for airline %s (item %d)",
                            airline_code_upper,
                            idx,
                        )
                    else:
                        best_count = len(best_flights) if isinstance(best_flights, list) else 0
                        other_count = len(other_flights) if isinstance(other_flights, list) else 0
                        log.info(
                            "n8n returned flight data for airline %s (item %d): best_flights=%d, other_flights=%d",
                            airline_code_upper,
                            idx,
                            best_count,
                            other_count,
                        )

                # Store the data in database
                with get_db() as db:
                    try:
                        # Find the auto_search_airline_id
                        if auto_search_id is not None:
                            # Use auto_search_id if provided (more reliable for refresh)
                            auto_search_airline = db.query(AutoSearchAirline).filter(
                                AutoSearchAirline.auto_search_id == auto_search_id
                            ).join(Airline).filter(
                                Airline.code == airline_code_upper
                            ).first()
                        else:
                            # Fall back to searching by departure/arrival (for backward compatibility)
                            auto_search_airline = db.query(AutoSearchAirline).join(AutoSearchConfig).filter(
                                AutoSearchConfig.departure_id == departure_id.upper(),
                                AutoSearchConfig.arrival_id == arrival_id.upper(),
                            ).join(Airline).filter(
                                Airline.code == airline_code_upper
                            ).first()
                        
                        auto_search_airline_id = auto_search_airline.auto_search_airline_id if auto_search_airline else None
                        
                        if auto_search_airline_id is None:
                            log.warning(
                                "No matching auto_search_airline found for %s -> %s, airline=%s%s. Storing without link.",
                                departure_id,
                                arrival_id,
                                airline_code_upper,
                                f", auto_search_id={auto_search_id}" if auto_search_id else "",
                            )
                        
                        search_ids = []
                        errors = []
                        log.info(
                            "Starting to store %d search items for airline %s",
                            len(data_list),
                            airline_code_upper,
                        )
                        
                        for idx, search_data in enumerate(data_list):
                            try:
                                search_params = search_data.get("search_parameters", {})
                                outbound_date = search_params.get("outbound_date", "N/A")
                                return_date = search_params.get("return_date", "N/A")
                                
                                log.info(
                                    "Processing search data item %d/%d for airline %s: %s -> %s, dates: %s / %s",
                                    idx + 1,
                                    len(data_list),
                                    airline_code_upper,
                                    search_params.get("departure_id", "N/A"),
                                    search_params.get("arrival_id", "N/A"),
                                    outbound_date,
                                    return_date,
                                )
                                
                                search_id = _store_flight_search_data(db, search_data, auto_search_airline_id)
                                search_ids.append(search_id)
                                log.info(
                                    "Successfully stored search item %d/%d with ID: %d (dates: %s / %s)",
                                    idx + 1,
                                    len(data_list),
                                    search_id,
                                    outbound_date,
                                    return_date,
                                )
                            except ValueError as ve:
                                error_msg = f"Validation error in item {idx + 1}/{len(data_list)}: {str(ve)}"
                                log.error(error_msg)
                                errors.append(error_msg)
                                # Continue processing other items
                                continue
                            except Exception as e:
                                error_msg = f"Failed to store search data item {idx + 1}/{len(data_list)}: {str(e)}"
                                log.exception(error_msg)
                                errors.append(error_msg)
                                # Continue processing other items
                                continue

                        log.info(
                            "Finished processing all %d search items for airline %s. Successfully stored: %d, Errors: %d",
                            len(data_list),
                            airline_code_upper,
                            len(search_ids),
                            len(errors),
                        )

                        if search_ids:
                            db.commit()
                            log.info(
                                "Committed %d flight searches to database for %s -> %s, airline=%s",
                                len(search_ids),
                                departure_id,
                                arrival_id,
                                airline_code_upper,
                            )
                            if errors:
                                log.warning(
                                    "Some errors occurred while processing n8n response for airline %s (%d errors): %s",
                                    airline_code_upper,
                                    len(errors),
                                    "; ".join(errors[:5]),  # Show first 5 errors
                                )
                        else:
                            log.error(
                                "No search records were successfully stored from n8n response for airline %s. All %d items failed. Errors: %s",
                                airline_code_upper,
                                len(data_list),
                                "; ".join(errors[:10]) if errors else "Unknown error",
                            )
                            db.rollback()
                    except Exception as e:
                        db.rollback()
                        log.exception("Failed to store n8n response data for airline %s: %s", airline_code_upper, str(e))
                        
            except ValueError as json_err:
                log.error(
                    "Failed to parse JSON from n8n response for airline %s: %s. Response text (first 1000 chars): %s",
                    airline_code_upper,
                    str(json_err),
                    response.text[:1000] if response.text else "No response body",
                )
            except Exception as e:
                log.exception(
                    "Unexpected error processing n8n response for airline %s: %s",
                    airline_code_upper,
                    str(e),
                )
            
        except requests.RequestException as req_err:
            log.error(
                "n8n webhook call failed for airline %s: %s -> %s. Error: %s",
                airline_code_upper,
                departure_id,
                arrival_id,
                str(req_err),
            )
            log.exception("Request exception details:")
        except Exception as e:
            log.exception(
                "Unexpected error calling n8n webhook for airline %s: %s -> %s. Error: %s",
                airline_code_upper,
                departure_id,
                arrival_id,
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
        auto_search_id=auto_search_id,
    )

    log.info(
        "Auto flight search created for user %s: %s -> %s, airlines=%s",
        user.id,
        payload.from_place,
        payload.to_place,
        airline_codes,
    )

    # Fetch the created auto search config to return full data
    with get_db() as db:
        auto_search_config = db.query(AutoSearchConfig).filter(
            AutoSearchConfig.auto_search_id == auto_search_id
        ).first()
        
        if auto_search_config:
            return AutoFlightSearchResponse(
                success=True,
                message="Auto flight search initiated. n8n workflow will handle the search.",
                airlines=airline_models,
                auto_search_id=auto_search_config.auto_search_id,
                departure_id=auto_search_config.departure_id,
                arrival_id=auto_search_config.arrival_id,
                travel_class=auto_search_config.travel_class,
                is_direct=auto_search_config.is_direct,
                direct_flight=auto_search_config.is_direct,
                return_trip_duration=auto_search_config.return_trip_duration,
                created_at=auto_search_config.created_at,
                updated_at=auto_search_config.updated_at,
            )
    
    # Fallback if auto_search_config not found (shouldn't happen)
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
    has_search_params = "search_parameters" in search_data
    has_best_flights = "best_flights" in search_data
    has_other_flights = "other_flights" in search_data
    
    log.info("Storing flight search data: has_search_params=%s, has_best_flights=%s, has_other_flights=%s",
             has_search_params,
             has_best_flights,
             has_other_flights)
    
    search_params = search_data.get("search_parameters", {})
    if not search_params:
        log.error("Missing search_parameters in search_data. Available keys: %s", list(search_data.keys()))
        raise ValueError("Missing search_parameters in search data")
    
    # Check for null/empty flight data
    best_flights = search_data.get("best_flights")
    other_flights = search_data.get("other_flights")
    
    if best_flights is None:
        log.warning("best_flights is None (not present or explicitly null) in search_data")
    elif isinstance(best_flights, list) and len(best_flights) == 0:
        log.warning("best_flights is an empty list in search_data")
    elif not isinstance(best_flights, list):
        log.warning("best_flights is not a list: type=%s, value=%s", type(best_flights).__name__, str(best_flights)[:200])
    
    if other_flights is None:
        log.warning("other_flights is None (not present or explicitly null) in search_data")
    elif isinstance(other_flights, list) and len(other_flights) == 0:
        log.warning("other_flights is an empty list in search_data")
    elif not isinstance(other_flights, list):
        log.warning("other_flights is not a list: type=%s, value=%s", type(other_flights).__name__, str(other_flights)[:200])
    
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
    best_flights_raw = search_data.get("best_flights")
    if best_flights_raw is None:
        log.warning("best_flights is None for search_id=%d, skipping best flights storage", search.search_id)
        best_flights = []
    elif not isinstance(best_flights_raw, list):
        log.error("best_flights is not a list (type=%s) for search_id=%d, skipping best flights storage", 
                 type(best_flights_raw).__name__, search.search_id)
        best_flights = []
    else:
        best_flights = best_flights_raw
    
    best_flight_count = 0
    for idx, flight_option_data in enumerate(best_flights):
        try:
            if not isinstance(flight_option_data, dict):
                log.error("best_flights[%d] is not a dict (type=%s) for search_id=%d, skipping", 
                         idx, type(flight_option_data).__name__, search.search_id)
                continue
            _store_flight_option(db, search.search_id, flight_option_data, is_best=True)
            best_flight_count += 1
        except Exception as e:
            log.exception("Failed to store best_flights[%d] for search_id=%d: %s", idx, search.search_id, str(e))
            continue
    
    if best_flight_count > 0:
        log.info("Stored %d best flights for search_id=%d", best_flight_count, search.search_id)
    
    # Store other flights
    other_flights_raw = search_data.get("other_flights")
    if other_flights_raw is None:
        log.warning("other_flights is None for search_id=%d, skipping other flights storage", search.search_id)
        other_flights = []
    elif not isinstance(other_flights_raw, list):
        log.error("other_flights is not a list (type=%s) for search_id=%d, skipping other flights storage", 
                 type(other_flights_raw).__name__, search.search_id)
        other_flights = []
    else:
        other_flights = other_flights_raw
    
    other_flight_count = 0
    for idx, flight_option_data in enumerate(other_flights):
        try:
            if not isinstance(flight_option_data, dict):
                log.error("other_flights[%d] is not a dict (type=%s) for search_id=%d, skipping", 
                         idx, type(flight_option_data).__name__, search.search_id)
                continue
            _store_flight_option(db, search.search_id, flight_option_data, is_best=False)
            other_flight_count += 1
        except Exception as e:
            log.exception("Failed to store other_flights[%d] for search_id=%d: %s", idx, search.search_id, str(e))
            continue
    
    if other_flight_count > 0:
        log.info("Stored %d other flights for search_id=%d", other_flight_count, search.search_id)
    
    # Log summary
    if best_flight_count == 0 and other_flight_count == 0:
        log.warning("No flight options stored for search_id=%d (best_flights=%d items, other_flights=%d items)", 
                   search.search_id, len(best_flights), len(other_flights))
    
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


@router.get(
    "/auto-search/{auto_search_id}/results",
    summary="Get flight search results for an auto search",
)
async def get_auto_flight_search_results(
    auto_search_id: int,
    user=Depends(get_verified_user),
):
    """
    Get all flight search results (searches, flight_options, segments, etc.) for an auto search.
    
    Returns a comprehensive view of all stored flight data for the given auto_search_id.
    """
    with get_db() as db:
        try:
            # Verify auto search exists
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
            
            auto_search_airline_ids = [asa.auto_search_airline_id for asa in auto_search_airlines]
            
            if not auto_search_airline_ids:
                return {
                    "auto_search_id": auto_search_id,
                    "searches": [],
                    "total_searches": 0,
                    "total_flight_options": 0,
                }
            
            # Get all searches linked to these auto_search_airline records
            searches = db.query(Search).filter(
                Search.auto_search_airline_id.in_(auto_search_airline_ids)
            ).order_by(Search.created_at.desc()).all()
            
            results = []
            total_flight_options = 0
            
            for search in searches:
                # Get flight options for this search
                flight_options = db.query(FlightOption).filter(
                    FlightOption.search_id == search.search_id
                ).order_by(FlightOption.is_best_flight.desc(), FlightOption.price.asc()).all()
                
                total_flight_options += len(flight_options)
                
                flight_options_data = []
                for option in flight_options:
                    # Get flight segments
                    segments = db.query(FlightSegment).filter(
                        FlightSegment.option_id == option.option_id
                    ).order_by(FlightSegment.segment_order.asc()).all()
                    
                    # Get layovers
                    layovers = db.query(Layover).filter(
                        Layover.option_id == option.option_id
                    ).order_by(Layover.layover_order.asc()).all()
                    
                    # Get option extensions
                    option_extensions = db.query(OptionExtension).filter(
                        OptionExtension.option_id == option.option_id
                    ).all()
                    
                    segments_data = []
                    for segment in segments:
                        # Get segment extensions
                        segment_extensions = db.query(FlightExtension).filter(
                            FlightExtension.segment_id == segment.segment_id
                        ).all()
                        
                        segments_data.append({
                            "segment_id": segment.segment_id,
                            "segment_order": segment.segment_order,
                            "departure_airport_iata": segment.departure_airport_iata,
                            "departure_airport_name": segment.departure_airport_name,
                            "departure_date": str(segment.departure_date),
                            "departure_time": str(segment.departure_time),
                            "arrival_airport_iata": segment.arrival_airport_iata,
                            "arrival_airport_name": segment.arrival_airport_name,
                            "arrival_date": str(segment.arrival_date),
                            "arrival_time": str(segment.arrival_time),
                            "duration": segment.duration,
                            "airplane": segment.airplane,
                            "airline_id": segment.airline_id,
                            "airline": segment.airline,
                            "airline_logo": segment.airline_logo,
                            "travel_class": segment.travel_class,
                            "flight_number": segment.flight_number,
                            "is_overnight": segment.is_overnight,
                            "extensions": [ext.extension_text for ext in segment_extensions],
                            "has_in_seat_usb_outlet": segment.has_in_seat_usb_outlet,
                            "has_power_and_usb_outlets": segment.has_power_and_usb_outlets,
                            "has_on_demand_video": segment.has_on_demand_video,
                            "wifi": segment.wifi,
                            "seat_type": segment.seat_type,
                            "legroom_short": segment.legroom_short,
                            "legroom_long": segment.legroom_long,
                            "carbon_emission": segment.carbon_emission,
                        })
                    
                    layovers_data = [{
                        "layover_id": layover.layover_id,
                        "layover_order": layover.layover_order,
                        "airport_iata": layover.airport_iata,
                        "airport_name": layover.airport_name,
                        "duration": layover.duration,
                    } for layover in layovers]
                    
                    flight_options_data.append({
                        "option_id": option.option_id,
                        "is_best_flight": option.is_best_flight,
                        "total_duration": option.total_duration,
                        "price": option.price,
                        "type": option.type,
                        "airline_logo": option.airline_logo,
                        "departure_token": option.departure_token,
                        "carbon_emission_this_flight": option.carbon_emission_this_flight,
                        "carbon_emission_typical": option.carbon_emission_typical,
                        "carbon_emission_difference_percent": option.carbon_emission_difference_percent,
                        "carbon_emission_lowest_route": option.carbon_emission_lowest_route,
                        "extensions": [ext.extension_text for ext in option_extensions],
                        "segments": segments_data,
                        "layovers": layovers_data,
                    })
                
                # Get price insights
                price_insight = db.query(PriceInsight).filter(
                    PriceInsight.search_id == search.search_id
                ).first()
                
                price_insight_data = None
                if price_insight:
                    # Get price history
                    price_history = db.query(PriceHistory).filter(
                        PriceHistory.insight_id == price_insight.insight_id
                    ).order_by(PriceHistory.iso_date.asc()).all()
                    
                    price_insight_data = {
                        "insight_id": price_insight.insight_id,
                        "lowest_price": price_insight.lowest_price,
                        "price_level": price_insight.price_level,
                        "typical_low_price": price_insight.typical_low_price,
                        "typical_high_price": price_insight.typical_high_price,
                        "price_history": [{
                            "history_id": ph.history_id,
                            "price": ph.price,
                            "iso_date": str(ph.iso_date),
                        } for ph in price_history],
                    }
                
                results.append({
                    "search_id": search.search_id,
                    "engine": search.engine,
                    "departure_id": search.departure_id,
                    "arrival_id": search.arrival_id,
                    "currency": search.currency,
                    "outbound_date": str(search.outbound_date),
                    "return_date": str(search.return_date) if search.return_date else None,
                    "flight_type": search.flight_type,
                    "travel_class": search.travel_class,
                    "stops": search.stops,
                    "adults": search.adults,
                    "children": search.children,
                    "infants_in_seat": search.infants_in_seat,
                    "infants_on_lap": search.infants_on_lap,
                    "included_airlines": search.included_airlines,
                    "created_at": str(search.created_at),
                    "flight_options": flight_options_data,
                    "price_insight": price_insight_data,
                })
            
            log.info(
                "Retrieved %d searches with %d total flight options for auto_search_id=%d",
                len(results),
                total_flight_options,
                auto_search_id,
            )
            
            return {
                "auto_search_id": auto_search_id,
                "searches": results,
                "total_searches": len(results),
                "total_flight_options": total_flight_options,
            }
            
        except HTTPException:
            raise
        except Exception as e:
            log.exception("Failed to get auto flight search results: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get auto flight search results: {str(e)}",
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


@router.post(
    "/auto-search/{auto_search_id}/refresh",
    response_model=AutoFlightSearchResponse,
    summary="Refresh an auto flight search",
)
async def refresh_auto_flight_search(
    auto_search_id: int,
    user=Depends(get_verified_user),
):
    """
    Refresh an auto flight search by calling n8n API again and updating the database.
    
    This will:
    1. Delete all existing search data for this auto search
    2. Call n8n webhook again with the same parameters
    3. Store the new search data in the database
    
    The auto_search_config and auto_search_airline records are preserved.
    """
    airlines_table = AirlinesTable()
    
    with get_db() as db:
        try:
            # Get the auto search config
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
            
            if not auto_search_airlines:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No airlines configured for this auto search",
                )
            
            # Get airline codes and models
            airline_codes = []
            airline_models = []
            for asa in auto_search_airlines:
                airline = airlines_table.get(asa.airline_id)
                if airline:
                    if airline.code:
                        airline_codes.append(airline.code)
                    airline_models.append(airline)
            
            if not airline_codes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No valid airline codes found for this auto search",
                )
            
            # Get all search_ids linked to these auto_search_airline records
            auto_search_airline_ids = [asa.auto_search_airline_id for asa in auto_search_airlines]
            
            # Delete existing searches (but keep the config and airline links)
            if auto_search_airline_ids:
                searches_to_delete = db.query(Search).filter(
                    Search.auto_search_airline_id.in_(auto_search_airline_ids)
                ).all()
                
                if searches_to_delete:
                    log.info(
                        "Deleting %d existing searches before refresh for auto search %d",
                        len(searches_to_delete),
                        auto_search_id,
                    )
                    
                    # Delete searches (cascades will handle related data)
                    for search in searches_to_delete:
                        db.delete(search)
                    db.commit()
            
            # Update the updated_at timestamp
            auto_search.updated_at = datetime.utcnow()
            db.commit()
            
            log.info(
                "Refreshing auto flight search %d: %s -> %s, airlines=%s",
                auto_search_id,
                auto_search.departure_id,
                auto_search.arrival_id,
                airline_codes,
            )
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            log.exception("Failed to prepare refresh for auto flight search %d: %s", auto_search_id, str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to prepare refresh for auto flight search",
            )
    
    # Call n8n webhook again with the same parameters
    _call_n8n_webhook_for_airlines(
        departure_id=auto_search.departure_id,
        arrival_id=auto_search.arrival_id,
        is_direct=auto_search.is_direct,
        airline_codes=airline_codes,
        trip_duration=auto_search.return_trip_duration,
        auto_search_id=auto_search_id,
    )
    
    # Return the updated auto search config
    with get_db() as db:
        try:
            auto_search_updated = db.query(AutoSearchConfig).filter(
                AutoSearchConfig.auto_search_id == auto_search_id
            ).first()
            
            if not auto_search_updated:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Auto flight search not found after refresh",
                )
            
            return AutoFlightSearchResponse(
                success=True,
                message="Auto flight search refreshed successfully",
                auto_search_id=auto_search_updated.auto_search_id,
                departure_id=auto_search_updated.departure_id,
                arrival_id=auto_search_updated.arrival_id,
                travel_class=auto_search_updated.travel_class,
                is_direct=auto_search_updated.is_direct,
                direct_flight=auto_search_updated.is_direct,  # For frontend compatibility
                return_trip_duration=auto_search_updated.return_trip_duration,
                created_at=auto_search_updated.created_at,
                updated_at=auto_search_updated.updated_at,
                airlines=airline_models,
            )
        except HTTPException:
            raise
        except Exception as e:
            log.exception("Failed to fetch auto flight search after refresh: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch auto flight search after refresh",
            )
