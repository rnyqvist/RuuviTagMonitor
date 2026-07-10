import csv
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from ruuvitag_monitor.app import (
    RuuviReading,
    append_reading_csv,
    capture_file_name,
    load_logging_settings,
    safe_file_stem,
    save_logging_settings,
)


class DataCollectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.local_app_data = patch.dict("os.environ", {"LOCALAPPDATA": self.temp_dir.name})
        self.local_app_data.start()

    def tearDown(self) -> None:
        self.local_app_data.stop()
        self.temp_dir.cleanup()

    def test_logging_settings_round_trip(self) -> None:
        settings = {
            "C0:FF:EE:00:00:01": {
                "enabled": True,
                "interval_seconds": 15,
                "file_name": "Kitchen_2026-07-10.csv",
                "capture_started_at": "2026-07-10T12:00:00+03:00",
            },
        }
        save_logging_settings(settings)

        self.assertEqual(load_logging_settings(), settings)

    def test_each_mac_uses_a_separate_csv(self) -> None:
        first = self._reading("C0:FF:EE:00:00:01")
        second = self._reading("C0:FF:EE:00:00:02")

        first_path = append_reading_csv(first, "Kitchen", self._path("Kitchen_2026-07-10.csv"))
        second_path = append_reading_csv(second, "Sauna", self._path("Sauna_2026-07-10.csv"))

        self.assertNotEqual(first_path, second_path)
        self.assertTrue(first_path.exists())
        self.assertTrue(second_path.exists())

    def test_append_writes_one_header_and_multiple_rows(self) -> None:
        reading = self._reading("C0:FF:EE:00:00:01")

        path = append_reading_csv(reading, "Kitchen", self._path("Kitchen_2026-07-10.csv"))
        append_reading_csv(reading, "Kitchen", path)

        with path.open(encoding="utf-8", newline="") as csv_file:
            rows = list(csv.DictReader(csv_file))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["name"], "Kitchen")
        self.assertEqual(rows[0]["temperature_c"], "21.125")
        self.assertEqual(path.parent, Path(self.temp_dir.name) / "RuuviTagMonitor" / "data")

    def test_capture_filename_uses_name_and_start_date(self) -> None:
        started = datetime(2026, 7, 10, 12, 0, 0)

        self.assertEqual(capture_file_name("Kitchen", started), "Kitchen_2026-07-10.csv")
        self.assertEqual(capture_file_name("Kitchen", started, 2), "Kitchen_2026-07-10_2.csv")

    def test_filename_removes_windows_invalid_characters(self) -> None:
        self.assertEqual(safe_file_stem('Sauna: North/West?'), "Sauna_ North_West_")
        self.assertEqual(safe_file_stem("CON"), "CON_tag")

    @staticmethod
    def _path(file_name: str) -> Path:
        from ruuvitag_monitor.app import data_directory

        return data_directory() / file_name

    @staticmethod
    def _reading(mac_address: str) -> RuuviReading:
        return RuuviReading(
            mac_address=mac_address,
            default_name="Ruuvi 0001",
            temperature_c=21.125,
            humidity_percent=45.5,
            pressure_hpa=1001.25,
            acceleration_g=1.0,
            battery_mv=2900,
            tx_power_dbm=4,
            movement_counter=7,
            measurement_sequence=123,
            rssi=-61,
            last_seen=datetime(2026, 7, 10, 12, 0, 0),
        )


if __name__ == "__main__":
    unittest.main()
