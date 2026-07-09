from __future__ import annotations

import asyncio
import json
import math
import os
import queue
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

try:
    from bleak import BleakScanner
except ImportError:  # pragma: no cover - handled at runtime in the GUI
    BleakScanner = None


APP_NAME = "RuuviTag Monitor"
RUUVI_COMPANY_ID = 0x0499
CARD_WIDTH = 360
CARD_HEIGHT = 334
CARD_GAP = 12
WINDOW_CHROME_X = 56
WINDOW_CHROME_Y = 128
EMPTY_SIZE = (680, 400)
MIN_SIZE = (500, 400)
MAX_COLUMNS = 3


@dataclass
class RuuviReading:
    mac_address: str
    default_name: str
    temperature_c: float
    humidity_percent: float
    pressure_hpa: float
    acceleration_g: float
    battery_mv: int
    tx_power_dbm: int
    movement_counter: int
    measurement_sequence: int
    rssi: int
    last_seen: datetime

    @property
    def temperature_text(self) -> str:
        return f"{self.temperature_c:.1f} C"

    @property
    def humidity_text(self) -> str:
        return f"{self.humidity_percent:.1f} %"

    @property
    def pressure_text(self) -> str:
        return f"{self.pressure_hpa:.1f}"

    @property
    def battery_text(self) -> str:
        return f"{self.battery_mv} mV"

    @property
    def tx_power_text(self) -> str:
        return f"{self.tx_power_dbm} dBm"

    @property
    def movement_text(self) -> str:
        return f"{self.movement_counter} / {self.acceleration_g:.2f} g"

    @property
    def sequence_text(self) -> str:
        return str(self.measurement_sequence)

    @property
    def rssi_text(self) -> str:
        return f"{self.rssi} dBm"

    @property
    def last_seen_text(self) -> str:
        return self.last_seen.strftime("%H.%M.%S")


def settings_path() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "RuuviTagMonitor" / "tag-names.json"
    return Path.home() / "AppData" / "Local" / "RuuviTagMonitor" / "tag-names.json"


def load_tag_names() -> dict[str, str]:
    path = settings_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(key).upper(): str(value) for key, value in data.items() if str(value).strip()}


def save_tag_names(names: dict[str, str]) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(names, indent=2, sort_keys=True), encoding="utf-8")


def read_i16(data: bytes, offset: int) -> int:
    value = (data[offset] << 8) | data[offset + 1]
    return value - 0x10000 if value & 0x8000 else value


def read_u16(data: bytes, offset: int) -> int:
    return (data[offset] << 8) | data[offset + 1]


def decode_ruuvi_rawv2(data: bytes, rssi: int, timestamp: datetime | None = None) -> RuuviReading | None:
    if len(data) < 24 or data[0] != 0x05:
        return None

    temperature_raw = read_i16(data, 1)
    humidity_raw = read_u16(data, 3)
    pressure_raw = read_u16(data, 5)
    acceleration_x_raw = read_i16(data, 7)
    acceleration_y_raw = read_i16(data, 9)
    acceleration_z_raw = read_i16(data, 11)
    power_info = read_u16(data, 13)
    movement_counter = data[15]
    measurement_sequence = read_u16(data, 16)
    mac_address = ":".join(f"{value:02X}" for value in data[18:24])

    temperature_c = temperature_raw * 0.005
    humidity_percent = humidity_raw * 0.0025
    pressure_hpa = (pressure_raw + 50000) / 100.0
    battery_mv = (power_info >> 5) + 1600
    tx_power_dbm = -40 + ((power_info & 0x1F) * 2)
    acceleration_g = math.sqrt(
        (acceleration_x_raw / 1000.0) ** 2
        + (acceleration_y_raw / 1000.0) ** 2
        + (acceleration_z_raw / 1000.0) ** 2
    )

    short_id = mac_address.replace(":", "")[-4:]

    return RuuviReading(
        mac_address=mac_address,
        default_name=f"Ruuvi {short_id}",
        temperature_c=temperature_c,
        humidity_percent=humidity_percent,
        pressure_hpa=pressure_hpa,
        acceleration_g=acceleration_g,
        battery_mv=battery_mv,
        tx_power_dbm=tx_power_dbm,
        movement_counter=movement_counter,
        measurement_sequence=measurement_sequence,
        rssi=rssi,
        last_seen=timestamp or datetime.now(),
    )


