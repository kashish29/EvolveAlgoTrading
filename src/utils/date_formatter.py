from datetime import datetime
from typing import Optional, List

# Define a list of common date formats to try
COMMON_DATE_FORMATS: List[str] = [
    "%Y-%m-%d %H:%M:%S.%f%z",  # With microseconds and timezone
    "%Y-%m-%d %H:%M:%S%z",     # With seconds and timezone
    "%Y-%m-%d %H:%M:%S",       # With seconds, no timezone
    "%Y-%m-%d %H:%M",          # With minutes, no timezone
    "%Y-%m-%d",                # Date only
    "%Y/%m/%d %H:%M:%S",       # Slash separators
    "%Y/%m/%d",
    "%d-%m-%Y %H:%M:%S",       # Day-month-year
    "%d-%m-%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
    "%Y%m%d%H%M%S",            # Compact form
    "%Y%m%d",                  # Compact date
    # Add more formats as needed, e.g., for ISO 8601
    "%Y-%m-%dT%H:%M:%S%z",     # ISO 8601 with Z or +HH:MM
    "%Y-%m-%dT%H:%M:%S.%f%z", # ISO 8601 with microseconds
    "%Y-%m-%dT%H:%M:%S",       # ISO 8601 (naive or assumes local if no tz)
]

def parse_date(date_str: str, formats: Optional[List[str]] = None) -> Optional[datetime]:
    """
    Parses a date string into a datetime object using a list of common formats.

    Args:
        date_str (str): The date string to parse.
        formats (Optional[List[str]]): A list of strptime formats to try. 
                                       If None, uses COMMON_DATE_FORMATS.

    Returns:
        Optional[datetime]: A datetime object if parsing is successful, 
                            None otherwise.
    """
    if not date_str or not isinstance(date_str, str):
        return None

    formats_to_try = formats if formats is not None else COMMON_DATE_FORMATS

    for fmt in formats_to_try:
        try:
            # Handle 'Z' for UTC in ISO 8601 formats explicitly if needed,
            # as %z might not always parse it correctly across all platforms/python versions.
            # Python 3.7+ %z handles Z correctly. For older, a replace might be needed:
            # if 'Z' in date_str and fmt.endswith('%z'):
            #     dt = datetime.strptime(date_str.replace('Z', '+0000'), fmt)
            # else:
            #     dt = datetime.strptime(date_str, fmt)
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue  # Try the next format
    
    print(f"Warning: Could not parse date string '{date_str}' with any of the provided formats.")
    return None

if __name__ == '__main__':
    print("Testing date_formatter.py...")
    test_dates = [
        "2023-10-26 14:30:00",
        "2023-10-26",
        "2023/10/26 14:30:00",
        "26-10-2023",
        "20231026143000",
        "2023-10-26T12:30:45Z", # ISO 8601 UTC
        "2023-10-26T15:30:45+03:00", # ISO 8601 with offset
        "2023-10-26T15:30:45.123456+03:00", # ISO 8601 with microseconds and offset
        "invalid-date-string",
        None, # Test None input
        ""    # Test empty string
    ]

    for td_str in test_dates:
        parsed = parse_date(td_str)
        if parsed:
            print(f"Successfully parsed '{td_str}' -> {parsed} (TZ: {parsed.tzinfo})")
        else:
            print(f"Failed to parse '{td_str}'")
    
    # Test with custom formats
    custom_fmt_str = "23/Oct/2023--14::30"
    custom_formats = ["%d/%b/%Y--%H::%M"]
    parsed_custom = parse_date(custom_fmt_str, formats=custom_formats)
    if parsed_custom:
        print(f"Successfully parsed '{custom_fmt_str}' with custom format -> {parsed_custom}")
    else:
        print(f"Failed to parse '{custom_fmt_str}' with custom format")
