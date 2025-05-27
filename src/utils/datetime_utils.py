from datetime import datetime, timedelta, timezone

def get_current_utc_timestamp() -> datetime:
    """Returns the current UTC timestamp, timezone-aware."""
    return datetime.now(timezone.utc)

def format_timestamp(ts: datetime, fmt: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    """Formats a datetime object into a string."""
    return ts.strftime(fmt)

# Example Usage:
if __name__ == '__main__':
    now_utc = get_current_utc_timestamp()
    print(f"Current UTC Timestamp: {now_utc}")
    print(f"Formatted Timestamp: {format_timestamp(now_utc)}")
    
    # Example of creating a specific timezone-aware datetime
    # from dateutil import tz # Would need 'python-dateutil' in requirements.txt
    # est = tz.gettz('America/New_York')
    # dt_est = datetime(2023, 10, 26, 10, 0, 0, tzinfo=est)
    # print(f"Specific EST Timestamp: {format_timestamp(dt_est)}")
    # print(f"Converted to UTC: {format_timestamp(dt_est.astimezone(timezone.utc))}")
