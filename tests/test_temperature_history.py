import csv
import tempfile
import unittest
from pathlib import Path

from ruuvitag_monitor.app import CSV_FIELDS, graph_window_layout, load_environment_history


class TemperatureHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_combines_capture_files_by_mac_and_sorts_by_time(self) -> None:
        self._write_csv(
            "Kitchen_2.csv",
            [self._row("2026-07-12T12:00:00+03:00", "22.5", "AA:BB:CC:DD:EE:01", "Kitchen", "1002.5")],
        )
        self._write_csv(
            "Kitchen_1.csv",
            [self._row("2026-07-12T10:00:00+03:00", "20.5", "AA:BB:CC:DD:EE:01", "Kitchen", "998.5")],
        )

        history = load_environment_history(self.data_dir)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].display_name, "Kitchen")
        self.assertEqual(history[0].temperatures_c, [20.5, 22.5])
        self.assertEqual(history[0].pressures_hpa, [998.5, 1002.5])
        self.assertEqual([timestamp.hour for timestamp in history[0].timestamps], [10, 12])

    def test_returns_a_separate_series_for_each_tag(self) -> None:
        self._write_csv(
            "tags.csv",
            [
                self._row("2026-07-12T10:00:00+03:00", "20", "AA:01", "Kitchen"),
                self._row("2026-07-12T10:00:00+03:00", "80", "AA:02", "Sauna"),
            ],
        )

        history = load_environment_history(self.data_dir)

        self.assertEqual([item.display_name for item in history], ["Kitchen", "Sauna"])

    def test_skips_invalid_rows_and_unreadable_csv_content(self) -> None:
        self._write_csv(
            "mixed.csv",
            [
                self._row("not-a-date", "20", "AA:01", "Kitchen"),
                self._row("2026-07-12T10:00:00+03:00", "not-a-number", "AA:01", "Kitchen"),
                self._row("2026-07-12T11:00:00+03:00", "21.25", "AA:01", "Kitchen"),
            ],
        )
        (self.data_dir / "broken.csv").write_bytes(b"\xff\xfe\x00")

        history = load_environment_history(self.data_dir)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].temperatures_c, [21.25])

    def test_graph_window_scales_to_tag_count(self) -> None:
        self.assertEqual(graph_window_layout(1, 1920, 1080), (1100, 500, 330))
        self.assertEqual(graph_window_layout(2, 1920, 1080), (1100, 664, 280))
        self.assertEqual(graph_window_layout(3, 1920, 1080), (1100, 836, 240))

    def test_many_graphs_are_bounded_by_screen_height(self) -> None:
        self.assertEqual(graph_window_layout(5, 1920, 1080), (1100, 1000, 240))

    def _write_csv(self, file_name: str, rows: list[dict[str, object]]) -> None:
        with (self.data_dir / file_name).open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _row(
        timestamp: str,
        temperature: str,
        mac_address: str,
        name: str,
        pressure: str = "1000",
    ) -> dict[str, object]:
        return {
            "timestamp": timestamp,
            "mac_address": mac_address,
            "name": name,
            "temperature_c": temperature,
            "humidity_percent": "45",
            "pressure_hpa": pressure,
            "acceleration_g": "1",
            "battery_mv": "2900",
            "tx_power_dbm": "4",
            "movement_counter": "1",
            "measurement_sequence": "2",
            "rssi_dbm": "-60",
        }


if __name__ == "__main__":
    unittest.main()
