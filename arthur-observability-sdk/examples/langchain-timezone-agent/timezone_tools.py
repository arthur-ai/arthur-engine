"""
Timezone tools for LangChain agent with OpenInference tracing.

This file combines the timezone conversion functions with LangChain tool wrappers
for use in the tutorial agent.
"""

import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from langchain.tools import tool

def load_timezone_shortcuts():
    """Load timezone shortcuts from JSON file."""
    try:
        # Get the directory of this script to find the JSON file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, 'timezone_shortcuts.json')
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Flatten the nested structure into a single dictionary
        shortcuts = {}
        for category in data.values():
            shortcuts.update(category)
        
        return shortcuts
    except FileNotFoundError:
        print("Warning: timezone_shortcuts.json not found, using fallback shortcuts")
        return {
            'EST': 'America/New_York', 'EDT': 'America/New_York',
            'CST': 'America/Chicago', 'CDT': 'America/Chicago',
            'MST': 'America/Denver', 'MDT': 'America/Denver',
            'PST': 'America/Los_Angeles', 'PDT': 'America/Los_Angeles',
            'GMT': 'GMT', 'UTC': 'UTC',
            'JST': 'Asia/Tokyo', 'IST': 'Asia/Kolkata',
            'CET': 'Europe/Paris', 'BST': 'Europe/London',
            'ZURICH': 'Europe/Zurich', 'LONDON': 'Europe/London',
            'TOKYO': 'Asia/Tokyo', 'CALIFORNIA': 'America/Los_Angeles',
            'NEW YORK': 'America/New_York'
        }

def convert_timezone(time_str, from_tz, to_tz):
    """
    Convert time between timezones.
    
    Args:
        time_str: "2024-03-15 14:30" or "2024-03-15 14:30:00" or "10pm" or "10:30pm"
        from_tz: "EST", "UTC", "America/New_York", "California", "Zurich", etc.
        to_tz: "JST", "UTC", "Asia/Tokyo", "California", "Zurich", etc.
    
    Returns:
        String with converted time or error message
    """
    shortcuts = load_timezone_shortcuts()
    
    try:
        # Handle time formats like "10pm", "10:30pm", "10 AM", etc.
        time_str = time_str.strip().upper()
        
        # If it's just a time (like "10PM"), assume today's date
        if re.match(r'^\d{1,2}(:\d{2})?\s*(AM|PM)$', time_str):
            today = datetime.now().strftime('%Y-%m-%d')
            time_str = f"{today} {time_str}"
        
        # Parse time
        if len(time_str.split(':')) == 2 and 'T' not in time_str:
            time_str += ":00"  # Add seconds if missing
        
        # Handle different date formats
        if '/' in time_str:
            time_str = time_str.replace('/', '-')
        
        # Parse the datetime
        dt = datetime.fromisoformat(time_str)
        
        # Get timezone names
        from_zone = shortcuts.get(from_tz.upper(), from_tz)
        to_zone = shortcuts.get(to_tz.upper(), to_tz)
        
        # Convert
        dt_from = dt.replace(tzinfo=ZoneInfo(from_zone))
        dt_to = dt_from.astimezone(ZoneInfo(to_zone))
        
        return f"{dt_to.strftime('%Y-%m-%d %H:%M:%S')} {to_tz.upper()}"
        
    except Exception as e:
        return f"Error: {str(e)}"

def current_time(timezone):
    """Get current time in timezone."""
    shortcuts = load_timezone_shortcuts()
    
    try:
        zone_name = shortcuts.get(timezone.upper(), timezone)
        now = datetime.now(ZoneInfo(zone_name))
        return f"{now.strftime('%Y-%m-%d %H:%M:%S')} {timezone.upper()}"
    except Exception as e:
        return f"Error: {str(e)}"

# LangChain Tool Wrappers

@tool
def get_current_time(timezone: str) -> str:
    """
    Get the current time in a specific timezone or city.
    
    Args:
        timezone: The timezone or city name (e.g., "Zurich", "California", "EST", "UTC")
    
    Returns:
        Current time in the specified timezone
    
    Examples:
        - "What is the time in Zurich right now?" -> get_current_time("Zurich")
        - "What time is it in California?" -> get_current_time("California")
        - "Current time in EST" -> get_current_time("EST")
    """
    return current_time(timezone)

@tool
def convert_time_between_zones(time_str: str, from_timezone: str, to_timezone: str) -> str:
    """
    Convert a time from one timezone to another.
    
    Args:
        time_str: The time to convert (e.g., "10pm", "2024-03-15 14:30", "10:30pm")
        from_timezone: The source timezone or city (e.g., "EDT", "California", "Zurich")
        to_timezone: The target timezone or city (e.g., "PST", "Tokyo", "London")
    
    Returns:
        The converted time in the target timezone
    
    Examples:
        - "What is 10pm EDT in California?" -> convert_time_between_zones("10pm", "EDT", "California")
        - "Convert 2:30pm EST to Tokyo time" -> convert_time_between_zones("2:30pm", "EST", "Tokyo")
        - "What time is 9am in London when it's 3pm in New York?" -> convert_time_between_zones("3pm", "New York", "London")
    """
    return convert_timezone(time_str, from_timezone, to_timezone) 