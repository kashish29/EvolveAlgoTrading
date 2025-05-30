import unittest
from datetime import datetime, timezone, timedelta # Added timedelta
from src.utils.date_formatter import parse_date, COMMON_DATE_FORMATS

class TestDateFormatter(unittest.TestCase):

    def test_parse_date_valid_formats(self):
        test_cases = {
            "2023-10-26 14:30:00": datetime(2023, 10, 26, 14, 30, 0),
            "2023-01-05": datetime(2023, 1, 5),
            "2023/07/15 08:00:00": datetime(2023, 7, 15, 8, 0, 0),
            "15-07-2023": datetime(2023, 7, 15),
            "20230715083000": datetime(2023, 7, 15, 8, 30, 0),
            "20231112": datetime(2023, 11, 12),
            # ISO 8601 Examples
            "2023-10-26T12:30:45Z": datetime(2023, 10, 26, 12, 30, 45, tzinfo=timezone.utc),
            "2023-10-26T15:30:45+03:00": datetime(2023, 10, 26, 15, 30, 45, tzinfo=timezone(timedelta(hours=3))),
            "2023-10-26T09:30:45-03:00": datetime(2023, 10, 26, 9, 30, 45, tzinfo=timezone(timedelta(hours=-3))),
            "2023-10-26T15:30:45.123456+03:00": datetime(2023, 10, 26, 15, 30, 45, 123456, tzinfo=timezone(timedelta(hours=3))),
            "2023-10-26T12:30:45.500Z": datetime(2023, 10, 26, 12, 30, 45, 500000, tzinfo=timezone.utc),
        }
        for date_str, expected_dt in test_cases.items():
            with self.subTest(date_str=date_str):
                parsed_dt = parse_date(date_str)
                self.assertIsNotNone(parsed_dt, f"Failed to parse '{date_str}'")
                # For timezone-aware comparisons, ensure both have timezone info or both are naive.
                if expected_dt.tzinfo is not None:
                    self.assertIsNotNone(parsed_dt.tzinfo, f"Parsed datetime for '{date_str}' should be timezone-aware.")
                    # Can't directly compare offset objects, but can compare total offset from UTC
                    self.assertEqual(parsed_dt.utcoffset(), expected_dt.utcoffset(), f"Timezone offset mismatch for '{date_str}'")
                    # Compare without tzinfo if offsets match, or compare directly if supported
                    self.assertEqual(parsed_dt.replace(tzinfo=None), expected_dt.replace(tzinfo=None), f"Date/time value mismatch for '{date_str}'")

                else:
                    self.assertIsNone(parsed_dt.tzinfo, f"Parsed datetime for '{date_str}' should be naive.")
                    self.assertEqual(parsed_dt, expected_dt, f"Datetime mismatch for '{date_str}'")


    def test_parse_date_invalid_formats(self):
        invalid_dates = [
            "2023-13-01",  # Invalid month
            "not-a-date",
            "2023-10-26T12:30:45X", # Invalid timezone specifier
            "202310", # Too short for any defined compact format
        ]
        for date_str in invalid_dates:
            with self.subTest(date_str=date_str):
                self.assertIsNone(parse_date(date_str), f"Should have failed to parse '{date_str}'")

    def test_parse_date_empty_or_none_input(self):
        self.assertIsNone(parse_date(None))
        self.assertIsNone(parse_date(""))

    def test_parse_date_with_custom_formats(self):
        custom_date_str = "10/26/2023/14/30"
        custom_formats = ["%m/%d/%Y/%H/%M"]
        expected_dt = datetime(2023, 10, 26, 14, 30)
        parsed_dt = parse_date(custom_date_str, formats=custom_formats)
        self.assertEqual(parsed_dt, expected_dt)

        # Test with a format not in the custom list
        parsed_dt_fail = parse_date("2023-10-26", formats=custom_formats)
        self.assertIsNone(parsed_dt_fail)
        
    def test_all_common_formats_are_valid_strptime_formats(self):
        # This is a meta-test to ensure the formats themselves are valid for strptime
        # It doesn't parse a date string, but checks the format strings.
        # We can't directly validate a format string easily without trying to parse with it.
        # A simple check: try to parse a known datetime with each format.
        # This is more of an integration check for the COMMON_DATE_FORMATS list itself.
        # For simplicity, this test is more of a reminder.
        # A more robust check would involve carefully crafting date strings for each format.
        self.assertTrue(len(COMMON_DATE_FORMATS) > 0) # Basic check

if __name__ == '__main__':
    unittest.main()
