"""Prompt construction for MCP workflow"""

from typing import List, Optional


def build_system_prompt(
    departure: str,
    destination: str,
    airlines: List[str],
    return_trip_days: Optional[int] = None,
    travel_class: str = "economy",
) -> str:
    """
    Build the system prompt for the AI agent.

    Args:
        departure: Departure airport code
        destination: Destination airport code
        airlines: List of airline codes
        return_trip_days: Optional number of days for return trip
        travel_class: Travel class

    Returns:
        System prompt string
    """
    airline_list = ", ".join(airlines)
    travel_class_label = {
        "economy": "Economy",
        "premium_economy": "Premium Economy",
        "business": "Business",
        "first": "First Class",
    }.get(travel_class.lower(), "Economy")

    return_trip_text = f" with {return_trip_days} days return trip" if return_trip_days else ""

    prompt = f"""You are an AI assistant helping to find cheap flight tickets. Your task is to search for flights from {departure} to {destination} on {airline_list} airlines{return_trip_text} in {travel_class_label} class.

WORKFLOW:
1. Start by using google_ai_mode tool to get a big picture of which periods will have cheap ticket prices. Use SIMPLE SENTENCES like: "Give me the cheapest {return_trip_days if return_trip_days else '8'} days return flights of {airlines[0] if airlines else 'CX'} from {departure} to {destination} in the next 6 months, provide all the exact ticket price (all price in HKD), multiple departure and return dates and time"

2. IMPORTANT: Google AI Mode results might not be the most accurate data. You MUST search for real data using google_flight_calendar and google_flight_search tools.

3. Use google_flight_calendar to get an overview of real pricing in the periods that Google AI Mode suggested.

4. Use google_flight_search to get real flight data. Only google_flight_search's data can be stored in the database. You may need to search multiple times with different date combinations to find cheap tickets.

5. Filter out irrelevant tickets - only store flights that match the specified airlines and route.

6. Continue searching until you have found at least a few cheap ticket options, or until you've exhausted reasonable date combinations.

RULES:
- Always use simple sentences when calling google_ai_mode
- Google AI Mode is for initial insights only - always verify with real data
- Only google_flight_search results are stored in the database
- Skip tickets that don't match the specified airlines or route
- Search multiple date combinations if needed to find cheap tickets
- All prices should be in HKD

Available tools:
- google_ai_mode: Get initial insights about cheap periods (use simple sentences)
- google_flight_calendar: Get price overview for date ranges
- google_flight_search: Get detailed flight data and store in database (this is the only tool that stores data)

Start by calling google_ai_mode with a simple sentence query."""

    return prompt


def build_user_prompt(
    departure: str,
    destination: str,
    airlines: List[str],
    return_trip_days: Optional[int] = None,
) -> str:
    """
    Build the user prompt with search parameters.

    Args:
        departure: Departure airport code
        destination: Destination airport code
        airlines: List of airline codes
        return_trip_days: Optional number of days for return trip

    Returns:
        User prompt string
    """
    airline_list = ", ".join(airlines)
    return_trip_text = f" with {return_trip_days} days return trip" if return_trip_days else ""

    return f"Find cheap flights from {departure} to {destination} on {airline_list}{return_trip_text}."

