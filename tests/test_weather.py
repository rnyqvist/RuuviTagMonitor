import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from ruuvitag_monitor.app import (
    WeatherLocation,
    fetch_local_weather,
    geocode_city,
    hourly_forecast_for_day,
    load_weather_location,
    save_weather_location,
    weather_description,
    weather_number,
    weather_symbol,
)


class WeatherTests(unittest.TestCase):
    def test_weather_description_handles_known_and_unknown_codes(self):
        self.assertEqual(weather_description(0), "Clear sky")
        self.assertEqual(weather_description(999), "Unknown conditions")

    def test_weather_symbol_groups_weather_codes(self):
        self.assertEqual(weather_symbol(0), "☀")
        self.assertEqual(weather_symbol(63), "☔")
        self.assertEqual(weather_symbol(73), "❄")
        self.assertEqual(weather_symbol(95), "⚡")

    def test_weather_number_handles_missing_and_invalid_values(self):
        self.assertEqual(weather_number(18.55, 1), "18.6")
        self.assertEqual(weather_number(None), "–")
        self.assertEqual(weather_number(float("nan")), "–")

    def test_today_hourly_forecast_starts_at_current_full_hour(self):
        hourly = [
            {"time": "2026-07-18T18:00"},
            {"time": "2026-07-18T19:00"},
            {"time": "2026-07-18T20:00"},
            {"time": "2026-07-19T00:00"},
        ]
        result = hourly_forecast_for_day(
            hourly,
            datetime.fromisoformat("2026-07-18"),
            datetime.fromisoformat("2026-07-18T19:31"),
        )
        self.assertEqual([item["time"] for item in result], ["2026-07-18T19:00", "2026-07-18T20:00"])

    def test_tomorrow_hourly_forecast_keeps_the_full_day(self):
        hourly = [{"time": f"2026-07-19T{hour:02d}:00"} for hour in range(24)]
        result = hourly_forecast_for_day(hourly, datetime.fromisoformat("2026-07-19"))
        self.assertEqual(len(result), 24)
        self.assertEqual(result[0]["time"], "2026-07-19T00:00")

    def test_fetch_local_weather_combines_location_and_forecast(self):
        response = {
            "current": {"temperature_2m": 18.5, "weather_code": 1},
            "daily": {"time": ["2026-07-18", "2026-07-19"], "weather_code": [1, 61], "temperature_2m_max": [21.0, 19.0], "temperature_2m_min": [13.0, 12.0]},
            "hourly": {"time": ["2026-07-18T00:00", "2026-07-19T00:00"], "temperature_2m": [14.0, 13.0], "weather_code": [1, 61]},
        }
        with patch("ruuvitag_monitor.app._get_json", return_value=response):
            result = fetch_local_weather(WeatherLocation("Helsinki, Uusimaa, Finland", 60.17, 24.94))
        self.assertEqual(result.location_name, "Helsinki, Uusimaa, Finland")
        self.assertEqual(result.current["temperature_2m"], 18.5)
        self.assertEqual(result.daily[0]["temperature_2m_max"], 21.0)
        self.assertEqual(result.hourly[1]["weather_code"], 61)
        self.assertEqual(len(result.daily), 2)

    def test_geocode_city_rejects_invalid_coordinates(self):
        response = {"results": [{"name": "Invalid", "latitude": 120, "longitude": 24.94}]}
        with patch("ruuvitag_monitor.app._get_json", return_value=response):
            with self.assertRaisesRegex(ValueError, "invalid coordinates"):
                geocode_city("Invalid")

    def test_geocode_city_uses_first_search_result(self):
        response = {"results": [{"name": "Helsinki", "admin1": "Uusimaa", "country": "Finland", "latitude": 60.17, "longitude": 24.94}]}
        with patch("ruuvitag_monitor.app._get_json", return_value=response):
            location = geocode_city("Helsinki Finland")
        self.assertEqual(location.name, "Helsinki, Uusimaa, Finland")

    def test_weather_location_is_saved_and_loaded(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "weather-location.json"
            location = WeatherLocation("Helsinki, Uusimaa, Finland", 60.17, 24.94)
            with patch("ruuvitag_monitor.app.weather_location_path", return_value=path):
                save_weather_location(location)
                self.assertEqual(load_weather_location(), location)

    def test_fetch_local_weather_rejects_empty_daily_forecast(self):
        with patch("ruuvitag_monitor.app._get_json", return_value={"current": {}, "daily": {"time": []}, "hourly": {"time": []}}):
            with self.assertRaisesRegex(ValueError, "incomplete forecast"):
                fetch_local_weather(WeatherLocation("Helsinki", 60.17, 24.94))
