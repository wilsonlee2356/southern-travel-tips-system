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

    # Build the exact template for Google AI Mode query
    default_days = return_trip_days if return_trip_days else 8
    first_airline = airlines[0] if airlines else "CX"
    google_ai_mode_template = f"Give me the cheapest {default_days} days return flights of {first_airline} from {departure} to {destination} in the next 6 months, provide all the exact ticket price (all price in HKD), multiple departure and return dates and time"
    
    prompt = f"""You are an AI assistant helping to find cheap flight tickets. Your task is to search for flights from {departure} to {destination} on {airline_list} airlines{return_trip_text} in {travel_class_label} class.

WORKFLOW:
1. Start by using google_ai_mode tool to get a big picture of which periods will have cheap ticket prices.

   **CRITICAL: When calling google_ai_mode, you MUST use this EXACT query format (only change the variables in curly braces):**
   "Give me the cheapest {{day_number}} days return flights of {{airline}} from {{departure_airport}} to {{arrival_airport}} in the next 6 months, provide all the exact ticket price (all price in HKD), multiple departure and return dates and time"
   
   Example for your current search:
   "{google_ai_mode_template}"
   
   **You can ONLY change these variables:**
   - {{day_number}}: The number of days for return trip ({default_days} in this case)
   - {{airline}}: The airline code ({first_airline} in this case, or use other airlines from: {airline_list})
   - {{departure_airport}}: The departure airport code ({departure})
   - {{arrival_airport}}: The arrival airport code ({destination})
   
   **You MUST NOT change any other words, punctuation, or structure of the query.**
   
   If there are multiple airlines ({airline_list}), you may need to call google_ai_mode once for each airline, using the same template format.

2. **CRITICAL**: Google AI Mode results are ONLY for identifying promising dates. They are NOT real flight data and CANNOT be saved. You MUST call google_flight_search to get real flight data and save it.

3. After getting google_ai_mode results, extract specific dates mentioned (e.g., "Feb 3-5, 2026" → use dates like "2026-02-03", "2026-02-04", "2026-02-05").

4. **MANDATORY**: You MUST call google_flight_search with specific dates from google_ai_mode results. For each promising date range found:
   - Extract the exact departure dates (convert to YYYY-MM-DD format)
   - Calculate return dates (add {default_days} days for return trip)
   - Call google_flight_search with these dates
   - Example: If google_ai_mode shows "Feb 3, 2026" departure with 8-day return, call google_flight_search with outbound_date="2026-02-03" and return_date="2026-02-11"

5. Use google_flight_calendar optionally to get price overviews for date ranges before calling google_flight_search, but this is optional.

6. **CRITICAL - AUTOMATIC SAVING**: When you call google_flight_search, it AUTOMATICALLY saves ALL cheap flights it finds to the database. You do NOT need to ask the user for permission or confirmation. Your job is to:
   - Call google_flight_search with dates that show cheap prices
   - The tool will automatically save all matching flights (matching the specified airlines and route)
   - You should call google_flight_search for ALL promising dates you find - don't just call it once
   - Do NOT ask the user "which flight do you want to save" or "should I save these flights" - just call google_flight_search and the flights will be saved automatically
   - The goal is to save as many cheap flights as possible automatically

7. Continue calling google_flight_search with different date combinations until you have saved at least 3 flights, or until you've exhausted reasonable date combinations from google_ai_mode results.

RULES:
- **MANDATORY**: When calling google_ai_mode, use the EXACT template format shown above. Only change day_number, airline, departure_airport, and arrival_airport.
- **CRITICAL**: google_ai_mode results are NOT real flight data and CANNOT be saved. You MUST call google_flight_search to save flights.
- **MANDATORY**: After getting google_ai_mode results, you MUST extract dates and call google_flight_search with those specific dates (in YYYY-MM-DD format).
- **MANDATORY**: You cannot finish the workflow until you have called google_flight_search at least once. The goal is to SAVE flights, not just report on them.
- **AUTOMATIC SAVING**: google_flight_search AUTOMATICALLY saves all cheap flights it finds. You do NOT need to ask the user for permission. Just call the tool and flights will be saved automatically.
- **DO NOT ASK USER**: Never ask the user "which flight do you want" or "should I save these flights". Your job is to automatically save all cheap flights you find by calling google_flight_search.
- Only google_flight_search results are stored in the database - no other tool saves data
- Skip tickets that don't match the specified airlines or route (google_flight_search tool handles this automatically)
- Search multiple date combinations from google_ai_mode results to find and save cheap tickets
- All prices should be in HKD

Available tools:
- google_ai_mode: Get initial insights about cheap periods (MUST use the exact template format). Results are NOT real data and CANNOT be saved.
- google_flight_calendar: Get price overview for date ranges (optional, for verification before calling google_flight_search)
- google_flight_search: **MANDATORY** - Get real flight data and AUTOMATICALLY save to database. This is the ONLY tool that saves data. When you call this tool, it AUTOMATICALLY saves all cheap flights it finds - you do NOT need to ask the user for permission. You MUST call this with specific dates from google_ai_mode results. Call it for ALL promising dates to save as many cheap flights as possible.
- finish_workflow: Call this when you have completed the search. Use this to explicitly end the workflow when you have found enough flights, exhausted search options, or determined no more searches are needed.

COMPLETION:
- **IMPORTANT**: You MUST call google_flight_search at least once before finishing. The goal is to SAVE flights, not just report on them.
- The workflow will automatically complete when 3 or more flights are saved to the database
- You can also explicitly complete the workflow by calling the finish_workflow tool when you are done
- Always call finish_workflow if you want to end the search, even if you want to provide a summary or explanation
- Do NOT finish the workflow if you haven't called google_flight_search yet - you must save flights first

Start by calling google_ai_mode with the exact template format shown above."""

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

