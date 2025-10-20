"""
Timezone utility class for destination cities
Returns GMT timezone information for cities in the destination mapper
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

log = logging.getLogger(__name__)

class TimezoneHelper:
    """
    Timezone utility class that provides GMT timezone information for destination cities
    """
    
    # Timezone mapping for cities in the destination mapper
    # Format: "City Name": {"timezone": "timezone_name", "gmt_offset": hours, "dst": bool}
    CITY_TIMEZONES = {
        # Asian cities
        "Tokyo": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Seoul": {"timezone": "Asia/Seoul", "gmt_offset": 9, "dst": False},
        "Bangkok": {"timezone": "Asia/Bangkok", "gmt_offset": 7, "dst": False},
        "Singapore": {"timezone": "Asia/Singapore", "gmt_offset": 8, "dst": False},
        "Hong Kong": {"timezone": "Asia/Hong_Kong", "gmt_offset": 8, "dst": False},
        "Taipei": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Osaka": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},  # Same as Tokyo
        "Kyoto": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},  # Same as Tokyo
        "Shanghai": {"timezone": "Asia/Shanghai", "gmt_offset": 8, "dst": False},
        "Beijing": {"timezone": "Asia/Shanghai", "gmt_offset": 8, "dst": False},  # Same as Shanghai
        "Ho Chi Minh City": {"timezone": "Asia/Ho_Chi_Minh", "gmt_offset": 7, "dst": False},
        "Hanoi": {"timezone": "Asia/Ho_Chi_Minh", "gmt_offset": 7, "dst": False},  # Same as Ho Chi Minh
        "Kuala Lumpur": {"timezone": "Asia/Kuala_Lumpur", "gmt_offset": 8, "dst": False},
        "Manila": {"timezone": "Asia/Manila", "gmt_offset": 8, "dst": False},
        "Jakarta": {"timezone": "Asia/Jakarta", "gmt_offset": 7, "dst": False},
        "Bali": {"timezone": "Asia/Makassar", "gmt_offset": 8, "dst": False},  # Bali uses WITA
        "Phuket": {"timezone": "Asia/Bangkok", "gmt_offset": 7, "dst": False},  # Same as Bangkok
        "Chiang Mai": {"timezone": "Asia/Bangkok", "gmt_offset": 7, "dst": False},  # Same as Bangkok
        "Pattaya": {"timezone": "Asia/Bangkok", "gmt_offset": 7, "dst": False},  # Same as Bangkok
        "Jeju Island": {"timezone": "Asia/Seoul", "gmt_offset": 9, "dst": False},  # Same as Seoul
        
        # Japanese cities and regions (all use JST)
        "Nagoya": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Yokohama": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Fukuoka": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Sapporo": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Sendai": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Hiroshima": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Kobe": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Okinawa": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Hokkaido": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Hakone": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Nara": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Kamakura": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Nikko": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Karuizawa": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Kawaguchiko": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Kanazawa": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Matsumoto": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Nagasaki": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Kumamoto": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Kagoshima": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Aomori": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Akita": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Yamagata": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Fukushima": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Ibaraki": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Tochigi": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Gunma": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Saitama": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Chiba": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Kanagawa": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Niigata": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Toyama": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Ishikawa": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Fukui": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Yamanashi": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Nagano": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Gifu": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Shizuoka": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Aichi": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Mie": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Shiga": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Wakayama": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Tottori": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Shimane": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Okayama": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Yamaguchi": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Tokushima": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Kagawa": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Ehime": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Kochi": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Saga": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Oita": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        "Miyazaki": {"timezone": "Asia/Tokyo", "gmt_offset": 9, "dst": False},
        
        # Taiwanese cities and regions (all use CST)
        "Kaohsiung": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Taichung": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Tainan": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Hsinchu": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Taoyuan": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Keelung": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Chiayi": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Changhua": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Pingtung": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Yilan": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Hualien": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Taitung": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Penghu": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Kinmen": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Matsu": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Nantou": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Yunlin": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "Miaoli": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        "New Taipei": {"timezone": "Asia/Taipei", "gmt_offset": 8, "dst": False},
        
        # European cities
        "Paris": {"timezone": "Europe/Paris", "gmt_offset": 1, "dst": True},
        "London": {"timezone": "Europe/London", "gmt_offset": 0, "dst": True},
        "Rome": {"timezone": "Europe/Rome", "gmt_offset": 1, "dst": True},
        "Barcelona": {"timezone": "Europe/Madrid", "gmt_offset": 1, "dst": True},
        "Amsterdam": {"timezone": "Europe/Amsterdam", "gmt_offset": 1, "dst": True},
        "Berlin": {"timezone": "Europe/Berlin", "gmt_offset": 1, "dst": True},
        "Vienna": {"timezone": "Europe/Vienna", "gmt_offset": 1, "dst": True},
        "Prague": {"timezone": "Europe/Prague", "gmt_offset": 1, "dst": True},
        "Venice": {"timezone": "Europe/Rome", "gmt_offset": 1, "dst": True},  # Same as Rome
        "Florence": {"timezone": "Europe/Rome", "gmt_offset": 1, "dst": True},  # Same as Rome
        "Milan": {"timezone": "Europe/Rome", "gmt_offset": 1, "dst": True},  # Same as Rome
        "Madrid": {"timezone": "Europe/Madrid", "gmt_offset": 1, "dst": True},
        "Lisbon": {"timezone": "Europe/Lisbon", "gmt_offset": 0, "dst": True},
        "Athens": {"timezone": "Europe/Athens", "gmt_offset": 2, "dst": True},
        "Istanbul": {"timezone": "Europe/Istanbul", "gmt_offset": 3, "dst": True},
        "Budapest": {"timezone": "Europe/Budapest", "gmt_offset": 1, "dst": True},
        "Munich": {"timezone": "Europe/Berlin", "gmt_offset": 1, "dst": True},  # Same as Berlin
        "Zurich": {"timezone": "Europe/Zurich", "gmt_offset": 1, "dst": True},
        "Geneva": {"timezone": "Europe/Zurich", "gmt_offset": 1, "dst": True},  # Same as Zurich
        "Edinburgh": {"timezone": "Europe/London", "gmt_offset": 0, "dst": True},  # Same as London
        "Dublin": {"timezone": "Europe/Dublin", "gmt_offset": 0, "dst": True},
        "Copenhagen": {"timezone": "Europe/Copenhagen", "gmt_offset": 1, "dst": True},
        "Stockholm": {"timezone": "Europe/Stockholm", "gmt_offset": 1, "dst": True},
        "Oslo": {"timezone": "Europe/Oslo", "gmt_offset": 1, "dst": True},
        "Helsinki": {"timezone": "Europe/Helsinki", "gmt_offset": 2, "dst": True},
        
        # North American cities
        "New York": {"timezone": "America/New_York", "gmt_offset": -5, "dst": True},
        "Los Angeles": {"timezone": "America/Los_Angeles", "gmt_offset": -8, "dst": True},
        "San Francisco": {"timezone": "America/Los_Angeles", "gmt_offset": -8, "dst": True},  # Same as LA
        "Las Vegas": {"timezone": "America/Los_Angeles", "gmt_offset": -8, "dst": True},  # Same as LA
        "Chicago": {"timezone": "America/Chicago", "gmt_offset": -6, "dst": True},
        "Seattle": {"timezone": "America/Los_Angeles", "gmt_offset": -8, "dst": True},  # Same as LA
        "Boston": {"timezone": "America/New_York", "gmt_offset": -5, "dst": True},  # Same as NYC
        "Miami": {"timezone": "America/New_York", "gmt_offset": -5, "dst": True},  # Same as NYC
        "Vancouver": {"timezone": "America/Vancouver", "gmt_offset": -8, "dst": True},
        "Toronto": {"timezone": "America/Toronto", "gmt_offset": -5, "dst": True},
        "Montreal": {"timezone": "America/Toronto", "gmt_offset": -5, "dst": True},  # Same as Toronto
        "Mexico City": {"timezone": "America/Mexico_City", "gmt_offset": -6, "dst": True},
        "Cancun": {"timezone": "America/Cancun", "gmt_offset": -5, "dst": True},
        
        # Oceania cities
        "Sydney": {"timezone": "Australia/Sydney", "gmt_offset": 10, "dst": True},
        "Melbourne": {"timezone": "Australia/Melbourne", "gmt_offset": 10, "dst": True},
        "Auckland": {"timezone": "Pacific/Auckland", "gmt_offset": 12, "dst": True},
        "Gold Coast": {"timezone": "Australia/Sydney", "gmt_offset": 10, "dst": True},  # Same as Sydney
        "Brisbane": {"timezone": "Australia/Brisbane", "gmt_offset": 10, "dst": False},  # No DST in Queensland
        
        # Middle Eastern cities
        "Dubai": {"timezone": "Asia/Dubai", "gmt_offset": 4, "dst": False},
        "Abu Dhabi": {"timezone": "Asia/Dubai", "gmt_offset": 4, "dst": False},  # Same as Dubai
        "Jerusalem": {"timezone": "Asia/Jerusalem", "gmt_offset": 2, "dst": True},
        "Tel Aviv": {"timezone": "Asia/Jerusalem", "gmt_offset": 2, "dst": True},  # Same as Jerusalem
        
        # African cities
        "Cape Town": {"timezone": "Africa/Johannesburg", "gmt_offset": 2, "dst": False},
        "Johannesburg": {"timezone": "Africa/Johannesburg", "gmt_offset": 2, "dst": False},
        "Marrakech": {"timezone": "Africa/Casablanca", "gmt_offset": 0, "dst": True},
        "Cairo": {"timezone": "Africa/Cairo", "gmt_offset": 2, "dst": True},
        
        # South American cities
        "Rio de Janeiro": {"timezone": "America/Sao_Paulo", "gmt_offset": -3, "dst": True},
        "Sao Paulo": {"timezone": "America/Sao_Paulo", "gmt_offset": -3, "dst": True},
        "Buenos Aires": {"timezone": "America/Argentina/Buenos_Aires", "gmt_offset": -3, "dst": False},
        "Lima": {"timezone": "America/Lima", "gmt_offset": -5, "dst": False},
        "Santiago": {"timezone": "America/Santiago", "gmt_offset": -3, "dst": True},
    }
    
    @classmethod
    def get_timezone_info(cls, city_name: str) -> Optional[Dict[str, Any]]:
        """
        Get timezone information for a city
        
        Args:
            city_name: Name of the city (English name from destination mapper)
            
        Returns:
            Dictionary with timezone information or None if city not found
            Format: {
                "timezone": "timezone_name",
                "gmt_offset": hours_from_gmt,
                "dst": bool_has_daylight_saving,
                "current_gmt_offset": current_offset_including_dst,
                "gmt_string": "GMT+/-X" or "GMT+/-X (DST)"
            }
        """
        if not city_name:
            return None
            
        # Normalize city name (remove extra spaces, handle case)
        normalized_city = city_name.strip()
        
        # Check if city exists in our mapping
        if normalized_city not in cls.CITY_TIMEZONES:
            log.warning(f"City '{city_name}' not found in timezone mapping")
            return None
            
        city_info = cls.CITY_TIMEZONES[normalized_city]
        
        # Calculate current GMT offset (including DST if applicable)
        current_offset = city_info["gmt_offset"]
        gmt_string = f"GMT{current_offset:+d}"
        
        # Add DST indicator if applicable
        if city_info["dst"]:
            gmt_string += " (DST)"
            
        return {
            "timezone": city_info["timezone"],
            "gmt_offset": city_info["gmt_offset"],
            "dst": city_info["dst"],
            "current_gmt_offset": current_offset,
            "gmt_string": gmt_string
        }
    
    @classmethod
    def get_gmt_offset(cls, city_name: str) -> Optional[int]:
        """
        Get GMT offset in hours for a city
        
        Args:
            city_name: Name of the city
            
        Returns:
            GMT offset in hours (positive for east of GMT, negative for west)
        """
        timezone_info = cls.get_timezone_info(city_name)
        return timezone_info["current_gmt_offset"] if timezone_info else None
    
    @classmethod
    def get_gmt_string(cls, city_name: str) -> Optional[str]:
        """
        Get GMT string representation for a city
        
        Args:
            city_name: Name of the city
            
        Returns:
            GMT string like "GMT+9" or "GMT-5 (DST)"
        """
        timezone_info = cls.get_timezone_info(city_name)
        return timezone_info["gmt_string"] if timezone_info else None
    
    @classmethod
    def get_current_time_in_city(cls, city_name: str) -> Optional[Dict[str, Any]]:
        """
        Get current time in a city
        
        Args:
            city_name: Name of the city
            
        Returns:
            Dictionary with current time information or None if city not found
            Format: {
                "city": "city_name",
                "current_time": "YYYY-MM-DD HH:MM:SS",
                "gmt_offset": hours_from_gmt,
                "gmt_string": "GMT+/-X"
            }
        """
        timezone_info = cls.get_timezone_info(city_name)
        if not timezone_info:
            return None
            
        # Calculate current time in the city
        utc_now = datetime.now(timezone.utc)
        city_offset = timedelta(hours=timezone_info["current_gmt_offset"])
        city_time = utc_now + city_offset
        
        return {
            "city": city_name,
            "current_time": city_time.strftime("%Y-%m-%d %H:%M:%S"),
            "gmt_offset": timezone_info["current_gmt_offset"],
            "gmt_string": timezone_info["gmt_string"]
        }
    
    @classmethod
    def list_all_cities(cls) -> list:
        """
        Get list of all cities with timezone information
        
        Returns:
            List of city names
        """
        return list(cls.CITY_TIMEZONES.keys())
    
    @classmethod
    def search_cities(cls, query: str) -> list:
        """
        Search for cities by name (case-insensitive partial match)
        
        Args:
            query: Search query
            
        Returns:
            List of matching city names
        """
        if not query:
            return []
            
        query_lower = query.lower().strip()
        return [
            city for city in cls.CITY_TIMEZONES.keys()
            if query_lower in city.lower()
        ]


# Convenience functions for easy access
def get_city_timezone(city_name: str) -> Optional[Dict[str, Any]]:
    """Get timezone information for a city"""
    return TimezoneHelper.get_timezone_info(city_name)

def get_city_gmt_offset(city_name: str) -> Optional[int]:
    """Get GMT offset for a city"""
    return TimezoneHelper.get_gmt_offset(city_name)

def get_city_gmt_string(city_name: str) -> Optional[str]:
    """Get GMT string for a city"""
    return TimezoneHelper.get_gmt_string(city_name)

def get_city_current_time(city_name: str) -> Optional[Dict[str, Any]]:
    """Get current time in a city"""
    return TimezoneHelper.get_current_time_in_city(city_name)