class BleScannerWorker:
    def __init__(self, event_queue: queue.Queue[tuple[str, object]]) -> None:
        self.event_queue = event_queue
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def _run(self) -> None:
        if BleakScanner is None:
            self.event_queue.put(("error", "The 'bleak' package is not installed. Run: pip install -r requirements.txt"))
            self.event_queue.put(("stopped", None))
            return

        try:
            asyncio.run(self._scan())
        except Exception as exc:  # noqa: BLE001 - surface scanner errors to UI
            self.event_queue.put(("error", f"BLE scanner failed: {exc}"))
        finally:
            self.event_queue.put(("stopped", None))

    async def _scan(self) -> None:
        def on_advertisement(_device, advertisement_data) -> None:
            payload = advertisement_data.manufacturer_data.get(RUUVI_COMPANY_ID)
            if not payload:
                return
            reading = decode_ruuvi_rawv2(bytes(payload), advertisement_data.rssi, datetime.now())
            if reading:
                self.event_queue.put(("reading", reading))

        scanner = BleakScanner(on_advertisement, scanning_mode="active")
        await scanner.start()
        self.event_queue.put(("started", None))
        try:
            while not self.stop_event.is_set():
                await asyncio.sleep(0.1)
        finally:
            await scanner.stop()


class SensorCard(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: RuuviTagMonitorApp, reading: RuuviReading) -> None:
        super().__init__(parent, style="Card.TFrame", padding=18)
        self.app = app
        self.mac_address = reading.mac_address
        self.name_var = tk.StringVar(value=app.display_name_for(reading))
        self.rssi_var = tk.StringVar()
        self.temp_var = tk.StringVar()
        self.humidity_var = tk.StringVar()
        self.pressure_var = tk.StringVar()
        self.battery_var = tk.StringVar()
        self.tx_var = tk.StringVar()
        self.movement_var = tk.StringVar()
        self.sequence_var = tk.StringVar()
        self.last_seen_var = tk.StringVar()

        self.configure(width=CARD_WIDTH, height=CARD_HEIGHT)
        self.grid_propagate(False)
        self._build_ui()
        self.update_reading(reading)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        name_entry = ttk.Entry(self, textvariable=self.name_var, style="Name.TEntry")
        name_entry.grid(row=0, column=0, columnspan=2, sticky="ew")
        name_entry.bind("<Return>", self._save_name)
        name_entry.bind("<FocusOut>", self._save_name)

        ttk.Label(self, text=self.mac_address, style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(3, 20))
        ttk.Label(self, textvariable=self.rssi_var, style="Rssi.TLabel", padding=(10, 5)).grid(
            row=0, column=1, rowspan=2, sticky="ne"
        )

        self._metric("Temperature", self.temp_var, 2, 0, "Temperature.TLabel")
        self._metric("Humidity", self.humidity_var, 2, 1, "LargeMetric.TLabel")
        self._metric("Pressure", self.pressure_var, 4, 0, "Metric.TLabel")
        self._metric("Battery", self.battery_var, 4, 1, "Metric.TLabel")
        self._metric("TX", self.tx_var, 4, 2, "Metric.TLabel")
        self._metric("Movement", self.movement_var, 6, 0, "SmallValue.TLabel")
        self._metric("Sequence", self.sequence_var, 6, 1, "SmallValue.TLabel")
        self._metric("Last seen", self.last_seen_var, 6, 2, "SmallValue.TLabel")

    def _metric(self, label: str, variable: tk.StringVar, row: int, column: int, value_style: str) -> None:
        frame = ttk.Frame(self, style="MetricGroup.TFrame")
        frame.grid(row=row, column=column, sticky="nw", pady=(0, 16), padx=(0, 10))
        ttk.Label(frame, text=label, style="Muted.TLabel").pack(anchor="w")
        ttk.Label(frame, textvariable=variable, style=value_style).pack(anchor="w")

    def _save_name(self, _event=None) -> None:
        self.app.save_display_name(self.mac_address, self.name_var.get())

    def update_reading(self, reading: RuuviReading) -> None:
        if self.mac_address not in self.app.tag_names:
            self.name_var.set(reading.default_name)
        self.rssi_var.set(reading.rssi_text)
        self.temp_var.set(reading.temperature_text)
        self.humidity_var.set(reading.humidity_text)
        self.pressure_var.set(reading.pressure_text)
        self.battery_var.set(reading.battery_text)
        self.tx_var.set(reading.tx_power_text)
        self.movement_var.set(reading.movement_text)
        self.sequence_var.set(reading.sequence_text)
        self.last_seen_var.set(reading.last_seen_text)


class RuuviTagMonitorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.minsize(*MIN_SIZE)
        self.configure(bg="#f3f6f1")

        self.event_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.scanner = BleScannerWorker(self.event_queue)
        self.tag_names = load_tag_names()
        self.cards: dict[str, SensorCard] = {}
        self.readings: dict[str, RuuviReading] = {}
        self.scanning = False

        self.status_var = tk.StringVar(value="Ready to scan nearby RuuviTag BLE advertisements.")
        self.start_text = tk.StringVar(value="Start scan")
        self._configure_style()
        self._build_ui()
        self.bind("<F5>", lambda _event: self.start_scan())
        self.bind("<Escape>", lambda _event: self.stop_scan())
        self._resize_to_content()
        self.after(100, self._drain_events)

    def _configure_style(self) -> None:
        self.style = ttk.Style(self)
        if "vista" in self.style.theme_names():
            self.style.theme_use("vista")

        self.style.configure(".", font=("Segoe UI", 10))
        self.style.configure("Root.TFrame", background="#f3f6f1")
        self.style.configure("Toolbar.TFrame", background="#f3f6f1")
        self.style.configure("Cards.TFrame", background="#f3f6f1")
        self.style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        self.style.configure("MetricGroup.TFrame", background="#ffffff", relief="flat", borderwidth=0)
        self.style.configure("Title.TLabel", background="#f3f6f1", foreground="#202020", font=("Segoe UI", 18, "bold"))
        self.style.configure("Status.TLabel", background="#f3f6f1", foreground="#5f665b")
        self.style.configure("Muted.TLabel", background="#ffffff", foreground="#686f64", font=("Segoe UI", 9))
        self.style.configure("Metric.TLabel", background="#ffffff", foreground="#202020", font=("Segoe UI", 16, "bold"))
        self.style.configure("LargeMetric.TLabel", background="#ffffff", foreground="#202020", font=("Segoe UI", 22, "bold"))
        self.style.configure("Temperature.TLabel", background="#ffffff", foreground="#337b2f", font=("Segoe UI", 32, "bold"))
        self.style.configure("SmallValue.TLabel", background="#ffffff", foreground="#202020", font=("Segoe UI", 9))
        self.style.configure("Rssi.TLabel", background="#4d9f38", foreground="#ffffff", font=("Segoe UI", 10))
        self.style.configure("Name.TEntry", font=("Segoe UI", 12, "bold"))
        self.style.configure("Accent.TButton", font=("Segoe UI", 10))

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="Root.TFrame", padding=20)
        root.pack(fill="both", expand=True)

        toolbar = ttk.Frame(root, style="Toolbar.TFrame")
        toolbar.pack(fill="x")
        toolbar.columnconfigure(0, weight=1)

        title_area = ttk.Frame(toolbar, style="Toolbar.TFrame")
        title_area.grid(row=0, column=0, sticky="ew")
        ttk.Label(title_area, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_area, textvariable=self.status_var, style="Status.TLabel").pack(anchor="w", pady=(2, 0))

        button_area = ttk.Frame(toolbar, style="Toolbar.TFrame")
        button_area.grid(row=0, column=1, sticky="e")
        self.start_button = ttk.Button(button_area, textvariable=self.start_text, command=self.start_scan, style="Accent.TButton")
        self.start_button.pack(side="left", padx=(0, 8))
        self.stop_button = ttk.Button(button_area, text="Stop", command=self.stop_scan, state="disabled")
        self.stop_button.pack(side="left", padx=(0, 8))
        ttk.Button(button_area, text="Clear", command=self.clear_tags).pack(side="left")

        self.cards_frame = ttk.Frame(root, style="Cards.TFrame")
        self.cards_frame.pack(fill="both", expand=True, pady=(22, 0))

        self.empty_label = ttk.Label(
            self.cards_frame,
            text="No RuuviTags yet\nStart scanning to discover nearby Ruuvi sensors.",
            background="#f3f6f1",
            foreground="#5f665b",
            justify="center",
            font=("Segoe UI", 13),
        )
        self.empty_label.pack(expand=True)

    def start_scan(self) -> None:
        self.scanner.start()
        self.scanning = True
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status_var.set("Starting BLE scanner...")

    def stop_scan(self) -> None:
        self.scanner.stop()
        self.status_var.set("Stopping scan...")

    def clear_tags(self) -> None:
        for card in self.cards.values():
            card.destroy()
        self.cards.clear()
        self.readings.clear()
        self._layout_cards()
        self.status_var.set("Cleared current sensor list.")

    def display_name_for(self, reading: RuuviReading) -> str:
        return self.tag_names.get(reading.mac_address.upper(), reading.default_name)

    def save_display_name(self, mac_address: str, proposed_name: str) -> None:
        name = proposed_name.strip()
        key = mac_address.upper()
        reading = self.readings.get(mac_address)
        if name:
            self.tag_names[key] = name
            self.status_var.set(f"Saved name '{name}' for {mac_address}.")
        else:
            self.tag_names.pop(key, None)
            if reading and mac_address in self.cards:
                self.cards[mac_address].name_var.set(reading.default_name)
            self.status_var.set(f"Reset name for {mac_address}.")
        save_tag_names(self.tag_names)

    def _drain_events(self) -> None:
        while True:
            try:
                event, payload = self.event_queue.get_nowait()
            except queue.Empty:
                break

            if event == "started":
                self.status_var.set("Scanning for RuuviTag BLE advertisements...")
            elif event == "stopped":
                self.scanning = False
                self.start_button.configure(state="normal")
                self.stop_button.configure(state="disabled")
                if not self.cards:
                    self.status_var.set("Scan stopped. No RuuviTags found.")
            elif event == "error":
                self.scanning = False
                self.start_button.configure(state="normal")
                self.stop_button.configure(state="disabled")
                message = str(payload)
                self.status_var.set(message)
                messagebox.showerror(APP_NAME, message)
            elif event == "reading":
                self._upsert_reading(payload)

        self.after(100, self._drain_events)

    def _upsert_reading(self, reading: RuuviReading) -> None:
        self.readings[reading.mac_address] = reading
        card = self.cards.get(reading.mac_address)
        new_card = card is None
        if card is None:
            card = SensorCard(self.cards_frame, self, reading)
            self.cards[reading.mac_address] = card
        else:
            card.update_reading(reading)

        self.status_var.set(f"Receiving RuuviTag data from {len(self.cards)} sensor{'s' if len(self.cards) != 1 else ''}.")
        if new_card:
            self._layout_cards()

    def _layout_cards(self) -> None:
        if self.cards:
            self.empty_label.pack_forget()
        else:
            self.empty_label.pack(expand=True)

        columns = self._column_count()
        for index, card in enumerate(self.cards.values()):
            row = index // columns
            column = index % columns
            card.grid(row=row, column=column, padx=(0, CARD_GAP), pady=(0, CARD_GAP), sticky="nw")

        self._resize_to_content()

    def _column_count(self) -> int:
        count = len(self.cards)
        if count <= 1:
            return 1
        if count == 2:
            return 2
        if count == 4:
            return 2
        return min(MAX_COLUMNS, count)

    def _resize_to_content(self) -> None:
        count = len(self.cards)
        if count == 0:
            width, height = EMPTY_SIZE
        else:
            columns = self._column_count()
            rows = math.ceil(count / columns)
            width = WINDOW_CHROME_X + columns * (CARD_WIDTH + CARD_GAP)
            height = WINDOW_CHROME_Y + rows * (CARD_HEIGHT + CARD_GAP)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = min(max(width, MIN_SIZE[0]), screen_width - 80)
        height = min(max(height, MIN_SIZE[1]), screen_height - 80)
        self.geometry(f"{int(width)}x{int(height)}")


def main() -> None:
    app = RuuviTagMonitorApp()
    app.mainloop()
