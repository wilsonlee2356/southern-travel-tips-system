"""JSON Extractor Utility

This module provides functionality to extract JSON objects from strings
by locating the first opening brace '{' to the last closing brace '}'.
"""

import logging

log = logging.getLogger(__name__)


def extract_json(text: str) -> str | None:
    """
    Extract JSON from a string by finding the substring from the first '{' to the last '}'.
    
    Args:
        text: The input string that may contain JSON
        
    Returns:
        The extracted JSON string, or None if no JSON is found
        
    Examples:
        >>> extract_json("Some text {\\"key\\": \\"value\\"} more text")
        '{\"key\": \"value\"}'
        
        >>> extract_json("No JSON here")
        None
    """
    if not text or not isinstance(text, str):
        return None
    
    # Find the first opening brace
    start_index = text.find('{')
    if start_index == -1:
        return None
    
    # Find the last closing brace
    end_index = text.rfind('}')
    if end_index == -1 or end_index < start_index:
        return None
    
    # Extract the substring from first '{' to last '}'
    json_string = text[start_index:end_index + 1]
    
    return json_string

